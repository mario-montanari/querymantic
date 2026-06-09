#!/usr/bin/env python3
"""Demand Pulse module.

Classifies the demand trend of each cluster from a monthly volume series:

- Mann-Kendall for the direction and its significance.
- Theil-Sen for a robust slope (the magnitude of the move).
- Momentum: the recent window mean against the preceding window mean.
- Seasonal strength from an STL decomposition, only when statsmodels is present.

The canonical engine state carries one volume per keyword, not a series, so a
series is an optional second input. When it is absent, every cluster is reported
as ``unknown`` (the trend cannot be computed), and a separate ``seasonal_marker``
flag is lifted from the engine's marker-based seasonality scope, clearly labelled
as marker-derived, not series-derived. The default sample run, which has volume
only, exercises this degraded path.

The series is an input, not derived state, so it is never written into
``run.json``; only the computed results are. The run-state therefore stays within
its schema.

This is a pure step: ``demand_pulse(run_state, series=...) -> run_state'``. It
fills the ``demand_pulse`` slot and leaves the rest untouched. The series, when
used, is passed as a parsed mapping (see ``load_series``).
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from querymantic.ports.stats import (
    mann_kendall,
    stats_capabilities,
    stl_strength,
    theil_sen,
)
from querymantic.text import tokenize

# Significance level for the Mann-Kendall test. The conventional 0.05; a parameter,
# not a magic number, and overridable through ``params``.
MK_ALPHA = 0.05

# Fewest points a trend test runs on. Below this a Mann-Kendall result is too noisy
# to trust, so the cluster stays ``unknown``. A chosen parameter.
MIN_SERIES_POINTS = 8

# Window, in periods, for the momentum ratio (recent mean over preceding mean).
MOMENTUM_WINDOW = 3

# Seasonal-strength cutoff above which a cluster is called ``seasonal``. A project
# parameter in [0, 1]; not a value taken from any source.
SEASONAL_STRENGTH_MIN = 0.5

# Assumed series period for STL. Monthly data, so twelve.
STL_PERIOD = 12

# A period column in the series CSV is a YYYY-MM header.
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


class DemandPulseError(Exception):
    """Raised when the optional series input cannot be parsed."""


def _norm(text: str) -> str:
    """Normalise a keyword for joining the series to the engine corpus."""
    return " ".join(tokenize(text))


def _parse_value(cell: str, path: Path, row: int) -> float:
    raw = cell.replace(",", "").replace(" ", "")
    try:
        value = float(raw)
    except ValueError as exc:
        raise DemandPulseError(
            f"{path} row {row}: non-numeric series value {cell!r}"
        ) from exc
    if value < 0:
        raise DemandPulseError(f"{path} row {row}: negative series value {cell!r}")
    return value


def load_series(path: Path) -> dict[str, Any]:
    """Parse a wide monthly-series CSV into a mapping the module can use.

    Expected shape: a ``keyword`` column (or the first column) followed by one
    column per month, each header in ``YYYY-MM`` form. Cells may be empty (the
    point is skipped for that keyword). Returns
    ``{"periods": [...], "by_keyword": {normalised_keyword: [value | None, ...]}}``
    with periods sorted chronologically.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise DemandPulseError(f"cannot read series file: {path}") from exc

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise DemandPulseError(f"series file is empty: {path}")

    header = rows[0]
    keyword_col = 0
    for i, name in enumerate(header):
        if name.strip().lower() == "keyword":
            keyword_col = i
            break

    period_cols = [
        (i, name.strip())
        for i, name in enumerate(header)
        if _PERIOD_RE.match(name.strip())
    ]
    if len(period_cols) < 2:
        raise DemandPulseError(
            f"series file needs at least two YYYY-MM columns: {path}"
        )
    period_cols.sort(key=lambda c: c[1])
    periods = [name for _, name in period_cols]

    by_keyword: dict[str, list[float | None]] = {}
    for row_index, row in enumerate(rows[1:], start=2):
        if len(row) <= keyword_col:
            continue
        raw_keyword = row[keyword_col].strip()
        if not raw_keyword:
            continue
        key = _norm(raw_keyword)
        if not key:
            continue
        values: list[float | None] = []
        for col, _ in period_cols:
            cell = row[col].strip() if col < len(row) else ""
            values.append(None if cell == "" else _parse_value(cell, path, row_index))
        by_keyword[key] = values

    if not by_keyword:
        raise DemandPulseError(f"series file has no usable rows: {path}")
    return {"periods": periods, "by_keyword": by_keyword}


def _config(params: dict[str, Any] | None) -> dict[str, Any]:
    cfg = {
        "alpha": MK_ALPHA,
        "min_series_points": MIN_SERIES_POINTS,
        "momentum_window": MOMENTUM_WINDOW,
        "seasonal_strength_min": SEASONAL_STRENGTH_MIN,
        "stl_period": STL_PERIOD,
    }
    if params:
        for key in cfg:
            if key in params:
                cfg[key] = params[key]
    # An STL period below 2 is not a seasonal cycle; the strength estimator would
    # report itself unavailable and silently downgrade classification, so reject it
    # rather than accept a value that quietly disables seasonality.
    if int(cfg["stl_period"]) < 2:
        raise ModuleError("stl_period must be an integer of 2 or more")
    if int(cfg["momentum_window"]) < 1:
        raise ModuleError("momentum_window must be an integer of 1 or more")
    return cfg


def _series_parts(series: Any) -> tuple[list[str], dict[str, list[float | None]]]:
    if series is None:
        return [], {}
    if isinstance(series, dict) and "by_keyword" in series:
        return list(series.get("periods") or []), dict(series.get("by_keyword") or {})
    raise ModuleError("series must be a mapping with 'periods' and 'by_keyword'")


def _seasonality_label(keyword: dict[str, Any]) -> str:
    scope = (keyword.get("scopes") or {}).get("seasonality") or {}
    label = scope.get("label", "")
    return label if isinstance(label, str) else ""


def _momentum(values: list[float], window: int) -> float | None:
    if window < 1 or len(values) < 2 * window:
        return None
    recent = mean(values[-window:])
    prior = mean(values[-2 * window : -window])
    if prior == 0:
        return None
    return round(recent / prior - 1.0, 6)


def _classify(
    mk: dict[str, Any],
    ts: dict[str, Any],
    seasonal_strength: float | None,
    cfg: dict[str, Any],
) -> str:
    if (
        seasonal_strength is not None
        and seasonal_strength >= cfg["seasonal_strength_min"]
    ):
        return "seasonal"
    p_value = mk.get("p_value")
    slope = ts.get("slope", 0.0)
    if p_value is not None and p_value < cfg["alpha"]:
        if slope > 0:
            return "rising"
        if slope < 0:
            return "declining"
    return "flat"


def _aggregate_cluster_series(
    members: list[int],
    keywords: list[dict[str, Any]],
    periods: list[str],
    by_keyword: dict[str, list[float | None]],
) -> list[float]:
    """Sum the member series per period, keeping periods with at least one value.

    Summing is the demand-weighted aggregation: high-volume keywords contribute
    proportionally more absolute volume to the cluster total.
    """
    member_series = []
    for m in members:
        key = _norm(keywords[m].get("keyword", ""))
        s = by_keyword.get(key)
        if s:
            member_series.append(s)
    if not member_series:
        return []
    aggregated: list[float] = []
    for pos in range(len(periods)):
        present = [s[pos] for s in member_series if pos < len(s) and s[pos] is not None]
        if present:
            aggregated.append(float(sum(present)))
    return aggregated


def _analyse_cluster(
    index: int,
    cluster: dict[str, Any],
    keywords: list[dict[str, Any]],
    periods: list[str],
    by_keyword: dict[str, list[float | None]],
    cfg: dict[str, Any],
    caps: dict[str, bool],
) -> dict[str, Any]:
    members = [m for m in (cluster.get("members") or []) if 0 <= m < len(keywords)]
    marker_counts = Counter(_seasonality_label(keywords[m]) for m in members)
    marker_counts.pop("", None)
    seasonal_marker = marker_counts.get("seasonal", 0) > 0

    aggregated = _aggregate_cluster_series(members, keywords, periods, by_keyword)
    n = len(aggregated)

    trend: dict[str, Any] | None = None
    momentum: float | None = None
    seasonal_strength: float | None = None

    if n >= cfg["min_series_points"]:
        mk = mann_kendall(aggregated)
        ts = theil_sen(aggregated)
        trend = {"mann_kendall": mk, "theil_sen": ts}
        momentum = _momentum(aggregated, cfg["momentum_window"])
        if caps["stl"] and n >= 2 * cfg["stl_period"]:
            strength = stl_strength(aggregated, cfg["stl_period"])
            if strength.get("available"):
                seasonal_strength = strength["seasonal_strength"]
        state = _classify(mk, ts, seasonal_strength, cfg)
        note = ""
    else:
        state = "unknown"
        note = "no usable series for this cluster's keywords; trend not computed"

    return {
        "cluster_index": index,
        "head": cluster.get("head", ""),
        "state": state,
        "series_points": n,
        "trend": trend,
        "momentum": momentum,
        "seasonal_strength": seasonal_strength,
        "seasonal_marker": seasonal_marker,
        "marker_label_counts": dict(marker_counts),
        "note": note,
    }


def demand_pulse(
    state: dict[str, Any],
    series: Any = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the per-cluster demand state and write it to the run-state."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("demand_pulse needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    clusters = engine.get("clusters")
    if not isinstance(keywords, list) or not isinstance(clusters, list) or not clusters:
        raise ModuleError("engine analysis has no clusters to work on")

    cfg = _config(params)
    caps = stats_capabilities()
    periods, by_keyword = _series_parts(series)

    reports: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    seasonal_markers = 0
    with_series = 0
    for index, cluster in enumerate(clusters):
        report = _analyse_cluster(
            index, cluster, keywords, periods, by_keyword, cfg, caps
        )
        reports.append(report)
        state_counts[report["state"]] += 1
        if report["seasonal_marker"]:
            seasonal_markers += 1
        if report["series_points"] >= cfg["min_series_points"]:
            with_series += 1

    state["modules"]["demand_pulse"] = {
        "params": cfg,
        "params_note": (
            "alpha, min_series_points, momentum_window, and seasonal_strength_min "
            "are parameters, not search-engine facts. Defaults are documented in the "
            "methodology reference."
        ),
        "stats_backend": {
            "mann_kendall": "stdlib",
            "theil_sen": "stdlib",
            "stl": "statsmodels" if caps["stl"] else "unavailable",
        },
        "series": {
            "source": "external_csv" if by_keyword else "none",
            "periods": periods,
            "keywords_with_series": len(by_keyword),
        },
        "summary": {
            "clusters": len(reports),
            "with_series": with_series,
            "states": dict(state_counts),
            "seasonal_markers": seasonal_markers,
        },
        "method_note": (
            "Mann-Kendall significance can be overstated when monthly demand is "
            "autocorrelated; the base test is used here, and a variance correction "
            "is a future option. Seasonal strength is computed only when STL is "
            "available. seasonal_marker is derived from keyword markers in the "
            "engine, not from the series."
        ),
        "clusters": reports,
    }
    return state
