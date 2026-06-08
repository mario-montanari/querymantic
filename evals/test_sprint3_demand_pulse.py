#!/usr/bin/env python3
"""Sprint 3 tests: the statistics port and the Demand Pulse module.

Covers the stdlib Mann-Kendall and Theil-Sen primitives, the optional STL path,
the series CSV parser, the degraded (no-series) contract on the sample corpus, the
with-series path on a controlled state, and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.demand_pulse import (  # noqa: E402
    MIN_SERIES_POINTS,
    demand_pulse,
    load_series,
)
from spektr_core import pipeline, run_state  # noqa: E402
from spektr_core.ports.stats import (  # noqa: E402
    mann_kendall,
    stats_capabilities,
    stl_strength,
    theil_sen,
)

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
SERIES_CSV = PLUGIN_ROOT / "assets" / "series" / "sample_series.csv"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


# --- statistics port -------------------------------------------------------


def test_mann_kendall_directions() -> None:
    rising = list(range(1, 13))
    mk = mann_kendall(rising)
    assert mk["direction"] == "up"
    assert mk["p_value"] is not None and mk["p_value"] < 0.05
    assert mk["tau"] == 1.0

    falling = list(range(12, 0, -1))
    assert mann_kendall(falling)["direction"] == "down"

    flat = [100] * 12
    flat_mk = mann_kendall(flat)
    assert flat_mk["s"] == 0
    # An all-tie series has no defined p-value, so it is never called significant.
    assert flat_mk["p_value"] is None

    assert mann_kendall([1, 2])["p_value"] is None  # too short


def test_theil_sen_slope() -> None:
    values = [2 * x + 5 for x in range(10)]
    ts = theil_sen(values)
    assert abs(ts["slope"] - 2.0) < 1e-9
    assert abs(ts["intercept"] - 5.0) < 1e-9


def test_stl_capability_and_degradation() -> None:
    caps = stats_capabilities()
    assert set(caps) == {"stl"}
    assert isinstance(caps["stl"], bool)
    if not caps["stl"]:
        out = stl_strength([1.0] * 24, 12)
        assert out["available"] is False


# --- series parser ---------------------------------------------------------


def test_load_series_shape() -> None:
    series = load_series(SERIES_CSV)
    assert len(series["periods"]) == 24
    assert series["periods"] == sorted(series["periods"])
    assert "running shoes" in series["by_keyword"]
    assert len(series["by_keyword"]["running shoes"]) == 24


# --- degraded (no-series) path on the sample corpus ------------------------


def _run(tmp: Path, modules: tuple[str, ...], module_kwargs=None) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs=module_kwargs,
    )


def test_demand_pulse_degraded_contract(tmp_path: Path) -> None:
    _run(tmp_path, ("demand_pulse",))
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["spektr"]["modules_run"] == ["demand_pulse"]

    dp = loaded["modules"]["demand_pulse"]
    assert dp["series"]["source"] == "none"
    assert dp["clusters"]
    # With no series, every cluster is unknown and carries no trend block.
    for cluster in dp["clusters"]:
        assert cluster["state"] == "unknown"
        assert cluster["trend"] is None
        assert cluster["series_points"] == 0
    assert dp["summary"]["states"].get("unknown") == len(dp["clusters"])


# --- with-series path on a controlled state --------------------------------


def _mini_state(member_series: dict[str, list[float]]) -> dict:
    keywords = [
        {"keyword": name, "scopes": {"seasonality": {"label": "evergreen"}}}
        for name in member_series
    ]
    clusters = [{"head": "head term", "members": list(range(len(keywords)))}]
    periods = [f"2025-{m:02d}" for m in range(1, 13)]
    by_keyword = {name: list(vals) for name, vals in member_series.items()}
    state = {
        "spektr": {"generated_at": FIXED_TIMESTAMP},
        "engine": {"keywords": keywords, "clusters": clusters},
        "modules": {"demand_pulse": None},
    }
    series = {"periods": periods, "by_keyword": by_keyword}
    return state, series


def test_demand_pulse_classifies_rising() -> None:
    state, series = _mini_state({"alpha term": [100 + 10 * i for i in range(12)]})
    out = demand_pulse(state, series=series)
    cluster = out["modules"]["demand_pulse"]["clusters"][0]
    assert cluster["series_points"] == 12
    assert cluster["state"] == "rising"
    assert cluster["trend"]["theil_sen"]["slope"] > 0
    assert cluster["momentum"] is not None and cluster["momentum"] > 0


def test_demand_pulse_classifies_flat() -> None:
    state, series = _mini_state({"alpha term": [100] * 12})
    out = demand_pulse(state, series=series)
    cluster = out["modules"]["demand_pulse"]["clusters"][0]
    assert cluster["series_points"] >= MIN_SERIES_POINTS
    assert cluster["state"] == "flat"


# --- integration with the sample series ------------------------------------


def test_demand_pulse_with_sample_series(tmp_path: Path) -> None:
    series = load_series(SERIES_CSV)
    kwargs = {"demand_pulse": {"series": series}}
    state = _run(tmp_path, ("demand_pulse",), module_kwargs=kwargs)
    dp = state["modules"]["demand_pulse"]
    assert dp["series"]["source"] == "external_csv"
    # The sample series feeds the running-shoes clusters, so at least one cluster
    # leaves the unknown state and carries a real trend block.
    moved = [c for c in dp["clusters"] if c["state"] != "unknown"]
    assert moved, "expected at least one cluster with a computed trend"
    assert any(c["trend"] is not None for c in moved)
    assert dp["summary"]["with_series"] >= 1


def test_demand_pulse_deterministic(tmp_path: Path) -> None:
    series = load_series(SERIES_CSV)
    kwargs = {"demand_pulse": {"series": series}}
    a = _run(tmp_path / "a", ("demand_pulse",), module_kwargs=kwargs)
    b = _run(tmp_path / "b", ("demand_pulse",), module_kwargs=kwargs)
    assert a["modules"]["demand_pulse"] == b["modules"]["demand_pulse"]
