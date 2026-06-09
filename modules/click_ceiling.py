#!/usr/bin/env python3
"""Click Ceiling module.

Estimates, per cluster, the band of winnable monthly organic clicks: the extra
clicks the cluster could plausibly capture by improving to a realistic rank,
given a dated CTR-by-position table and the SERP features present. It reports a
band, never a single number, because a single CTR curve is a crude approximation
and the realistic target rank is itself a range.

The dated table lives in ``data/ctr_table_2026Q2.json`` and carries per-cell
provenance: ``confirmed`` cells are exact source values, ``interpolated`` and
``extrapolated`` cells are filled by a documented formula between or past the
confirmed anchors, and ``derived`` SERP-feature factors come from confirmed
position-1 layout CTRs. A keyword whose current rank sits on a non-confirmed cell
gets a wider band, so the strength of the verification governs the band width.

Per keyword the click estimate is ``volume x CTR(position | features)``. The CTR
applies the single strongest suppression among the present SERP features (not a
product, to avoid compounding uncertainty) and, on AI-Overview queries, the
measured organic-CTR suppression. The band endpoints come from a target-rank
range (an optimistic rank 1 and a conservative rank 3, never worse than the
current rank) and from the CTR-cell uncertainty.

Prior module slots sharpen the band, each optional and degrading without:

- Citation Grid readiness decides how much of the AI-Overview suppression the
  optimistic endpoint recovers (a cited, answer-ready page earns clicks back).
- Demand Pulse trend lifts the upper endpoint on rising demand and trims it on
  declining demand.
- Entity Web topical authority leans the band: high authority keeps the rank-1
  target credible, low authority trims the upside.
- Fan-Out Radar coverage trims the upside on AI-heavy clusters whose sub-query
  family is poorly covered, since the answer surface captures clicks first.

Every adjustment is recorded per cluster as a driver, so the band is auditable.
The target-rank range, the per-slot factors, and the table's filled cells are
project parameters, not search-engine facts, and are labelled as such.

This is a pure step: ``click_ceiling(run_state) -> run_state'``. It fills the
``click_ceiling`` slot and leaves everything else untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CTR_TABLE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "ctr_table_2026Q2.json"
)

# Realistic target-rank range for the winnable band. Rank 1 is the optimistic
# ceiling; rank 3 is the conservative reachable target. Never worse than the
# keyword's current rank. Project parameters, overridable through ``params``.
DEFAULT_TARGET_HIGH = 1
DEFAULT_TARGET_LOW = 3

# Demand Pulse trend adjustment on the winnable band (multiplicative). Rising and
# seasonal demand lift the upper endpoint; declining demand trims both. Parameters.
DEFAULT_DEMAND_ADJ: dict[str, dict[str, float]] = {
    "rising": {"low": 1.0, "high": 1.15},
    "seasonal": {"low": 1.0, "high": 1.05},
    "declining": {"low": 0.85, "high": 0.85},
    "flat": {"low": 1.0, "high": 1.0},
}

# Entity Web authority credibility: how much of the rank-1 upside is credible.
# Credibility = floor + (1 - floor) * authority, applied to the upper endpoint.
DEFAULT_AUTHORITY_FLOOR = 0.7

# Fan-Out coverage trim, applied to the upper endpoint only when a cluster is
# AI-heavy (most members trigger an AI Overview) and its sub-query family is
# poorly covered. Trim = floor + (1 - floor) * cover_at_tau.
DEFAULT_COVERAGE_FLOOR = 0.7
AI_HEAVY_SHARE = 0.5
LOW_COVERAGE_TAU = 0.5

# CTR-cell uncertainty by provenance: a current rank on a non-confirmed cell
# widens that keyword's band. Project parameters.
PROVENANCE_UNCERTAINTY: dict[str, float] = {
    "confirmed": 0.0,
    "interpolated": 0.15,
    "extrapolated": 0.25,
    "unranked": 0.25,
}

# SERP features that suppress organic clicks and have a derived factor in the
# table. The strongest (smallest factor) among the present features is applied.
SUPPRESSING_FEATURES = ("featured_snippet", "shopping", "knowledge_panel")

# How many example keywords to list per cluster driver, to keep run.json compact.
MAX_DRIVER_EXAMPLES = 6


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


def load_ctr_table(path: Path | None = None) -> dict[str, Any]:
    """Load the dated CTR-by-position table.

    Reads the bundled table by default. Raises ``ModuleError`` if it is missing
    or malformed, since the module cannot estimate clicks without a curve.
    """
    target = path or _CTR_TABLE_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ModuleError(f"CTR table not found: {target}") from exc
    except json.JSONDecodeError as exc:
        raise ModuleError(f"CTR table is not valid JSON: {target}") from exc
    if not isinstance(data.get("positions"), dict) or not data["positions"]:
        raise ModuleError("CTR table has no positions")
    return data


def _config(params: dict[str, Any] | None) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "target_high": DEFAULT_TARGET_HIGH,
        "target_low": DEFAULT_TARGET_LOW,
        "demand_adj": {k: dict(v) for k, v in DEFAULT_DEMAND_ADJ.items()},
        "authority_floor": DEFAULT_AUTHORITY_FLOOR,
        "coverage_floor": DEFAULT_COVERAGE_FLOOR,
        "max_driver_examples": MAX_DRIVER_EXAMPLES,
    }
    if params:
        for key in ("target_high", "target_low"):
            if isinstance(params.get(key), int) and params[key] >= 1:
                cfg[key] = params[key]
        if isinstance(params.get("authority_floor"), (int, float)):
            cfg["authority_floor"] = float(params["authority_floor"])
        if isinstance(params.get("coverage_floor"), (int, float)):
            cfg["coverage_floor"] = float(params["coverage_floor"])
        if isinstance(params.get("max_driver_examples"), int):
            cfg["max_driver_examples"] = params["max_driver_examples"]
    if cfg["target_low"] < cfg["target_high"]:
        cfg["target_low"] = cfg["target_high"]
    return cfg


# --- CTR lookup -------------------------------------------------------------


def _position_cell(position: int, table: dict[str, Any]) -> tuple[float, str]:
    """Return (ctr, provenance) for a rank, clamping outside the table."""
    positions = table["positions"]
    max_pos = max(int(p) for p in positions)
    key = str(max(1, min(position, max_pos)))
    cell = positions[key]
    # A cell with no declared provenance is treated as the most uncertain bucket, not
    # a moderately confident one, so a malformed table widens the band rather than
    # quietly understating uncertainty. The bundled table always declares provenance.
    provenance = cell.get("provenance", "extrapolated")
    if position > max_pos:
        # Past the table: floor value, treated as extrapolated.
        provenance = "extrapolated"
    return float(cell["ctr"]), provenance


def _suppression_factor(
    features: list[str], table: dict[str, Any]
) -> tuple[float, str | None]:
    """Strongest (smallest) derived suppression among present SERP features.

    Returns (factor, feature_name) or (1.0, None) when no suppressing feature is
    present. Factors are taken from the table, never multiplied together.
    """
    factors = table.get("serp_feature_factors", {})
    best = 1.0
    chosen: str | None = None
    for feature in SUPPRESSING_FEATURES:
        if feature in features:
            value = factors.get(feature, {}).get("factor")
            if isinstance(value, (int, float)) and value < best:
                best = float(value)
                chosen = feature
    return best, chosen


def _ctr(
    position: int,
    features: list[str],
    table: dict[str, Any],
    aio_recovery: float,
) -> float:
    """CTR for a rank given the SERP features, with AI-Overview handling.

    ``aio_recovery`` in [0, 1] scales the recovery from the suppressed baseline
    toward the cited-page ceiling; 0 means no recovery (not cited yet).
    """
    base, _ = _position_cell(position, table)
    factor, _ = _suppression_factor(features, table)
    ctr = base * factor
    if "ai_overview" in features:
        aio = table.get("ai_overview", {})
        mult = float(aio.get("organic_ctr_multiplier", 1.0))
        recovery_max = float(aio.get("cited_recovery_max", 1.0))
        mult *= 1.0 + max(0.0, min(1.0, aio_recovery)) * (recovery_max - 1.0)
        ctr *= mult
    return ctr


# --- prior-slot readers -----------------------------------------------------


def _readiness_by_cluster(state: dict[str, Any]) -> dict[int, float]:
    cg = (state.get("modules") or {}).get("citation_grid")
    if not isinstance(cg, dict):
        return {}
    out: dict[int, float] = {}
    for row in cg.get("clusters") or []:
        idx = row.get("cluster_index")
        readiness = row.get("expected_readiness")
        if isinstance(idx, int) and isinstance(readiness, (int, float)):
            out[idx] = max(0.0, min(1.0, float(readiness) / 100.0))
    return out


def _authority_by_cluster(state: dict[str, Any]) -> dict[int, float]:
    ew = (state.get("modules") or {}).get("entity_web")
    if not isinstance(ew, dict):
        return {}
    out: dict[int, float] = {}
    for row in ew.get("topical_authority") or []:
        idx = row.get("cluster_index")
        auth = row.get("authority")
        if isinstance(idx, int) and isinstance(auth, (int, float)):
            out[idx] = max(0.0, min(1.0, float(auth)))
    return out


def _coverage_by_cluster(state: dict[str, Any]) -> dict[int, float]:
    fo = (state.get("modules") or {}).get("fan_out_radar")
    if not isinstance(fo, dict):
        return {}
    out: dict[int, float] = {}
    for row in fo.get("clusters") or []:
        idx = row.get("cluster_index")
        cover = (row.get("coverage") or {}).get("cover_at_tau")
        if isinstance(idx, int) and isinstance(cover, (int, float)):
            out[idx] = float(cover)
    return out


def _demand_state_by_cluster(state: dict[str, Any]) -> dict[int, str]:
    dp = (state.get("modules") or {}).get("demand_pulse")
    if not isinstance(dp, dict):
        return {}
    out: dict[int, str] = {}
    for row in dp.get("clusters") or []:
        idx = row.get("cluster_index")
        label = row.get("state")
        if isinstance(idx, int) and isinstance(label, str):
            out[idx] = label
    return out


# --- per-keyword and per-cluster computation --------------------------------


def _cluster_members(
    cluster: dict[str, Any], keywords: list[dict[str, Any]]
) -> list[int]:
    return [m for m in (cluster.get("members") or []) if 0 <= m < len(keywords)]


def _keyword_band(
    keyword: dict[str, Any],
    table: dict[str, Any],
    cfg: dict[str, Any],
    readiness: float,
) -> dict[str, Any] | None:
    """Winnable-clicks band for one keyword, or None if it has no usable volume."""
    metrics = keyword.get("metrics") or {}
    volume = metrics.get("volume")
    if not isinstance(volume, (int, float)) or volume <= 0:
        return None
    volume = float(volume)
    features = [f for f in (metrics.get("serp_features") or []) if isinstance(f, str)]
    position = metrics.get("position")
    has_position = isinstance(position, int) and position >= 1

    target_high = cfg["target_high"]
    target_low = min(cfg["target_low"], position) if has_position else cfg["target_low"]
    target_low = max(target_low, target_high)

    if has_position:
        current = volume * _ctr(position, features, table, aio_recovery=0.0)
        _, prov = _position_cell(position, table)
    else:
        current = 0.0
        prov = "unranked"  # no current rank known: most uncertain, full upside
    ceiling_high = volume * _ctr(target_high, features, table, aio_recovery=readiness)
    ceiling_low = volume * _ctr(target_low, features, table, aio_recovery=0.0)

    win_high = max(0.0, ceiling_high - current)
    win_low = max(0.0, ceiling_low - current)
    win_low, win_high = min(win_low, win_high), max(win_low, win_high)

    # CTR-cell uncertainty widens the band when the current rank is not confirmed.
    unc = PROVENANCE_UNCERTAINTY.get(prov, 0.15)
    win_low *= 1.0 - unc
    win_high *= 1.0 + unc

    _, suppressor = _suppression_factor(features, table)
    return {
        "keyword": keyword.get("keyword", ""),
        "volume": int(volume),
        "position": position if has_position else None,
        "position_provenance": prov,
        "serp_features": features,
        "suppressor": suppressor,
        "ai_overview": "ai_overview" in features,
        "current_clicks": current,
        "winnable_low": win_low,
        "winnable_high": win_high,
    }


def _apply_cluster_adjusters(
    win_low: float,
    win_high: float,
    cfg: dict[str, Any],
    state_label: str | None,
    authority: float | None,
    coverage: float | None,
    ai_share: float,
) -> tuple[float, float, list[dict[str, Any]]]:
    """Apply the optional prior-slot adjusters and record each as a driver."""
    drivers: list[dict[str, Any]] = []

    if state_label and state_label in cfg["demand_adj"] and state_label != "flat":
        adj = cfg["demand_adj"][state_label]
        win_low *= adj["low"]
        win_high *= adj["high"]
        drivers.append(
            {
                "adjuster": "demand_pulse",
                "basis": f"demand state {state_label}",
                "low_factor": round(adj["low"], 4),
                "high_factor": round(adj["high"], 4),
            }
        )

    if authority is not None:
        floor = cfg["authority_floor"]
        cred = floor + (1.0 - floor) * authority
        win_high *= cred
        drivers.append(
            {
                "adjuster": "entity_web_authority",
                "basis": f"topical authority {round(authority, 4)}",
                "low_factor": 1.0,
                "high_factor": round(cred, 4),
            }
        )

    if (
        coverage is not None
        and ai_share > AI_HEAVY_SHARE
        and coverage < LOW_COVERAGE_TAU
    ):
        floor = cfg["coverage_floor"]
        trim = floor + (1.0 - floor) * coverage
        win_high *= trim
        drivers.append(
            {
                "adjuster": "fan_out_coverage",
                "basis": f"AI-heavy cluster (share {round(ai_share, 2)}) with low coverage {round(coverage, 4)}",
                "low_factor": 1.0,
                "high_factor": round(trim, 4),
            }
        )

    win_low, win_high = min(win_low, win_high), max(win_low, win_high)
    return win_low, win_high, drivers


def click_ceiling(
    state: dict[str, Any], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute the winnable-clicks band layer and write it to the run-state."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("click_ceiling needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    clusters = engine.get("clusters")
    if not isinstance(keywords, list) or not isinstance(clusters, list) or not clusters:
        raise ModuleError("engine analysis has no clusters to work on")

    cfg = _config(params)
    table_path = None
    if params and isinstance(params.get("ctr_table_path"), str):
        table_path = Path(params["ctr_table_path"])
    table = (
        params["ctr_table"]
        if (params and isinstance(params.get("ctr_table"), dict))
        else load_ctr_table(table_path)
    )
    limit = cfg["max_driver_examples"]

    readiness_by_cluster = _readiness_by_cluster(state)
    authority_by_cluster = _authority_by_cluster(state)
    coverage_by_cluster = _coverage_by_cluster(state)
    state_by_cluster = _demand_state_by_cluster(state)

    reports: list[dict[str, Any]] = []
    total_low = 0.0
    total_high = 0.0
    total_current = 0.0
    by_intent: dict[str, dict[str, float]] = {}

    for index, cluster in enumerate(clusters):
        members = _cluster_members(cluster, keywords)
        readiness = readiness_by_cluster.get(index, 0.0)

        bands = [
            band
            for band in (
                _keyword_band(keywords[m], table, cfg, readiness) for m in members
            )
            if band is not None
        ]
        raw_low = sum(b["winnable_low"] for b in bands)
        raw_high = sum(b["winnable_high"] for b in bands)
        current = sum(b["current_clicks"] for b in bands)
        ai_members = sum(1 for b in bands if b["ai_overview"])
        ai_share = ai_members / len(bands) if bands else 0.0

        adj_low, adj_high, drivers = _apply_cluster_adjusters(
            raw_low,
            raw_high,
            cfg,
            state_by_cluster.get(index),
            authority_by_cluster.get(index),
            coverage_by_cluster.get(index),
            ai_share,
        )

        # Provenance mix of the member ranks, so the band's confidence is visible.
        prov_mix: dict[str, int] = {}
        for b in bands:
            prov_mix[b["position_provenance"]] = (
                prov_mix.get(b["position_provenance"], 0) + 1
            )

        top = sorted(bands, key=lambda b: b["winnable_high"], reverse=True)[:limit]
        top_examples = [
            {
                "keyword": b["keyword"],
                "volume": b["volume"],
                "position": b["position"],
                "winnable_band": [
                    int(round(b["winnable_low"])),
                    int(round(b["winnable_high"])),
                ],
                "suppressor": b["suppressor"],
                "ai_overview": b["ai_overview"],
            }
            for b in top
        ]

        intent = cluster.get("dominant_intent", "unknown")
        bucket = by_intent.setdefault(intent, {"low": 0.0, "high": 0.0})
        bucket["low"] += adj_low
        bucket["high"] += adj_high

        current_i = int(round(current))
        winnable = [int(round(adj_low)), int(round(adj_high))]
        reports.append(
            {
                "cluster_index": index,
                "head": cluster.get("head", ""),
                "dominant_intent": intent,
                "members_scored": len(bands),
                "current_clicks_estimate": current_i,
                "ceiling_band": [current_i + winnable[0], current_i + winnable[1]],
                "winnable_band": winnable,
                "ai_overview_share": round(ai_share, 4),
                "citation_readiness": round(readiness, 4)
                if index in readiness_by_cluster
                else None,
                "position_provenance_mix": prov_mix,
                "adjusters": drivers,
                "top_opportunities": top_examples,
            }
        )
        total_low += adj_low
        total_high += adj_high
        total_current += current

    intent_summary = {
        intent: {"winnable_band": [int(round(v["low"])), int(round(v["high"]))]}
        for intent, v in sorted(by_intent.items())
    }

    state["modules"]["click_ceiling"] = {
        "mode": "expected",
        "expected_only": True,
        "ctr_table": {
            "name": table.get("meta", {}).get("name", ""),
            "version": table.get("meta", {}).get("version", ""),
            "device_scope": table.get("meta", {}).get("device_scope", ""),
            "sources": [s.get("id") for s in table.get("meta", {}).get("sources", [])],
        },
        "params": {
            "target_high": cfg["target_high"],
            "target_low": cfg["target_low"],
            "authority_floor": round(cfg["authority_floor"], 4),
            "coverage_floor": round(cfg["coverage_floor"], 4),
        },
        "reads": {
            "citation_grid": bool(readiness_by_cluster),
            "demand_pulse": bool(state_by_cluster),
            "entity_web": bool(authority_by_cluster),
            "fan_out_radar": bool(coverage_by_cluster),
        },
        "method_note": (
            "Winnable clicks are reported as a band, never a single number: a single CTR "
            "curve is a crude approximation and the realistic target rank is itself a range. "
            "Confirmed CTR cells come from a dated primary source; interpolated and "
            "extrapolated cells are filled by formula and widen the band. The target-rank "
            "range and the prior-slot adjusters are project parameters, not search-engine facts."
        ),
        "summary": {
            "clusters": len(reports),
            "current_clicks_estimate": int(round(total_current)),
            "winnable_band": [int(round(total_low)), int(round(total_high))],
            "by_intent": intent_summary,
        },
        "clusters": reports,
    }
    return state
