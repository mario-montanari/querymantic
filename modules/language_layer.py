#!/usr/bin/env python3
"""Language Layer module.

The vendored engine supports four languages (English, French, German, Spanish).
On Italian input it misreads two axes: it votes the language to ``en`` or ``fr``
(Italian function words are not in its tables), and it flattens intent to
``informational`` because its intent markers are keyed by those four languages
with an English fallback, so Italian cues such as ``prezzo`` or ``migliori`` are
unseen. The one exception is a provided intent column, which the engine honours.

Language Layer corrects this offline, as a Querymantic module, without touching the
vendored engine. It runs FIRST, before the other modules, so they read corrected
language and intent rather than retrofitting each one. Per keyword it:

- Re-detects Italian by mirroring the engine's vote structure with an Italian
  lexical resource (the ``data/gazetteer/it.json`` cues plus the question
  pronouns) and a conservative, strictly-greater rule: Italian replaces the
  engine's language only when its vote beats the engine's, never on a tie. A
  declared language (engine confidence 1.0) is left untouched.
- For a keyword detected as Italian, recomputes the intent vector from Italian
  markers, mirroring the engine's own weights. The override is conservative: it
  fires only on positive Italian lexical evidence (a marker or question pronoun).
  When no Italian marker fires the engine's intent is kept, because it may carry
  a signal from a provided intent column.

It then recomputes the corpus language and intent counts and each cluster's
dominant intent in the produced state, and records every change in its own audit
slot so nothing is silent. The vendored engine package is never edited; only the
produced run-state is, exactly as any module writes the state.

Scope. Language Layer corrects the ``language`` and intent ``query_type`` fields
and the aggregates of them. It does not recompute the engine's per-keyword scopes
(quick wins, AIO eligibility, and so on), which the engine computed under its own
classification; that would mean reimplementing the engine. The ``modality`` and
``temporal`` axes of the intent vector are also left engine-derived: they key off
language-agnostic shape and English seasonal markers, outside this module's remit.

This is a pure step: ``language_layer(run_state) -> run_state'``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

# The Italian lexical resource. Kept as data so a sixth language is a file drop.
_GAZETTEER_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "gazetteer" / "it.json"
)

# A char vote, mirroring the engine's diacritic weight (a present cue counts 2).
_DIACRITIC_VOTE = 2

# Map a winning intent axis to the engine's funnel stage, identical to the engine.
_FUNNEL_MAP = {
    "informational": "awareness",
    "navigational": "consideration",
    "commercial_investigation": "consideration",
    "transactional": "decision",
}

# Internal axis keys to the engine's query_type names.
_INFO = "informational"
_NAV = "navigational"
_TRANS = "transactional"
_COMM = "commercial_investigation"


class ModuleError(Exception):
    """Raised when the module cannot run against the current run-state."""


class LanguageLayerError(Exception):
    """Raised when the Italian lexical resource cannot be loaded."""


_GAZETTEER_CACHE: dict[str, Any] | None = None


def load_gazetteer(path: Path | None = None) -> dict[str, Any]:
    """Load and lightly validate the Italian gazetteer, with a small cache.

    The cache holds the canonical data and every call returns an independent deep
    copy, so a caller that mutates the result cannot corrupt the cached resource for
    later runs in the same process.
    """
    global _GAZETTEER_CACHE
    if path is None and _GAZETTEER_CACHE is not None:
        return json.loads(json.dumps(_GAZETTEER_CACHE))
    target = path or _GAZETTEER_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LanguageLayerError(f"gazetteer not found: {target}") from exc
    except json.JSONDecodeError as exc:
        raise LanguageLayerError(f"gazetteer is not valid JSON: {target}") from exc
    for field in ("language_cues", "question_pronouns", "intent_markers"):
        if field not in data:
            raise LanguageLayerError(f"gazetteer is missing '{field}': {target}")
    markers = data["intent_markers"]
    for axis in ("transactional", "commercial", "informational", "navigational"):
        if axis not in markers:
            raise LanguageLayerError(
                f"gazetteer intent_markers missing '{axis}': {target}"
            )
    if path is None:
        _GAZETTEER_CACHE = data
        return json.loads(json.dumps(data))
    return data


def _engine_vote_score(confidence: float) -> int:
    """Invert the engine's confidence formula to its winning vote score.

    The engine sets ``confidence = min(1.0, 0.5 + best_score * 0.15)`` and returns
    ``0.4`` when no signal at all is found. So a confidence below 0.5 means a zero
    vote, and otherwise the score is ``round((confidence - 0.5) / 0.15)``.
    """
    if confidence < 0.5:
        return 0
    return round((confidence - 0.5) / 0.15)


def _italian_language_score(
    keyword: str, vocab: frozenset[str], diacritics: str
) -> int:
    """Italian vote: one per cue token, plus a diacritic char vote."""
    tokens = keyword.split()
    score = sum(1 for tok in tokens if tok in vocab)
    if any(ch in diacritics for ch in keyword):
        score += _DIACRITIC_VOTE
    return score


def _italian_confidence(score: int) -> float:
    """Italian detection confidence, on the engine's own scale."""
    return round(min(1.0, 0.5 + score * 0.15), 4)


def _italian_intent(
    keyword: str,
    markers: dict[str, list[str]],
    pronouns: frozenset[str],
    serp_features: list[str],
) -> tuple[str, float, str | None]:
    """Italian intent vector, mirroring the engine's weighting.

    Returns ``(query_type, confidence, fired_cue)``. ``fired_cue`` is ``None`` when
    no Italian lexical marker fired, which is the signal to keep the engine intent.
    """
    weights = {_INFO: 0.0, _NAV: 0.0, _TRANS: 0.0, _COMM: 0.0}
    tokens = keyword.split()
    first = tokens[0] if tokens else ""
    fired_cue: str | None = None

    if first in pronouns:
        weights[_INFO] += 0.7
        fired_cue = f"pronoun:{first}"

    for marker in markers["transactional"]:
        if marker in keyword:
            weights[_TRANS] += 0.8
            fired_cue = fired_cue or f"transactional:{marker}"
            break

    for marker in markers["commercial"]:
        if f" {marker} " in f" {keyword} " or keyword.startswith(f"{marker} "):
            weights[_COMM] += 0.7
            fired_cue = fired_cue or f"commercial:{marker}"
            break

    for marker in markers["navigational"]:
        if marker in keyword:
            weights[_NAV] += 0.9
            fired_cue = fired_cue or f"navigational:{marker}"
            break

    for marker in markers["informational"]:
        if marker in tokens:
            weights[_INFO] += 0.4
            fired_cue = fired_cue or f"informational:{marker}"
            break

    # SERP-feature nudges, identical to the engine. These are not Italian lexical
    # evidence, so they never trigger an override on their own.
    if any(f in serp_features for f in ("featured_snippet", "paa", "ai_overview")):
        weights[_INFO] += 0.1
    if any(f in serp_features for f in ("shopping", "local_pack")):
        weights[_TRANS] += 0.1

    query_type = max(weights, key=lambda k: weights[k])
    confidence = round(min(1.0, weights[query_type]), 4)
    return query_type, confidence, fired_cue


def language_layer(
    state: dict[str, Any], *, gazetteer: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Correct Italian language and intent in the run-state and write the audit slot."""
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("language_layer needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        raise ModuleError("engine analysis has no keywords")

    gaz = gazetteer if gazetteer is not None else load_gazetteer()
    vocab = frozenset(
        w.lower() for w in (gaz["language_cues"] + gaz["question_pronouns"])
    )
    pronouns = frozenset(w.lower() for w in gaz["question_pronouns"])
    markers = gaz["intent_markers"]
    diacritics = gaz.get("diacritics", "")

    language_changes: list[dict[str, Any]] = []
    intent_changes: list[dict[str, Any]] = []
    detected_italian = 0

    for index, record in enumerate(keywords):
        if not isinstance(record, dict):
            continue
        keyword = (record.get("keyword") or "").lower()
        if not keyword:
            continue

        engine_lang = record.get("language") or "unknown"
        engine_conf = record.get("language_confidence")
        engine_conf = (
            float(engine_conf) if isinstance(engine_conf, (int, float)) else 0.4
        )

        # A declared language (engine confidence 1.0) is authoritative; leave it.
        if engine_conf >= 1.0:
            continue

        it_score = _italian_language_score(keyword, vocab, diacritics)
        engine_score = _engine_vote_score(engine_conf)

        # Conservative, strictly-greater: Italian must beat the engine's vote.
        if it_score <= 0 or it_score <= engine_score:
            continue

        # Re-detect as Italian.
        detected_italian += 1
        new_conf = _italian_confidence(it_score)
        record["language"] = "it"
        record["language_confidence"] = new_conf
        enrichment = record.get("enrichment")
        if isinstance(enrichment, dict):
            enrichment["language_confidence"] = new_conf
        language_changes.append(
            {
                "index": index,
                "keyword": record.get("keyword", ""),
                "from": engine_lang,
                "to": "it",
                "italian_score": it_score,
                "engine_score": engine_score,
                "confidence": new_conf,
            }
        )

        # Recompute intent only on positive Italian lexical evidence.
        serp_features = (record.get("metrics") or {}).get("serp_features") or []
        if not isinstance(serp_features, list):
            serp_features = []
        new_intent, new_intent_conf, fired_cue = _italian_intent(
            keyword, markers, pronouns, serp_features
        )
        if fired_cue is None:
            continue  # no Italian marker fired; keep the engine intent

        vec = (
            (enrichment or {}).get("intent_vector")
            if isinstance(enrichment, dict)
            else None
        )
        if not isinstance(vec, dict):
            continue
        old_intent = vec.get("query_type")
        old_conf = (
            enrichment.get("intent_confidence")
            if isinstance(enrichment, dict)
            else None
        )
        vec["query_type"] = new_intent
        vec["funnel_stage"] = _FUNNEL_MAP[new_intent]
        if isinstance(enrichment, dict):
            enrichment["intent_confidence"] = new_intent_conf
        intent_changes.append(
            {
                "index": index,
                "keyword": record.get("keyword", ""),
                "from": old_intent,
                "to": new_intent,
                "confidence_from": round(float(old_conf), 4)
                if isinstance(old_conf, (int, float))
                else None,
                "confidence_to": new_intent_conf,
                "cue": fired_cue,
            }
        )

    _recompute_aggregates(engine)

    state["modules"]["language_layer"] = {
        "language": "it",
        "summary": {
            "keywords_total": len(keywords),
            "detected_italian": detected_italian,
            "language_reclassified": len(language_changes),
            "intent_reclassified": len(intent_changes),
            "by_language": dict(sorted(_counter_by_language(keywords).items())),
            "by_intent": dict(sorted(_counter_by_intent(keywords).items())),
        },
        "language_changes": language_changes,
        "intent_changes": intent_changes,
        "rules": {
            "detection": "strictly-greater Italian vote over the engine vote; declared language (confidence 1.0) untouched",
            "intent_override": "only on positive Italian lexical evidence (marker or question pronoun); otherwise the engine intent is kept",
            "diacritic_vote": _DIACRITIC_VOTE,
            "gazetteer": _GAZETTEER_PATH.name,
        },
    }
    return state


def _counter_by_language(keywords: list[dict[str, Any]]) -> Counter:
    return Counter(
        (kw.get("language") or "unknown") for kw in keywords if isinstance(kw, dict)
    )


def _counter_by_intent(keywords: list[dict[str, Any]]) -> Counter:
    return Counter(
        ((kw.get("enrichment") or {}).get("intent_vector") or {}).get(
            "query_type", "unknown"
        )
        for kw in keywords
        if isinstance(kw, dict)
    )


def _recompute_aggregates(engine: dict[str, Any]) -> None:
    """Recompute corpus language and intent counts and cluster dominant intents."""
    keywords = engine.get("keywords") or []
    corpus = engine.get("corpus_summary")
    if isinstance(corpus, dict):
        corpus["by_language"] = dict(_counter_by_language(keywords))
        corpus["by_intent"] = dict(_counter_by_intent(keywords))

    clusters = engine.get("clusters")
    if isinstance(clusters, list):
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            members = cluster.get("members") or []
            intents = [
                ((keywords[i].get("enrichment") or {}).get("intent_vector") or {}).get(
                    "query_type"
                )
                for i in members
                if isinstance(i, int)
                and 0 <= i < len(keywords)
                and isinstance(keywords[i], dict)
            ]
            intents = [x for x in intents if x]
            cluster["dominant_intent"] = (
                Counter(intents).most_common(1)[0][0] if intents else "unknown"
            )
