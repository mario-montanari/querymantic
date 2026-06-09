#!/usr/bin/env python3
"""Entity Web module.

Reads the engine analysis in the run-state and builds an entity layer on top of it:

- Extract candidate entities from the keyword phrases with the interchangeable
  extractor (default ``tfidf_position``).
- Attach demand (search volume) and ownership to each entity. An entity is owned
  when the analysed domain ranks for at least one keyword that contains it.
- Build a co-occurrence graph over the top entities and report each node's degree.
- List the demand entities the client does not own yet (the entity gaps).
- Score topical authority per cluster as the demand-weighted share of the cluster's
  entities that are owned.

This is a pure step: ``entity_web(run_state) -> run_state'``. It writes
``run_state['modules']['entity_web']`` and leaves everything else untouched.

Ownership note. "Owned" means the analysed domain ranks for the keyword, inferred
from a present ranking position at or above ``OWNED_POSITION_MAX``. Like the engine's
authority signals, this is corpus-bounded: it describes coverage relative to the
provided keyword set, not absolute search authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from spektr_core.entity_extractor import (
    DEFAULT_EXTRACTOR,
    DEFAULT_MIN_DF,
    get_extractor,
)

# A keyword counts as owned when the analysed domain ranks at this position or better.
# Twenty covers the first two result pages, a reasonable "has visibility" threshold.
OWNED_POSITION_MAX = 20

# Caps that keep run.json compact without dropping the signal that matters.
MAX_NGRAM = 2
ENTITIES_MAX = 200
GRAPH_MAX_NODES = 60
GAP_MAX = 50


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


def _is_owned(keyword: dict[str, Any]) -> bool:
    position = (keyword.get("metrics") or {}).get("position")
    return isinstance(position, (int, float)) and 0 < position <= OWNED_POSITION_MAX


def _volume(keyword: dict[str, Any]) -> int:
    volume = (keyword.get("metrics") or {}).get("volume")
    return int(volume) if isinstance(volume, (int, float)) else 0


def _cluster_index(keyword: dict[str, Any]) -> int | None:
    assignment = (keyword.get("scopes") or {}).get("cluster_assignment") or {}
    idx = assignment.get("cluster_index")
    return idx if isinstance(idx, int) else None


def entity_web(state: dict[str, Any]) -> dict[str, Any]:
    """Compute the entity layer and write it to the run-state."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("entity_web needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        raise ModuleError("engine analysis has no keywords")
    clusters = engine.get("clusters") or []

    documents = [
        {"text": kw.get("keyword", ""), "language": kw.get("language", "")}
        for kw in keywords
    ]
    extractor = get_extractor(DEFAULT_EXTRACTOR)
    raw = extractor(documents, min_df=DEFAULT_MIN_DF, max_ngram=MAX_NGRAM)

    cluster_heads = {i: c.get("head", "") for i, c in enumerate(clusters)}

    # Enrich every extracted term with demand, ownership, and cluster spread.
    entities: list[dict[str, Any]] = []
    for term, stat in raw.items():
        support = stat["support"]
        owned_support = sum(1 for i in support if _is_owned(keywords[i]))
        demand_volume = sum(_volume(keywords[i]) for i in support)
        cluster_idxs = [
            _cluster_index(keywords[i])
            for i in support
            if _cluster_index(keywords[i]) is not None
        ]
        dominant_cluster = (
            Counter(cluster_idxs).most_common(1)[0][0] if cluster_idxs else None
        )
        entities.append(
            {
                "entity": term,
                "score": stat["score"],
                "tf": stat["tf"],
                "df": stat["df"],
                "idf": stat["idf"],
                "position_factor": stat["position_factor"],
                "demand_volume": demand_volume,
                "owned": owned_support > 0,
                "owned_support": owned_support,
                "ownership_ratio": round(owned_support / stat["df"], 4),
                "support": support,
                "clusters": sorted(set(cluster_idxs)),
                "dominant_cluster": dominant_cluster,
            }
        )

    # Rank by salience; keep the strongest entities.
    entities.sort(key=lambda e: (-e["score"], e["entity"]))
    entities = entities[:ENTITIES_MAX]

    graph = _build_graph(entities)
    degree = {node: 0 for node in graph["nodes"]}
    for i, j, weight in graph["edges"]:
        degree[graph["nodes"][i]] += weight
        degree[graph["nodes"][j]] += weight
    for entity in entities:
        entity["degree"] = degree.get(entity["entity"], 0)

    gaps = _entity_gaps(entities, cluster_heads)
    authority = _topical_authority(entities, clusters)

    owned_count = sum(1 for e in entities if e["owned"])
    summary = {
        "entities_total": len(entities),
        "owned_entities": owned_count,
        "demand_only_entities": len(entities) - owned_count,
        "gap_count": len(gaps),
    }

    # Drop the per-entity support index lists from the stored output: they are large
    # and reconstructable from the engine keywords. Keep them out of run.json.
    for entity in entities:
        entity.pop("support", None)

    state["modules"]["entity_web"] = {
        "extractor": DEFAULT_EXTRACTOR,
        "params": {
            "min_df": DEFAULT_MIN_DF,
            "max_ngram": MAX_NGRAM,
            "owned_position_max": OWNED_POSITION_MAX,
            "graph_max_nodes": GRAPH_MAX_NODES,
        },
        "summary": summary,
        "entities": entities,
        "graph": graph,
        "entity_gaps": gaps,
        "topical_authority": authority,
    }
    return state


def _build_graph(entities: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a co-occurrence graph over the top entities.

    Two entities are linked when they appear together in at least one keyword; the
    edge weight is the number of shared keywords. Only the top ``GRAPH_MAX_NODES``
    entities by salience are included to keep the graph compact.
    """
    top = entities[:GRAPH_MAX_NODES]
    nodes = [e["entity"] for e in top]
    index_of = {name: i for i, name in enumerate(nodes)}
    supports = [set(e["support"]) for e in top]

    edges: list[list[int]] = []
    for a in range(len(top)):
        for b in range(a + 1, len(top)):
            shared = len(supports[a] & supports[b])
            if shared > 0:
                edges.append([index_of[nodes[a]], index_of[nodes[b]], shared])
    return {"nodes": nodes, "edges": edges}


def _entity_gaps(
    entities: list[dict[str, Any]], cluster_heads: dict[int, str]
) -> list[dict[str, Any]]:
    """List demand entities the client does not own, by descending demand."""
    gaps = [e for e in entities if not e["owned"] and e["demand_volume"] > 0]
    gaps.sort(key=lambda e: (-e["demand_volume"], e["entity"]))
    out: list[dict[str, Any]] = []
    for entity in gaps[:GAP_MAX]:
        suggested = entity.get("dominant_cluster")
        out.append(
            {
                "entity": entity["entity"],
                "demand_volume": entity["demand_volume"],
                "df": entity["df"],
                "suggested_cluster": suggested,
                "suggested_cluster_head": cluster_heads.get(suggested, "")
                if suggested is not None
                else "",
            }
        )
    return out


def _topical_authority(
    entities: list[dict[str, Any]], clusters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Score each cluster's topical authority as demand-weighted owned share."""
    out: list[dict[str, Any]] = []
    for cluster_index, cluster in enumerate(clusters):
        members = set(cluster.get("members") or [])
        if not members:
            continue
        in_cluster = [e for e in entities if members & set(e["support"])]
        # These are sums of per-entity demand, not cluster search volume: a
        # high-volume keyword contributes to every entity it contains. The ratio is
        # the meaningful figure; the absolute sums only weight it.
        entity_demand = sum(e["demand_volume"] for e in in_cluster)
        owned_entity_demand = sum(e["demand_volume"] for e in in_cluster if e["owned"])
        owned_entities = sum(1 for e in in_cluster if e["owned"])
        authority = (
            round(owned_entity_demand / entity_demand, 4) if entity_demand else 0.0
        )
        out.append(
            {
                "cluster_index": cluster_index,
                "head": cluster.get("head", ""),
                "authority": authority,
                "owned_entities": owned_entities,
                "total_entities": len(in_cluster),
                "owned_entity_demand": owned_entity_demand,
                "entity_demand": entity_demand,
            }
        )
    out.sort(key=lambda c: (-c["entity_demand"], c["cluster_index"]))
    return out
