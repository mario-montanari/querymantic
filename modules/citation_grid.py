#!/usr/bin/env python3
"""Citation Grid module.

Estimates how ready each cluster is to be cited by AI answer surfaces (Google AI
Overviews, ChatGPT search, Perplexity, Gemini, Claude with web search) and turns
that estimate into concrete editorial actions.

It runs fully offline and with no content corpus. There is no passage text to
read, so the module does two things instead:

1. A structural-signal checklist per cluster. Six citability components drive the
   checklist: Extractability, EntityCoverage, StructuredSignals, InformationGain,
   FreshnessProxy, SourceCues. Each component becomes a concrete action keyed off
   the run-state (the cluster's owned-gap entities, its question-shaped keywords,
   its SERP features, and the Fan-Out gatekeeper sub-queries). Two of the six,
   InformationGain and SourceCues, can only be measured on real passage text, so
   offline they are checklist-only and carry no number.

2. An expected citation-readiness per cluster (0 to 100) and an expected share of
   the client portfolio. Both are computed only from signals that have a genuine
   offline value in the run-state: the engine's AIO and GEO eligibility scopes, the
   Fan-Out coverage of the sub-query family, the Entity Web topical authority, the
   density of answer-shaped queries, the SERP structure features, and, when Demand
   Pulse has run, the demand trend as a freshness signal.

The reported figures are labelled ``expected``, never ``observed``. They are not a
"secret AI channel": they measure structure that ordinary indexing can already
read. An observed citation share, and the competitor split, are unmeasurable
offline (the run-state carries no competitor domains) and belong to the optional
Live Wire path, which overrides ``expected`` with ``observed``.

This is a pure step: ``citation_grid(run_state) -> run_state'``. It fills the
``citation_grid`` slot and leaves everything else untouched. It reads the Fan-Out
Radar and Entity Web slots when present and degrades gracefully without them; the
engine scopes alone are enough to produce a readiness estimate.
"""

from __future__ import annotations

from typing import Any

from querymantic.text import tokenize

# Default weights for the offline readiness blend. Each input is a signal that has
# a real value offline; a component with no value is dropped and the remaining
# weights are renormalised, so the score degrades gracefully when an upstream
# module is absent. These are project parameters, not search-engine facts; their
# spirit follows the published citability components, adapted to demand-side signals
# because there is no passage text offline. All are overridable through ``params``.
DEFAULT_WEIGHTS: dict[str, float] = {
    "eligibility": 0.28,
    "query_family": 0.24,
    "entity_coverage": 0.20,
    "extractability": 0.14,
    "structured_demand": 0.09,
    "freshness": 0.05,
}

# The six citability components, in methodology order. They drive the checklist.
# ``scored`` components feed the readiness number when their signal is present;
# ``checklist_only`` components need real passage text and so carry no offline value.
COMPONENTS: tuple[tuple[str, str], ...] = (
    ("extractability", "scored"),
    ("entity_coverage", "scored"),
    ("structured_signals", "scored"),
    ("information_gain", "checklist_only"),
    ("freshness_proxy", "scored"),
    ("source_cues", "checklist_only"),
)

# SERP features that reward an extractable, answer-shaped passage.
ANSWER_FEATURES = ("featured_snippet", "paa", "ai_overview")
# SERP features that reward a structured format (table, list, product grid).
STRUCTURE_FEATURES = ("featured_snippet", "paa", "shopping")

# question_paa labels that mark an answer-shaped query.
ANSWER_PAA_LABELS = ("question", "question_and_paa", "paa_only")

# How many example items to list per checklist action, to keep run.json compact.
MAX_CHECKLIST_EXAMPLES = 8

# Demand Pulse states that raise the freshness signal (recency matters more).
FRESH_STATES = {"rising": 1.0, "seasonal": 0.8, "declining": 0.4, "flat": 0.3}


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


def _norm(text: str) -> str:
    return " ".join(tokenize(text))


def _config(params: dict[str, Any] | None) -> dict[str, Any]:
    weights = dict(DEFAULT_WEIGHTS)
    cfg: dict[str, Any] = {
        "weights": weights,
        "max_checklist_examples": MAX_CHECKLIST_EXAMPLES,
    }
    if params:
        if isinstance(params.get("weights"), dict):
            for key, value in params["weights"].items():
                if key in weights and isinstance(value, (int, float)):
                    weights[key] = float(value)
        if isinstance(params.get("max_checklist_examples"), int):
            cfg["max_checklist_examples"] = params["max_checklist_examples"]
    return cfg


def _cluster_members(
    cluster: dict[str, Any], keywords: list[dict[str, Any]]
) -> list[int]:
    return [m for m in (cluster.get("members") or []) if 0 <= m < len(keywords)]


def _cluster_demand(
    cluster: dict[str, Any], members: list[int], keywords: list[dict[str, Any]]
) -> int:
    total = cluster.get("volume_total")
    if isinstance(total, (int, float)) and total >= 0:
        return int(total)
    summed = 0
    for m in members:
        vol = (keywords[m].get("metrics") or {}).get("volume")
        if isinstance(vol, (int, float)):
            summed += int(vol)
    return summed


def _is_answer_shaped(keyword: dict[str, Any]) -> bool:
    scopes = keyword.get("scopes") or {}
    label = (scopes.get("question_paa") or {}).get("label", "")
    if label in ANSWER_PAA_LABELS:
        return True
    if (keyword.get("enrichment") or {}).get("question_shape") is True:
        return True
    features = (keyword.get("metrics") or {}).get("serp_features") or []
    return any(f in features for f in ANSWER_FEATURES)


def _has_structure_feature(keyword: dict[str, Any]) -> bool:
    features = (keyword.get("metrics") or {}).get("serp_features") or []
    return any(f in features for f in STRUCTURE_FEATURES)


def _eligibility_value(
    members: list[int], keywords: list[dict[str, Any]]
) -> float | None:
    """Mean AIO eligibility score (0 to 1) across the cluster's keywords.

    The engine's ``aio_eligibility`` scope already scores 0 to 100 whether a query
    is the kind that triggers an AI answer surface. A keyword routed to a GEO
    opportunity (``dual`` or ``geo_only``) is nudged up, since it is cited by
    third-party generative engines even when Google shows no AI Overview.
    """
    scores: list[float] = []
    for m in members:
        scopes = keywords[m].get("scopes") or {}
        aio = scopes.get("aio_eligibility") or {}
        score = aio.get("score")
        if not isinstance(score, (int, float)):
            continue
        value = max(0.0, min(100.0, float(score))) / 100.0
        geo_label = (scopes.get("geo_opportunity") or {}).get("label", "")
        if geo_label in ("dual", "geo_only"):
            value = min(1.0, value + 0.1)
        scores.append(value)
    if not scores:
        return None
    return round(sum(scores) / len(scores), 6)


def _extractability_value(
    members: list[int], keywords: list[dict[str, Any]]
) -> float | None:
    if not members:
        return None
    answer_shaped = sum(1 for m in members if _is_answer_shaped(keywords[m]))
    return round(answer_shaped / len(members), 6)


def _structured_value(
    members: list[int], keywords: list[dict[str, Any]]
) -> float | None:
    if not members:
        return None
    with_feature = sum(1 for m in members if _has_structure_feature(keywords[m]))
    return round(with_feature / len(members), 6)


def _entity_coverage_value(
    index: int, authority_by_cluster: dict[int, float]
) -> float | None:
    return authority_by_cluster.get(index)


def _query_family_value(
    index: int, coverage_by_cluster: dict[int, float]
) -> float | None:
    return coverage_by_cluster.get(index)


def _freshness_value(index: int, state_by_cluster: dict[int, str]) -> float | None:
    state = state_by_cluster.get(index)
    if state is None or state == "unknown":
        return None
    return FRESH_STATES.get(state)


def _blend(
    values: dict[str, float | None], weights: dict[str, float]
) -> tuple[float, dict[str, Any]]:
    """Weighted mean over the inputs that have a value, renormalising the weights.

    Returns the readiness on a 0 to 100 scale and a per-input record of value,
    weight, and effective (renormalised) weight, so the figure is fully auditable.
    """
    present = {
        k: v for k, v in values.items() if v is not None and weights.get(k, 0) > 0
    }
    total_weight = sum(weights[k] for k in present)
    inputs: dict[str, Any] = {}
    readiness = 0.0
    for key in values:
        weight = weights.get(key, 0.0)
        value = values[key]
        available = key in present
        effective = (
            round(weights[key] / total_weight, 6)
            if (available and total_weight)
            else 0.0
        )
        if available:
            readiness += value * effective
        inputs[key] = {
            "value": round(value, 6) if value is not None else None,
            "weight": round(weight, 6),
            "effective_weight": effective,
            "available": available,
        }
    return round(readiness * 100, 4), inputs


def _checklist(
    index: int,
    members: list[int],
    keywords: list[dict[str, Any]],
    entity_for_cluster: dict[int, list[dict[str, Any]]],
    gaps_for_cluster: dict[int, list[str]],
    fan_out_for_cluster: dict[int, dict[str, Any]],
    state_by_cluster: dict[int, str],
    limit: int,
) -> list[dict[str, Any]]:
    """Build the per-cluster structural-signal checklist from the six components."""
    items: list[dict[str, Any]] = []

    # 1. Extractability: open sections with a short direct answer to the questions
    # this cluster's demand already asks.
    questions = sorted(
        {
            keywords[m].get("keyword", "")
            for m in members
            if _is_answer_shaped(keywords[m])
        }
    )
    items.append(
        {
            "component": "extractability",
            "requires": "offline",
            "action": "Open each section with a self-contained answer of 25 words or fewer, before the detail.",
            "basis": "answer-shaped queries in the cluster"
            if questions
            else "no answer-shaped query detected; add question-form subheadings",
            "examples": questions[:limit],
        }
    )

    # 2. EntityCoverage: name and define the cluster's entities, and close the
    # owned-gap entities the client does not cover yet.
    top_entities = sorted({e["entity"] for e in entity_for_cluster.get(index, [])})
    gap_entities = gaps_for_cluster.get(index, [])
    items.append(
        {
            "component": "entity_coverage",
            "requires": "offline",
            "action": "Name and define the cluster's key entities; close the owned-gap entities first.",
            "basis": "Entity Web topical authority and entity gaps",
            "examples": (gap_entities or top_entities)[:limit],
        }
    )

    # 3. StructuredSignals: match the formats the SERP already rewards here.
    feature_counts: dict[str, int] = {}
    for m in members:
        for feature in (keywords[m].get("metrics") or {}).get("serp_features") or []:
            if feature in STRUCTURE_FEATURES:
                feature_counts[feature] = feature_counts.get(feature, 0) + 1
    rewarded = sorted(feature_counts, key=lambda f: (-feature_counts[f], f))
    items.append(
        {
            "component": "structured_signals",
            "requires": "offline",
            "action": "Add a table or ordered list and at least one explicit statistic with its unit.",
            "basis": "SERP features present for this cluster"
            if rewarded
            else "no structured SERP feature detected; structure still aids passage extraction",
            "examples": rewarded[:limit],
        }
    )

    # 4. InformationGain: answer the gatekeeper sub-queries no one targets, and the
    # missing fan-out angles. Measured on text only, so offline this is guidance.
    fan = fan_out_for_cluster.get(index) or {}
    gatekeepers = sorted(fan.get("gatekeepers") or [])
    missing = sorted(fan.get("missing_archetypes") or [])
    items.append(
        {
            "component": "information_gain",
            "requires": "passage_text",
            "action": "Add information beyond the competing pages; answer the gatekeeper sub-queries and the missing fan-out angles.",
            "basis": "Fan-Out Radar gatekeepers and missing archetypes",
            "examples": (gatekeepers or missing)[:limit],
        }
    )

    # 5. FreshnessProxy: show a visible date; recency matters more when demand moves.
    state = state_by_cluster.get(index)
    if state and state != "unknown":
        basis = f"Demand Pulse state: {state}"
    else:
        basis = "demand trend unknown; a visible date still helps"
    items.append(
        {
            "component": "freshness_proxy",
            "requires": "offline",
            "action": "Show a visible publication or update date; refresh on a cadence that matches the demand trend.",
            "basis": basis,
            "examples": [],
        }
    )

    # 6. SourceCues: cite authority, add a credentialed byline and Organization
    # schema. Measured on the page, so offline this is guidance.
    items.append(
        {
            "component": "source_cues",
            "requires": "passage_text",
            "action": "Cite authoritative sources, add an author byline with credentials, and Organization schema with sameAs links.",
            "basis": "citation and authorship cues are read from the page, not from the keyword set",
            "examples": [],
        }
    )
    return items


def _topical_authority_map(state: dict[str, Any]) -> dict[int, float]:
    ew = (state.get("modules") or {}).get("entity_web")
    if not isinstance(ew, dict):
        return {}
    out: dict[int, float] = {}
    for row in ew.get("topical_authority") or []:
        idx = row.get("cluster_index")
        auth = row.get("authority")
        if isinstance(idx, int) and isinstance(auth, (int, float)):
            out[idx] = float(auth)
    return out


def _entities_by_cluster(state: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    ew = (state.get("modules") or {}).get("entity_web")
    if not isinstance(ew, dict):
        return {}
    out: dict[int, list[dict[str, Any]]] = {}
    for entity in ew.get("entities") or []:
        dominant = entity.get("dominant_cluster")
        if isinstance(dominant, int):
            out.setdefault(dominant, []).append(entity)
    return out


def _gaps_by_cluster(state: dict[str, Any]) -> dict[int, list[str]]:
    ew = (state.get("modules") or {}).get("entity_web")
    if not isinstance(ew, dict):
        return {}
    out: dict[int, list[str]] = {}
    for gap in ew.get("entity_gaps") or []:
        idx = gap.get("suggested_cluster")
        name = gap.get("entity")
        if isinstance(idx, int) and isinstance(name, str):
            out.setdefault(idx, []).append(name)
    return out


def _fan_out_by_cluster(state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    fo = (state.get("modules") or {}).get("fan_out_radar")
    if not isinstance(fo, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for row in fo.get("clusters") or []:
        idx = row.get("cluster_index")
        if isinstance(idx, int):
            out[idx] = row
    return out


def _coverage_by_cluster(fan_out: dict[int, dict[str, Any]]) -> dict[int, float]:
    out: dict[int, float] = {}
    for idx, row in fan_out.items():
        cover = (row.get("coverage") or {}).get("cover_at_tau")
        if isinstance(cover, (int, float)):
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


def citation_grid(
    state: dict[str, Any], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute the expected citation layer and write it to the run-state."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("citation_grid needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    clusters = engine.get("clusters")
    if not isinstance(keywords, list) or not isinstance(clusters, list) or not clusters:
        raise ModuleError("engine analysis has no clusters to work on")

    cfg = _config(params)
    weights = cfg["weights"]
    limit = cfg["max_checklist_examples"]

    authority_by_cluster = _topical_authority_map(state)
    entity_for_cluster = _entities_by_cluster(state)
    gaps_for_cluster = _gaps_by_cluster(state)
    fan_out_for_cluster = _fan_out_by_cluster(state)
    coverage_by_cluster = _coverage_by_cluster(fan_out_for_cluster)
    state_by_cluster = _demand_state_by_cluster(state)

    reports: list[dict[str, Any]] = []
    weighted_demand: list[float] = []

    for index, cluster in enumerate(clusters):
        members = _cluster_members(cluster, keywords)
        demand = _cluster_demand(cluster, members, keywords)

        values: dict[str, float | None] = {
            "eligibility": _eligibility_value(members, keywords),
            "query_family": _query_family_value(index, coverage_by_cluster),
            "entity_coverage": _entity_coverage_value(index, authority_by_cluster),
            "extractability": _extractability_value(members, keywords),
            "structured_demand": _structured_value(members, keywords),
            "freshness": _freshness_value(index, state_by_cluster),
        }
        readiness, inputs = _blend(values, weights)

        checklist = _checklist(
            index,
            members,
            keywords,
            entity_for_cluster,
            gaps_for_cluster,
            fan_out_for_cluster,
            state_by_cluster,
            limit,
        )

        reports.append(
            {
                "cluster_index": index,
                "head": cluster.get("head", ""),
                "members": len(members),
                "demand": demand,
                "expected_readiness": readiness,
                "readiness_inputs": inputs,
                "checklist": checklist,
                "expected_share": 0.0,  # filled in the normalisation pass below
            }
        )
        weighted_demand.append(readiness * demand)

    # Expected share: each cluster's readiness weighted by its demand, normalised to
    # sum to 100 across the client's own clusters. This is a within-portfolio
    # priority signal, explicitly NOT a competitor share and NOT observed.
    total = sum(weighted_demand)
    for report, w in zip(reports, weighted_demand):
        report["expected_share"] = round(100 * w / total, 4) if total else 0.0

    readiness_values = [r["expected_readiness"] for r in reports]
    mean_readiness = (
        round(sum(readiness_values) / len(readiness_values), 4)
        if readiness_values
        else 0.0
    )

    state["modules"]["citation_grid"] = {
        "mode": "expected",
        "expected_only": True,
        "params": {
            "weights": {k: round(v, 6) for k, v in weights.items()},
            "max_checklist_examples": limit,
        },
        "components": [{"name": name, "offline": kind} for name, kind in COMPONENTS],
        "reads": {
            "entity_web": bool(authority_by_cluster or entity_for_cluster),
            "fan_out_radar": bool(fan_out_for_cluster),
            "demand_pulse": bool(state_by_cluster),
        },
        "positioning_note": (
            "Citation readiness measures extractable structure (answer-shaped passages, "
            "named entities, statistics, citations, structured data), which ordinary "
            "indexing already reads. It is not a secret AI channel."
        ),
        "method_note": (
            "Readiness is an offline estimate from demand-side signals; the weights are "
            "project parameters, not search-engine facts. InformationGain and SourceCues "
            "need real passage text and are checklist-only offline. An observed citation "
            "share and the competitor split are unmeasurable offline and belong to the "
            "Live Wire path."
        ),
        "summary": {
            "clusters": len(reports),
            "mean_expected_readiness": mean_readiness,
            "scored_components": sum(1 for _, kind in COMPONENTS if kind == "scored"),
            "checklist_only_components": sum(
                1 for _, kind in COMPONENTS if kind == "checklist_only"
            ),
        },
        "clusters": reports,
    }
    return state
