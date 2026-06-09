#!/usr/bin/env python3
"""Sprint 6 tests: the Live Wire module (opt-in observed overlay).

Covers the capture parser and its tolerant numeric reading, domain matching, the
observed slot contract, the Search Console click override and its band re-anchor
invariant, the AI-citation share and competitor split (shares summing to 100), the
non-destructive overlay (the offline slots are byte-identical with and without a
capture), graceful degradation without the prior modules, and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.live_wire import (  # noqa: E402
    LiveWireError,
    _is_client_domain,
    _norm_domain,
    _to_float,
    load_capture,
)
from querymantic import pipeline, run_state  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
SAMPLE_CAPTURE = PLUGIN_ROOT / "assets" / "livewire" / "sample_capture.json"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"
OFFLINE_STACK = ("entity_web", "fan_out_radar", "citation_grid", "click_ceiling")
FULL_STACK = OFFLINE_STACK + ("live_wire",)


def _run(tmp: Path, modules: tuple[str, ...], with_capture: bool = True) -> dict:
    kwargs: dict = {}
    if "live_wire" in modules and with_capture:
        kwargs["live_wire"] = {"capture": load_capture(SAMPLE_CAPTURE)}
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs=kwargs,
    )


# --- the capture parser -----------------------------------------------------


def test_to_float_accepts_fraction_and_percent() -> None:
    assert _to_float(0.067) == pytest.approx(0.067)
    assert _to_float("5.4%") == pytest.approx(0.054)
    assert _to_float("2840") == pytest.approx(2840.0)
    assert _to_float("") is None
    assert _to_float(None) is None
    # A boolean is never a number, so a stray True does not become 1.0.
    assert _to_float(True) is None


def test_domain_matching() -> None:
    assert _norm_domain("https://www.Example-Shoes.com/trail") == "example-shoes.com"
    assert _is_client_domain("www.example-shoes.com/trail", "example-shoes.com")
    assert _is_client_domain("shop.example-shoes.com", "example-shoes.com")
    assert not _is_client_domain("competitor1.com", "example-shoes.com")


def test_load_capture_parses_both_blocks() -> None:
    cap = load_capture(SAMPLE_CAPTURE)
    assert cap["client_domain"] == "example-shoes.com"
    assert len(cap["search_console"]["rows"]) == 7
    # The percent-string CTR is normalised to a fraction at parse time.
    best = next(
        r for r in cap["search_console"]["rows"] if r["query"] == "best running shoes"
    )
    assert best["ctr"] == pytest.approx(0.054)
    assert "perplexity" in cap["ai_citations"]["surfaces"]


def test_load_capture_rejects_empty(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"livewire_capture": {"version": "1.0"}}', encoding="utf-8")
    with pytest.raises(LiveWireError):
        load_capture(bad)


# --- the observed slot contract ---------------------------------------------


def test_live_wire_contract(tmp_path: Path) -> None:
    _run(tmp_path, FULL_STACK)
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["querymantic"]["modules_run"][-1] == "live_wire"

    lw = loaded["modules"]["live_wire"]
    assert lw["mode"] == "observed"
    assert lw["opt_in"] is True
    assert lw["reads"] == {"click_ceiling": True, "citation_grid": True}
    assert lw["capture"]["client_domain"] == "example-shoes.com"
    assert lw["capture"]["search_console"]["present"] is True
    assert lw["capture"]["ai_citations"]["present"] is True
    assert "click_ceiling" in lw["overrides"]
    assert "citation_grid" in lw["overrides"]


# --- Search Console override ------------------------------------------------


def test_search_console_override_and_reanchor(tmp_path: Path) -> None:
    state = _run(tmp_path, FULL_STACK)
    lw = state["modules"]["live_wire"]
    cc_by_cluster = {
        c["cluster_index"]: c for c in state["modules"]["click_ceiling"]["clusters"]
    }
    sc = lw["overrides"]["click_ceiling"]
    assert sc["total_sc_rows"] == 7
    assert sc["matched_queries"] >= 1
    assert sc["anchored_to_click_ceiling"] is True
    assert sc["portfolio"]["observed_current_clicks"] > 0

    for row in sc["clusters"]:
        ci = row["cluster_index"]
        obs_current = row["observed_current_clicks"]
        assert obs_current >= 0
        ceiling = cc_by_cluster[ci]["ceiling_band"]
        # The winnable band is re-anchored: ceiling minus the measured current.
        exp_low = max(0, ceiling[0] - obs_current)
        exp_high = max(0, ceiling[1] - obs_current)
        assert row["observed_winnable_band"] == [
            min(exp_low, exp_high),
            max(exp_low, exp_high),
        ]


# --- AI citations override --------------------------------------------------


def test_ai_citation_share_and_split(tmp_path: Path) -> None:
    state = _run(tmp_path, FULL_STACK)
    cg = state["modules"]["live_wire"]["overrides"]["citation_grid"]
    port = cg["portfolio"]
    assert port["observed_queries"] == 4
    # Client share plus every competitor share sums to 100 (rounding aside).
    total = port["observed_citation_share"] + sum(
        d["share"] for d in port["competitor_split"]
    )
    assert total == pytest.approx(100.0, abs=0.5)
    # The competitor domains observed in the capture are surfaced.
    domains = {d["domain"] for d in port["competitor_split"]}
    assert "competitor1.com" in domains
    # The client earned at least one citation, so its share is positive.
    assert port["observed_citation_share"] > 0
    # Each cluster pairs the observed share with the expected one for comparison.
    for row in cg["clusters"]:
        assert "observed_citation_share" in row and "expected_share" in row


# --- the overlay is non-destructive -----------------------------------------


def test_offline_slots_untouched(tmp_path: Path) -> None:
    with_lw = _run(tmp_path / "with", FULL_STACK)
    without_lw = _run(tmp_path / "without", OFFLINE_STACK)
    # Live Wire writes its own slot and never edits the expected slots.
    assert with_lw["modules"]["citation_grid"] == without_lw["modules"]["citation_grid"]
    assert with_lw["modules"]["click_ceiling"] == without_lw["modules"]["click_ceiling"]
    assert without_lw["modules"]["live_wire"] is None


# --- degradation: capture alone, no prior modules ---------------------------


def test_live_wire_degrades_without_upstream(tmp_path: Path) -> None:
    state = _run(tmp_path, ("live_wire",))
    lw = state["modules"]["live_wire"]
    assert lw["reads"] == {"click_ceiling": False, "citation_grid": False}
    sc = lw["overrides"]["click_ceiling"]
    # Measured current clicks are still reported without a ceiling to anchor against.
    assert sc["anchored_to_click_ceiling"] is False
    assert sc["portfolio"]["observed_current_clicks"] > 0
    for row in sc["clusters"]:
        assert "observed_winnable_band" not in row
    # The citation share still computes from the observations alone.
    cg = lw["overrides"]["citation_grid"]
    assert cg["portfolio"]["observed_citation_share"] > 0
    for row in cg["clusters"]:
        assert row["expected_share"] is None


def test_live_wire_deterministic(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", FULL_STACK)
    b = _run(tmp_path / "b", FULL_STACK)
    assert a["modules"]["live_wire"] == b["modules"]["live_wire"]
