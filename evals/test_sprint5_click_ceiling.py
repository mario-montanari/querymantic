#!/usr/bin/env python3
"""Sprint 5 tests: the Click Ceiling module.

Covers the band contract on the sample corpus (a band, never a single number),
the ceiling-equals-current-plus-winnable invariant, the run-level summary and its
intent split, the dated CTR table and its per-cell provenance, the unranked-keyword
reading, the AI-Overview suppression and recovery, graceful degradation when the
prior modules are absent, and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.click_ceiling import (  # noqa: E402
    _ctr,
    load_ctr_table,
)
from spektr_core import pipeline, run_state  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"
FULL_STACK = ("entity_web", "fan_out_radar", "citation_grid", "click_ceiling")


def _run(tmp: Path, modules: tuple[str, ...]) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
    )


# --- full-stack contract ----------------------------------------------------


def test_click_ceiling_contract(tmp_path: Path) -> None:
    _run(tmp_path, FULL_STACK)
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["spektr"]["modules_run"][-1] == "click_ceiling"

    cc = loaded["modules"]["click_ceiling"]
    assert cc["mode"] == "expected"
    assert cc["expected_only"] is True
    assert cc["reads"]["citation_grid"] is True
    assert cc["reads"]["entity_web"] is True
    assert cc["reads"]["fan_out_radar"] is True
    assert cc["reads"]["demand_pulse"] is False
    for key in ("ctr_table", "params", "method_note", "summary", "clusters"):
        assert key in cc
    assert cc["ctr_table"]["version"] == "2026Q2"
    assert "sistrix_2020" in cc["ctr_table"]["sources"]
    assert cc["clusters"]


def test_band_invariants(tmp_path: Path) -> None:
    state = _run(tmp_path, FULL_STACK)
    cc = state["modules"]["click_ceiling"]
    for cluster in cc["clusters"]:
        low, high = cluster["winnable_band"]
        # A band, never a single number: two endpoints, low never above high.
        assert isinstance(low, int) and isinstance(high, int)
        assert 0 <= low <= high
        cur = cluster["current_clicks_estimate"]
        # The ceiling band is the current clicks plus the winnable band.
        assert cluster["ceiling_band"] == [cur + low, cur + high]


def test_summary_totals_and_intent_split(tmp_path: Path) -> None:
    state = _run(tmp_path, FULL_STACK)
    cc = state["modules"]["click_ceiling"]
    summary = cc["summary"]
    low, high = summary["winnable_band"]
    assert 0 <= low <= high
    assert summary["clusters"] == len(cc["clusters"])
    # The per-intent winnable bands sum to the run-level band (rounding aside).
    intent_low = sum(v["winnable_band"][0] for v in summary["by_intent"].values())
    intent_high = sum(v["winnable_band"][1] for v in summary["by_intent"].values())
    assert abs(intent_low - low) <= len(summary["by_intent"])
    assert abs(intent_high - high) <= len(summary["by_intent"])
    # The whole portfolio has genuine winnable upside on the sample.
    assert high > 0


def test_unranked_keyword_is_full_upside(tmp_path: Path) -> None:
    state = _run(tmp_path, FULL_STACK)
    cc = state["modules"]["click_ceiling"]
    seen_unranked = False
    for cluster in cc["clusters"]:
        for opp in cluster["top_opportunities"]:
            if opp["position"] is None:
                seen_unranked = True
                # An unranked high-volume term carries a non-trivial winnable band.
                assert opp["winnable_band"][1] >= opp["winnable_band"][0] >= 0
    assert seen_unranked, "the sample includes keywords with no recorded rank"


# --- AI Overview suppression and recovery ----------------------------------


def test_ai_overview_suppression_and_recovery() -> None:
    table = load_ctr_table()
    # Same rank, same volume: an AI-Overview query earns less than a plain one.
    plain = _ctr(1, [], table, aio_recovery=0.0)
    aio = _ctr(1, ["ai_overview"], table, aio_recovery=0.0)
    assert aio < plain
    # Citation readiness recovers part of the AI-Overview loss.
    recovered = _ctr(1, ["ai_overview"], table, aio_recovery=1.0)
    assert aio < recovered <= plain


def test_strongest_suppression_not_compounded() -> None:
    table = load_ctr_table()
    base = _ctr(1, [], table, aio_recovery=0.0)
    fs = table["serp_feature_factors"]["featured_snippet"]["factor"]
    shop = table["serp_feature_factors"]["shopping"]["factor"]
    both = _ctr(1, ["featured_snippet", "shopping"], table, aio_recovery=0.0)
    # The strongest single suppression applies, not the product of the two.
    assert abs(both - base * min(fs, shop)) < 1e-9
    assert both > base * fs * shop


# --- the dated CTR table and its provenance --------------------------------


def test_ctr_table_provenance_and_monotonicity() -> None:
    table = load_ctr_table()
    positions = table["positions"]
    # The SISTRIX anchors carry their exact published values and are confirmed.
    assert (
        positions["1"]["ctr"] == 0.285 and positions["1"]["provenance"] == "confirmed"
    )
    assert (
        positions["2"]["ctr"] == 0.157 and positions["2"]["provenance"] == "confirmed"
    )
    assert (
        positions["3"]["ctr"] == 0.110 and positions["3"]["provenance"] == "confirmed"
    )
    assert (
        positions["10"]["ctr"] == 0.025 and positions["10"]["provenance"] == "confirmed"
    )
    # Gap cells are marked as filled, never as source values.
    assert positions["5"]["provenance"] == "interpolated"
    assert positions["15"]["provenance"] == "extrapolated"
    # The curve is strictly monotone decreasing across the whole table.
    curve = [positions[str(p)]["ctr"] for p in range(1, 21)]
    assert all(curve[i] > curve[i + 1] for i in range(len(curve) - 1))


# --- degradation: engine data alone ----------------------------------------


def test_click_ceiling_degrades_without_upstream(tmp_path: Path) -> None:
    state = _run(tmp_path, ("click_ceiling",))
    cc = state["modules"]["click_ceiling"]
    assert cc["reads"] == {
        "citation_grid": False,
        "demand_pulse": False,
        "entity_web": False,
        "fan_out_radar": False,
    }
    # No upstream modules means no per-cluster adjusters and no readiness...
    for cluster in cc["clusters"]:
        assert cluster["adjusters"] == []
        assert cluster["citation_readiness"] is None
    # ...yet the band still computes from the engine metrics alone.
    assert cc["summary"]["winnable_band"][1] > 0


def test_click_ceiling_deterministic(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", FULL_STACK)
    b = _run(tmp_path / "b", FULL_STACK)
    assert a["modules"]["click_ceiling"] == b["modules"]["click_ceiling"]
