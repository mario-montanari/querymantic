#!/usr/bin/env python3
"""Sprint 4 tests: the Citation Grid module.

Covers the expected-only contract on the sample corpus, the six-component
checklist, the readiness blend and its graceful degradation when upstream modules
are absent, the freshness signal when Demand Pulse has run, the within-portfolio
expected share, and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.citation_grid import (  # noqa: E402
    COMPONENTS,
    DEFAULT_WEIGHTS,
    citation_grid,
)
from modules.demand_pulse import load_series  # noqa: E402
from spektr_core import pipeline, run_state  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
SERIES_CSV = PLUGIN_ROOT / "assets" / "series" / "sample_series.csv"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def _run(tmp: Path, modules: tuple[str, ...], module_kwargs=None) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs=module_kwargs,
    )


# --- full-stack contract on the sample corpus ------------------------------


def test_citation_grid_contract(tmp_path: Path) -> None:
    _run(tmp_path, ("entity_web", "fan_out_radar", "citation_grid"))
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["spektr"]["modules_run"] == [
        "entity_web",
        "fan_out_radar",
        "citation_grid",
    ]

    cg = loaded["modules"]["citation_grid"]
    assert cg["mode"] == "expected"
    assert cg["expected_only"] is True
    assert cg["reads"]["entity_web"] is True
    assert cg["reads"]["fan_out_radar"] is True
    assert cg["reads"]["demand_pulse"] is False
    for key in ("params", "components", "positioning_note", "method_note", "summary", "clusters"):
        assert key in cg
    assert cg["clusters"]
    # The six components are reported in methodology order, two checklist-only.
    assert [c["name"] for c in cg["components"]] == [name for name, _ in COMPONENTS]
    assert cg["summary"]["scored_components"] == 4
    assert cg["summary"]["checklist_only_components"] == 2


def test_readiness_bounds_and_checklist(tmp_path: Path) -> None:
    state = _run(tmp_path, ("entity_web", "fan_out_radar", "citation_grid"))
    cg = state["modules"]["citation_grid"]
    for cluster in cg["clusters"]:
        assert 0.0 <= cluster["expected_readiness"] <= 100.0
        # Every cluster carries the full six-component checklist.
        components = [item["component"] for item in cluster["checklist"]]
        assert components == [
            "extractability",
            "entity_coverage",
            "structured_signals",
            "information_gain",
            "freshness_proxy",
            "source_cues",
        ]
        # The two text-only components are flagged as needing passage text.
        by_name = {item["component"]: item for item in cluster["checklist"]}
        assert by_name["information_gain"]["requires"] == "passage_text"
        assert by_name["source_cues"]["requires"] == "passage_text"


def test_expected_share_is_a_portfolio_distribution(tmp_path: Path) -> None:
    state = _run(tmp_path, ("entity_web", "fan_out_radar", "citation_grid"))
    clusters = state["modules"]["citation_grid"]["clusters"]
    shares = [c["expected_share"] for c in clusters]
    assert all(s >= 0.0 for s in shares)
    # Shares form a within-portfolio distribution that sums to about 100.
    assert abs(sum(shares) - 100.0) < 0.01
    # A cluster with no demand contributes no share even with high readiness.
    zero_demand = [c for c in clusters if c["demand"] == 0]
    for cluster in zero_demand:
        assert cluster["expected_share"] == 0.0


# --- degradation: engine scopes alone still produce a readiness ------------


def test_citation_grid_degrades_without_upstream(tmp_path: Path) -> None:
    state = _run(tmp_path, ("citation_grid",))
    cg = state["modules"]["citation_grid"]
    assert cg["reads"] == {
        "entity_web": False,
        "fan_out_radar": False,
        "demand_pulse": False,
    }
    cluster = cg["clusters"][0]
    inputs = cluster["readiness_inputs"]
    # Without upstream modules these inputs have no value...
    assert inputs["query_family"]["available"] is False
    assert inputs["entity_coverage"]["available"] is False
    assert inputs["freshness"]["available"] is False
    # ...yet the engine scopes still produce a finite readiness.
    assert inputs["eligibility"]["available"] is True
    assert cluster["expected_readiness"] > 0.0


# --- freshness signal arrives only with Demand Pulse -----------------------


def test_freshness_signal_with_demand_pulse(tmp_path: Path) -> None:
    series = load_series(SERIES_CSV)
    kwargs = {"demand_pulse": {"series": series}}
    state = _run(
        tmp_path,
        ("entity_web", "fan_out_radar", "demand_pulse", "citation_grid"),
        module_kwargs=kwargs,
    )
    cg = state["modules"]["citation_grid"]
    assert cg["reads"]["demand_pulse"] is True
    fresh = [
        c for c in cg["clusters"] if c["readiness_inputs"]["freshness"]["available"]
    ]
    # The sample series moves a few clusters off unknown, so freshness becomes
    # available for them and stays absent for the rest.
    assert fresh, "expected at least one cluster with a freshness signal"
    for cluster in fresh:
        assert cluster["readiness_inputs"]["freshness"]["value"] is not None


# --- weights and renormalisation -------------------------------------------


def test_weights_renormalise_over_available_inputs(tmp_path: Path) -> None:
    state = _run(tmp_path, ("entity_web", "fan_out_radar", "citation_grid"))
    cluster = state["modules"]["citation_grid"]["clusters"][0]
    inputs = cluster["readiness_inputs"]
    effective = sum(i["effective_weight"] for i in inputs.values() if i["available"])
    # The effective weights of the present inputs sum to one.
    assert abs(effective - 1.0) < 1e-6
    # The default weights are the documented six-input blend.
    assert set(DEFAULT_WEIGHTS) == set(inputs)


def test_citation_grid_deterministic(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", ("entity_web", "fan_out_radar", "citation_grid"))
    b = _run(tmp_path / "b", ("entity_web", "fan_out_radar", "citation_grid"))
    assert a["modules"]["citation_grid"] == b["modules"]["citation_grid"]
