#!/usr/bin/env python3
"""The shared report view for Output Forge.

All four renderers read the same normalised view, built once from the run-state,
so a deck, a Word audit, an Excel workbook, and an HTML dashboard never disagree on
a figure. This module is where the run-state's nested slots are flattened into a
flat, render-ready shape, and where the one cross-cutting rule lives: when Live Wire
has placed an observed value next to an expected one, the view marks the observed
value as the headline and keeps the expected one beside it. The renderers present;
they do not recompute.

The view is plain data (dicts and lists) and is deterministic: every derived float
is rounded, and clusters are ordered by demand so two runs on the same input yield
the same view. It reads each module slot defensively and simply omits a section when
the module behind it did not run, mirroring the suite's degrade-not-break rule.
"""

from __future__ import annotations

from typing import Any

# How many rows to surface in the "top" lists the renderers lead with.
TOP_CLUSTERS = 12
TOP_GAPS = 12
TOP_OPPORTUNITIES = 10

# Rounding for the rendered figures. The run-state keeps full precision in its module
# slots; the deliverable shows rounded values so it never claims a precision the
# estimate does not have. Fractions that feed a percentage formatter keep enough
# decimals for a one-decimal percent (``_round``); a 0-to-100 score shows one decimal
# (``_score``); a 0-to-1 ratio shown raw shows two (``_ratio``).
_ROUND = 4
_SCORE_ROUND = 1
_RATIO_ROUND = 2


def _round(value: Any) -> Any:
    return (
        round(float(value), _ROUND)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else value
    )


def _score(value: Any) -> Any:
    """Round a 0-to-100 score to one decimal, matching the dashboard cards."""
    return (
        round(float(value), _SCORE_ROUND)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else value
    )


def _ratio(value: Any) -> Any:
    """Round a 0-to-1 ratio shown raw to two decimals, avoiding false precision."""
    return (
        round(float(value), _RATIO_ROUND)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else value
    )


def _slot(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    slot = (state.get("modules") or {}).get(name)
    return slot if isinstance(slot, dict) else None


def _by_cluster(
    slot: dict[str, Any] | None, key: str = "clusters"
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not slot:
        return out
    for row in slot.get(key) or []:
        idx = row.get("cluster_index")
        if isinstance(idx, int):
            out[idx] = row
    return out


def _authority_by_cluster(
    entity_web: dict[str, Any] | None,
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not entity_web:
        return out
    for row in entity_web.get("topical_authority") or []:
        idx = row.get("cluster_index")
        if isinstance(idx, int):
            out[idx] = row
    return out


def _header(state: dict[str, Any]) -> dict[str, Any]:
    querymantic = state.get("querymantic") or {}
    engine = state.get("engine") or {}
    meta = engine.get("run_metadata") or {}
    return {
        "label": str(meta.get("label", "") or ""),
        "generated_at": str(querymantic.get("generated_at", "")),
        "input_hash": str(querymantic.get("input_hash", "")),
        "input_files": len(querymantic.get("inputs") or []),
        "plugin_version": str(querymantic.get("plugin_version", "")),
        "schema_version": str(querymantic.get("schema_version", "")),
        "modules_run": list(querymantic.get("modules_run") or []),
    }


def _corpus(state: dict[str, Any]) -> dict[str, Any]:
    cs = (state.get("engine") or {}).get("corpus_summary") or {}
    by_intent = cs.get("by_intent") or {}
    intent_rows = sorted(
        ({"intent": k, "count": int(v)} for k, v in by_intent.items()),
        key=lambda r: (-r["count"], r["intent"]),
    )
    return {
        "total_keywords": cs.get("total_keywords"),
        "intent_split": intent_rows,
        "by_language": dict(sorted((cs.get("by_language") or {}).items())),
        "by_source": dict(sorted((cs.get("by_source") or {}).items())),
        "aio_eligibility_share": _round(cs.get("aio_eligibility_share")),
        "geo_opportunity_share": _round(cs.get("geo_opportunity_share")),
        "demand_opportunity_score": _score(cs.get("demand_opportunity_score")),
    }


def _clusters(state: dict[str, Any]) -> list[dict[str, Any]]:
    engine = state.get("engine") or {}
    engine_clusters = engine.get("clusters") or []

    authority = _authority_by_cluster(_slot(state, "entity_web"))
    fan_out = _by_cluster(_slot(state, "fan_out_radar"))
    citation = _by_cluster(_slot(state, "citation_grid"))
    ceiling = _by_cluster(_slot(state, "click_ceiling"))
    pulse = _by_cluster(_slot(state, "demand_pulse"))

    live = _slot(state, "live_wire")
    observed_clicks = (
        _by_cluster((live or {}).get("overrides", {}).get("click_ceiling"))
        if live
        else {}
    )
    observed_cites = (
        _by_cluster((live or {}).get("overrides", {}).get("citation_grid"))
        if live
        else {}
    )

    rows: list[dict[str, Any]] = []
    for idx, cluster in enumerate(engine_clusters):
        row: dict[str, Any] = {
            "cluster_index": idx,
            "head": str(cluster.get("head", "")),
            "size": cluster.get("size"),
            "volume_total": cluster.get("volume_total"),
            "dominant_intent": str(cluster.get("dominant_intent", "")),
        }
        if idx in authority:
            row["topical_authority"] = _ratio(authority[idx].get("authority"))
        if idx in fan_out:
            cov = fan_out[idx].get("coverage") or {}
            row["cover_at_tau"] = _ratio(cov.get("cover_at_tau"))
            row["missing_archetypes"] = list(
                fan_out[idx].get("missing_archetypes") or []
            )
        if idx in citation:
            row["expected_readiness"] = _score(citation[idx].get("expected_readiness"))
            row["expected_share"] = _score(citation[idx].get("expected_share"))
        if idx in ceiling:
            band = ceiling[idx].get("winnable_band") or []
            row["winnable_band"] = (
                [int(band[0]), int(band[1])] if len(band) == 2 else None
            )
            row["current_clicks_estimate"] = ceiling[idx].get("current_clicks_estimate")
            row["ai_overview_share"] = _round(ceiling[idx].get("ai_overview_share"))
        if idx in pulse:
            row["demand_state"] = str(pulse[idx].get("state", "")) or None
        # Observed values override the headline when Live Wire measured them.
        if idx in observed_clicks:
            oc = observed_clicks[idx]
            row["observed_current_clicks"] = oc.get("observed_current_clicks")
            ob = oc.get("observed_winnable_band")
            if isinstance(ob, list) and len(ob) == 2:
                row["observed_winnable_band"] = [int(ob[0]), int(ob[1])]
        if idx in observed_cites:
            row["observed_citation_share"] = _round(
                observed_cites[idx].get("observed_citation_share")
            )
        rows.append(row)

    rows.sort(key=lambda r: (-(r.get("volume_total") or 0), r["cluster_index"]))
    return rows


def _winnable(state: dict[str, Any]) -> dict[str, Any] | None:
    cc = _slot(state, "click_ceiling")
    if not cc:
        return None
    summary = cc.get("summary") or {}
    by_intent = summary.get("by_intent") or {}
    intent_rows = []
    for intent, payload in sorted(by_intent.items()):
        band = (payload or {}).get("winnable_band") or []
        if len(band) == 2:
            intent_rows.append(
                {"intent": intent, "winnable_band": [int(band[0]), int(band[1])]}
            )
    band = summary.get("winnable_band") or []
    out: dict[str, Any] = {
        "portfolio_winnable_band": [int(band[0]), int(band[1])]
        if len(band) == 2
        else None,
        "current_clicks_estimate": summary.get("current_clicks_estimate"),
        "by_intent": intent_rows,
    }
    live = _slot(state, "live_wire")
    sc = (
        (live or {}).get("overrides", {}).get("click_ceiling", {}).get("portfolio")
        if live
        else None
    )
    if isinstance(sc, dict) and "observed_current_clicks" in sc:
        out["observed_current_clicks"] = sc.get("observed_current_clicks")
        ob = sc.get("observed_winnable_band")
        if isinstance(ob, list) and len(ob) == 2:
            out["observed_winnable_band"] = [int(ob[0]), int(ob[1])]
    return out


def _readiness(state: dict[str, Any]) -> dict[str, Any] | None:
    cg = _slot(state, "citation_grid")
    if not cg:
        return None
    summary = cg.get("summary") or {}
    return {
        "mean_expected_readiness": _score(summary.get("mean_expected_readiness")),
        "scored_components": summary.get("scored_components"),
        "checklist_only_components": summary.get("checklist_only_components"),
        "expected_only": bool(cg.get("expected_only", True)),
    }


def _gaps(state: dict[str, Any]) -> list[dict[str, Any]]:
    ew = _slot(state, "entity_web")
    if not ew:
        return []
    gaps = []
    for g in ew.get("entity_gaps") or []:
        gaps.append(
            {
                "entity": str(g.get("entity", "")),
                "demand_volume": g.get("demand_volume"),
                "suggested_cluster_head": str(g.get("suggested_cluster_head", "")),
            }
        )
    gaps.sort(key=lambda r: (-(r.get("demand_volume") or 0), r["entity"]))
    return gaps[:TOP_GAPS]


def _observed(state: dict[str, Any]) -> dict[str, Any] | None:
    live = _slot(state, "live_wire")
    if not live:
        return None
    overrides = live.get("overrides") or {}
    cg = (overrides.get("citation_grid") or {}).get("portfolio") or {}
    sc = (overrides.get("click_ceiling") or {}).get("portfolio") or {}
    return {
        "surfaces": list((overrides.get("citation_grid") or {}).get("surfaces") or []),
        "observed_citation_share": _round(cg.get("observed_citation_share")),
        "competitor_split": [
            {"domain": str(d.get("domain", "")), "share": _round(d.get("share"))}
            for d in (cg.get("competitor_split") or [])
        ],
        "observed_current_clicks": sc.get("observed_current_clicks"),
    }


def _provenance(
    state: dict[str, Any],
    readiness: dict[str, Any] | None,
    winnable: dict[str, Any] | None,
) -> list[str]:
    notes: list[str] = []
    if readiness is not None:
        notes.append(
            "Citation readiness and share are expected, offline estimates from "
            "structural signals, normalised within the client's own clusters. They "
            "are not a competitor or an observed share."
        )
    if winnable is not None:
        notes.append(
            "Winnable clicks are reported as a low-to-high band, never a single "
            "number. The band widens where a CTR cell is filled by formula rather "
            "than confirmed by a source."
        )
    if _slot(state, "live_wire") is not None:
        notes.append(
            "Observed figures come from a Live Wire capture and sit beside the "
            "expected ones; AI answer surfaces vary by session, so treat an observed "
            "citation share as a sample, not a guarantee."
        )
    return notes


def build_view(state: dict[str, Any]) -> dict[str, Any]:
    """Build the normalised report view from a run-state.

    Returns a plain, deterministic mapping the renderers consume directly. Sections
    backed by a module that did not run are omitted (``None`` or an empty list).
    """
    clusters = _clusters(state)
    readiness = _readiness(state)
    winnable = _winnable(state)
    return {
        "header": _header(state),
        "corpus": _corpus(state),
        "clusters": clusters,
        "top_clusters": clusters[:TOP_CLUSTERS],
        "winnable": winnable,
        "readiness": readiness,
        "gaps": _gaps(state),
        "observed": _observed(state),
        "provenance_notes": _provenance(state, readiness, winnable),
    }
