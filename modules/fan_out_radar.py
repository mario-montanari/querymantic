#!/usr/bin/env python3
"""Fan-Out Radar module.

Models how a head query fans out into sub-queries and measures how well each
cluster's keywords already cover that fan-out. It runs fully offline: with no
content corpus, the cluster's own keywords are the documents, so the coverage is an
*expected* coverage, not an observed one.

For each cluster it generates sub-queries across seven archetypes (related,
implicit, comparative, recent, personalized, reformulation, entity-expanded; after
Mike King / iPullRank's account of AI Mode fan-out), scores each sub-query against
the cluster's keywords with BM25, and reports:

- per sub-query: the best BM25 score, whether it is covered, how central it is, its
  originating search volume, and whether it is a gatekeeper query;
- per cluster: Cover@tau, the missing archetypes, and the gatekeeper queries;
- a run summary.

Gatekeeper query (an internal term): a sub-query that is central to the fan-out,
because many of the cluster's keywords answer it, yet has no originating search
volume. Nobody types it, but a content set must answer it to compete.

The number of sub-queries a real fan-out produces is a secondary industry estimate
(often quoted as eight to twelve), not a figure from any search-engine source. Here
it is a configurable cap, not presented as a fact.

This is a pure step: ``fan_out_radar(run_state) -> run_state'``. It fills the
``fan_out_radar`` slot. It reads the Entity Web graph when present to enrich the
related and entity-expanded archetypes, and degrades gracefully without it.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from spektr_core.text import stopwords_for, tokenize
from spektr_core.text.bm25 import BM25, median_value

ARCHETYPES = (
    "related",
    "implicit",
    "comparative",
    "recent",
    "personalized",
    "reformulation",
    "entity_expanded",
)

# Cap on generated sub-queries per cluster. Derived from the secondary "8 to 12"
# industry estimate; a parameter, not a search-engine fact.
MAX_SUBQUERIES_PER_CLUSTER = 12

# Question words for the implicit archetype.
IMPLICIT_PREFIXES = ("what", "why", "how", "when")

# How many neighbours or siblings to use per generative archetype.
TOP_NEIGHBOURS = 3
TOP_SIBLINGS = 3

# A sub-query is a gatekeeper when at least this many cluster keywords answer it and
# it has no originating volume.
GATEKEEPER_MIN_CENTRALITY = 2

_SYNONYMS_PATH = Path(__file__).resolve().parent.parent / "data" / "synonyms.json"


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


def _load_synonyms() -> dict[str, list[str]]:
    try:
        data = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {
        k: v
        for k, v in data.items()
        if not k.startswith("_") and isinstance(v, list)
    }


def _reference_year(state: dict[str, Any]) -> int:
    stamp = (state.get("spektr") or {}).get("generated_at", "")
    try:
        return int(str(stamp)[:4])
    except (ValueError, TypeError):
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).year


def _norm(text: str) -> str:
    """Normalise a phrase for exact-match lookups: collapsed lowercase tokens."""
    return " ".join(tokenize(text))


def fan_out_radar(state: dict[str, Any]) -> dict[str, Any]:
    """Compute the fan-out coverage layer and write it to the run-state."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("fan_out_radar needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    clusters = engine.get("clusters")
    if not isinstance(keywords, list) or not isinstance(clusters, list) or not clusters:
        raise ModuleError("engine analysis has no clusters to work on")

    synonyms = _load_synonyms()
    reference_year = _reference_year(state)

    # Volume by normalised keyword, for originating-volume lookups.
    volume_by_keyword: dict[str, int] = {}
    for kw in keywords:
        vol = (kw.get("metrics") or {}).get("volume")
        if isinstance(vol, (int, float)):
            key = _norm(kw.get("keyword", ""))
            volume_by_keyword[key] = max(volume_by_keyword.get(key, 0), int(vol))

    entity_neighbours = _entity_neighbours(state)
    cluster_heads = [c.get("head", "") for c in clusters]

    cluster_reports: list[dict[str, Any]] = []
    coverage_values: list[float] = []
    total_gatekeepers = 0

    for index, cluster in enumerate(clusters):
        report = _analyse_cluster(
            index,
            cluster,
            clusters,
            cluster_heads,
            keywords,
            synonyms,
            reference_year,
            entity_neighbours,
            volume_by_keyword,
        )
        cluster_reports.append(report)
        coverage_values.append(report["coverage"]["cover_at_tau"])
        total_gatekeepers += len(report["gatekeepers"])

    mean_coverage = round(sum(coverage_values) / len(coverage_values), 4) if coverage_values else 0.0

    state["modules"]["fan_out_radar"] = {
        "params": {
            "k1": 1.2,
            "b": 0.75,
            "max_subqueries_per_cluster": MAX_SUBQUERIES_PER_CLUSTER,
            "reference_year": reference_year,
            "tau": "median_max_bm25",
            "gatekeeper_min_centrality": GATEKEEPER_MIN_CENTRALITY,
        },
        "archetypes": list(ARCHETYPES),
        "subquery_count_note": (
            "The eight-to-twelve sub-query figure is a secondary industry estimate, "
            "not a search-engine fact. The per-cluster cap is a parameter."
        ),
        "mode": "expected",
        "summary": {
            "clusters": len(cluster_reports),
            "mean_cover_at_tau": mean_coverage,
            "total_gatekeepers": total_gatekeepers,
        },
        "clusters": cluster_reports,
    }
    return state


def _entity_neighbours(state: dict[str, Any]) -> dict[str, list[str]]:
    """Return entity -> neighbour entities from the Entity Web graph, if present."""
    ew = (state.get("modules") or {}).get("entity_web")
    if not isinstance(ew, dict):
        return {}
    graph = ew.get("graph") or {}
    nodes = graph.get("nodes") or []
    neighbours: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in graph.get("edges") or []:
        try:
            i, j, _weight = edge
            neighbours[nodes[i]].append(nodes[j])
            neighbours[nodes[j]].append(nodes[i])
        except (ValueError, IndexError, KeyError):
            continue
    return neighbours


def _analyse_cluster(
    index: int,
    cluster: dict[str, Any],
    clusters: list[dict[str, Any]],
    cluster_heads: list[str],
    keywords: list[dict[str, Any]],
    synonyms: dict[str, list[str]],
    reference_year: int,
    entity_neighbours: dict[str, list[str]],
    volume_by_keyword: dict[str, int],
) -> dict[str, Any]:
    head = cluster.get("head", "")
    members = [m for m in (cluster.get("members") or []) if 0 <= m < len(keywords)]
    member_keywords = [keywords[m].get("keyword", "") for m in members]
    language = _dominant_language(members, keywords)
    stop = stopwords_for(language)

    docs = [[t for t in tokenize(kw) if t not in stop] for kw in member_keywords]
    bm25 = BM25(docs)

    sub_queries = _generate_subqueries(
        head,
        index,
        member_keywords,
        cluster_heads,
        synonyms,
        reference_year,
        entity_neighbours,
        stop,
    )

    # Score every sub-query, then derive the coverage threshold from the scores.
    scored: list[dict[str, Any]] = []
    for archetype, query in sub_queries:
        q_tokens = [t for t in tokenize(query) if t not in stop]
        max_bm25 = round(bm25.max_score(q_tokens), 6)
        scored.append(
            {
                "query": query,
                "archetype": archetype,
                "q_tokens": q_tokens,
                "max_bm25": max_bm25,
            }
        )

    tau = round(median_value([s["max_bm25"] for s in scored]), 6)

    covered_count = 0
    gatekeepers: list[str] = []
    covered_archetypes: set[str] = set()
    out_subqueries: list[dict[str, Any]] = []
    for item in scored:
        centrality = bm25.coverage_count(item["q_tokens"], tau) if tau > 0 else 0
        covered = item["max_bm25"] >= tau and item["max_bm25"] > 0
        originating_volume = volume_by_keyword.get(_norm(item["query"]), 0)
        is_gatekeeper = (
            centrality >= GATEKEEPER_MIN_CENTRALITY and originating_volume == 0
        )
        if covered:
            covered_count += 1
            covered_archetypes.add(item["archetype"])
        if is_gatekeeper:
            gatekeepers.append(item["query"])
        out_subqueries.append(
            {
                "query": item["query"],
                "archetype": item["archetype"],
                "max_bm25": item["max_bm25"],
                "covered": covered,
                "centrality": centrality,
                "originating_volume": originating_volume,
                "gatekeeper": is_gatekeeper,
            }
        )

    produced_archetypes = {s["archetype"] for s in scored}
    missing = sorted(produced_archetypes - covered_archetypes)
    total = len(out_subqueries)
    cover_at_tau = round(covered_count / total, 4) if total else 0.0

    return {
        "cluster_index": index,
        "head": head,
        "language": language,
        "sub_queries": out_subqueries,
        "coverage": {
            "cover_at_tau": cover_at_tau,
            "tau": tau,
            "covered": covered_count,
            "total": total,
        },
        "missing_archetypes": missing,
        "gatekeepers": gatekeepers,
    }


def _dominant_language(members: list[int], keywords: list[dict[str, Any]]) -> str:
    langs = [keywords[m].get("language", "") for m in members if keywords[m].get("language")]
    if not langs:
        return "en"
    return Counter(langs).most_common(1)[0][0]


def _generate_subqueries(
    head: str,
    cluster_index: int,
    member_keywords: list[str],
    cluster_heads: list[str],
    synonyms: dict[str, list[str]],
    reference_year: int,
    entity_neighbours: dict[str, list[str]],
    stop: frozenset[str],
) -> list[tuple[str, str]]:
    """Generate (archetype, query) pairs for one cluster.

    Each archetype is generated into its own bucket, then the buckets are merged
    round-robin up to the cap, so the sub-query set keeps archetype diversity rather
    than letting the earliest archetypes use up the budget.
    """
    head_norm = _norm(head)
    head_tokens = tokenize(head)
    head_set = set(head_tokens)
    seen: set[str] = set()
    buckets: dict[str, list[str]] = {a: [] for a in ARCHETYPES}

    def add(archetype: str, query: str) -> None:
        norm = _norm(query)
        if not norm or norm == head_norm or norm in seen:
            return
        seen.add(norm)
        buckets[archetype].append(query)

    def usable_neighbour(term: str) -> bool:
        # A neighbour must add a token beyond the head, or the query is degenerate
        # ("running shoes" + "shoes" -> "running shoes shoes").
        tokens = set(tokenize(term))
        return bool(tokens) and not tokens <= head_set

    graph_neighbours = [
        n for n in entity_neighbours.get(head, []) if usable_neighbour(n)
    ][:TOP_NEIGHBOURS]

    # Related: head plus co-occurrence neighbours, falling back to frequent member
    # tokens not already in the head.
    related_terms = graph_neighbours or _frequent_member_terms(
        member_keywords, head_tokens, stop
    )
    for term in related_terms[:TOP_NEIGHBOURS]:
        add("related", f"{head} {term}")

    # Implicit: question words plus the head.
    for prefix in IMPLICIT_PREFIXES:
        add("implicit", f"{prefix} {head}")

    # Comparative: head vs the most similar sibling cluster heads.
    for sibling in _similar_siblings(cluster_index, head_tokens, cluster_heads):
        add("comparative", f"{head} vs {sibling}")

    # Recent: head plus year tokens around the reference year.
    for year in (reference_year, reference_year - 1, reference_year + 1):
        add("recent", f"{head} {year}")

    # Personalized: only from explicit audience signals, which the offline corpus
    # does not carry, so this archetype is skipped here by design.

    # Reformulation: swap a head token for a gazetteer synonym.
    for i, token in enumerate(head_tokens):
        for synonym in synonyms.get(token, []):
            swapped = head_tokens[:i] + [synonym] + head_tokens[i + 1 :]
            add("reformulation", " ".join(swapped))

    # Entity-expanded: pair a neighbour entity's distinctive token with the head
    # noun, so "running shoes" expands to siblings like "trail shoes" or "best
    # shoes" rather than to a bare neighbour token.
    head_noun = head_tokens[-1] if head_tokens else ""
    for neighbour in graph_neighbours:
        nb_tokens = tokenize(neighbour)
        extra = next(
            (t for t in nb_tokens if t not in head_set),
            nb_tokens[0] if nb_tokens else "",
        )
        if extra and head_noun and extra != head_noun:
            add("entity_expanded", f"{extra} {head_noun}")

    # Round-robin merge to preserve archetype diversity under the cap.
    out: list[tuple[str, str]] = []
    while len(out) < MAX_SUBQUERIES_PER_CLUSTER and any(buckets.values()):
        for archetype in ARCHETYPES:
            if buckets[archetype]:
                out.append((archetype, buckets[archetype].pop(0)))
                if len(out) >= MAX_SUBQUERIES_PER_CLUSTER:
                    break
    return out


def _frequent_member_terms(
    member_keywords: list[str], head_tokens: list[str], stop: frozenset[str]
) -> list[str]:
    head_set = set(head_tokens)
    counts: Counter[str] = Counter()
    for kw in member_keywords:
        for token in tokenize(kw):
            if token in stop or token in head_set:
                continue
            counts[token] += 1
    return [term for term, _ in counts.most_common(TOP_NEIGHBOURS)]


def _similar_siblings(
    cluster_index: int, head_tokens: list[str], cluster_heads: list[str]
) -> list[str]:
    head_set = set(head_tokens)
    if not head_set:
        return []
    scored: list[tuple[float, str]] = []
    for other_index, other_head in enumerate(cluster_heads):
        if other_index == cluster_index:
            continue
        other_set = set(tokenize(other_head))
        if not other_set:
            continue
        jaccard = len(head_set & other_set) / len(head_set | other_set)
        if 0 < jaccard < 1:
            scored.append((jaccard, other_head))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [head for _, head in scored[:TOP_SIBLINGS]]
