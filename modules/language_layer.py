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

A second, corpus-level pass then corrects what no per-keyword vote can see:
realistic Italian corpora are dominated by short content keywords with no
function words and no accents, where the engine falls back to English at
confidence 0.4 and the Italian vote scores zero. The pass works on a corpus
prior: when the Italian share of evidence-bearing keywords (an Italian cue or a
real engine vote) reaches a declared threshold, the corpus is treated as
Italian-majority and two narrow classes inherit the prior. (1) Exact vote ties,
which the strictly-greater rule alone must concede to the engine. (2)
Zero-signal keywords that carry positive Italian form evidence: a declared
Italian morphological suffix, or the Italian orthographic shape (every token
vowel-final, no letter or sequence foreign to Italian orthography). The prior
NEVER overrides a contrary engine vote, however weak: a keyword the engine
scored higher than the Italian vote keeps the engine's language. Zero-signal
keywords with a foreign shape (brand names, bare English queries) are left
untouched, so an Italian site's legitimate foreign keywords survive an
Italian-majority corpus. Thresholds and confidence are declared, surfaced in
the audit slot with provenance, and overridable through ``params``; every
prior decision is recorded in ``language_changes`` with its reason.

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

# The engine emits confidence 0.5 + score * 0.15, so 0.65 is its weakest REAL
# vote (score 1); anything below is the no-signal English fallback (0.4).
_ENGINE_EVIDENCE_CONFIDENCE = 0.65

# Corpus-prior defaults. Project parameters, not search-engine facts; surfaced
# in the audit slot with provenance and overridable through ``params``.
_PRIOR_DEFAULTS: dict[str, Any] = {
    # Master switch for the corpus-level second pass.
    "prior_enabled": True,
    # Italian share of evidence-bearing keywords needed to call the corpus
    # Italian-majority.
    "prior_share_threshold": 0.5,
    # Minimum evidence-bearing keywords before the share means anything; a
    # micro-corpus must not switch the prior on.
    "prior_min_evidence": 10,
    # Confidence assigned to prior-inherited detections. Deliberately below
    # 0.65 (the engine's weakest real vote) so downstream consumers can tell
    # prior-inherited from evidence-detected.
    "prior_confidence": 0.55,
}

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


def _resolve_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Merge caller overrides over the declared prior defaults, type-checked."""
    cfg = dict(_PRIOR_DEFAULTS)
    if not params:
        return cfg
    if isinstance(params.get("prior_enabled"), bool):
        cfg["prior_enabled"] = params["prior_enabled"]
    for key in ("prior_share_threshold", "prior_confidence"):
        value = params.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cfg[key] = float(value)
    value = params.get("prior_min_evidence")
    if isinstance(value, int) and not isinstance(value, bool):
        cfg["prior_min_evidence"] = value
    return cfg


def _italian_shape(
    keyword: str,
    vowels: frozenset[str],
    foreign_letters: str,
    foreign_sequences: tuple[str, ...],
) -> bool:
    """True when every alphabetic token has the Italian orthographic shape.

    Native Italian words end in a vowel and never contain the foreign letters
    or sequences declared in the gazetteer. Digit tokens are neutral. This is
    deliberately a SHAPE test, not a dictionary: it admits unknown content
    words while rejecting brand names and bare foreign queries.
    """
    tokens = [tok for tok in keyword.split() if not tok.isdigit()]
    if not tokens:
        return False
    for tok in tokens:
        if any(ch in foreign_letters for ch in tok):
            return False
        if any(seq in tok for seq in foreign_sequences):
            return False
        if tok[-1] not in vowels:
            return False
    return True


def _morphology_cue(
    keyword: str, suffixes: tuple[str, ...], foreign_letters: str
) -> str | None:
    """First Italian morphological suffix carried by a token, or None.

    A token bearing a foreign letter cannot carry Italian morphology, and the
    token must extend the suffix by at least two characters so short foreign
    words cannot match by accident.
    """
    for tok in keyword.split():
        if any(ch in foreign_letters for ch in tok):
            continue
        for suffix in suffixes:
            if len(tok) >= len(suffix) + 2 and tok.endswith(suffix):
                return suffix
    return None


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


def _flip_to_italian(
    record: dict[str, Any],
    index: int,
    keyword: str,
    engine_lang: str,
    new_conf: float,
    it_score: int,
    engine_score: int,
    reason: str,
    markers: dict[str, list[str]],
    pronouns: frozenset[str],
    language_changes: list[dict[str, Any]],
    intent_changes: list[dict[str, Any]],
) -> None:
    """Set a record to Italian, then apply the evidence-gated intent override."""
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
            "reason": reason,
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
        return  # no Italian marker fired; keep the engine intent

    vec = (
        (enrichment or {}).get("intent_vector")
        if isinstance(enrichment, dict)
        else None
    )
    if not isinstance(vec, dict):
        return
    old_intent = vec.get("query_type")
    old_conf = (
        enrichment.get("intent_confidence") if isinstance(enrichment, dict) else None
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


def language_layer(
    state: dict[str, Any],
    *,
    gazetteer: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
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
    suffixes = tuple(gaz.get("morphological_suffixes") or ())
    foreign_letters = str(gaz.get("foreign_letters") or "")
    foreign_sequences = tuple(gaz.get("foreign_sequences") or ())
    vowels = frozenset("aeiou") | frozenset(diacritics)
    cfg = _resolve_params(params)

    language_changes: list[dict[str, Any]] = []
    intent_changes: list[dict[str, Any]] = []
    detected_italian = 0
    rows: list[dict[str, Any]] = []

    # Pass 1: the per-keyword strictly-greater vote, exactly as before.
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
            rows.append(
                {
                    "index": index,
                    "record": record,
                    "keyword": keyword,
                    "engine_lang": engine_lang,
                    "declared": True,
                    "it_score": 0,
                    "engine_score": _engine_vote_score(engine_conf),
                    "engine_conf": engine_conf,
                }
            )
            continue

        it_score = _italian_language_score(keyword, vocab, diacritics)
        engine_score = _engine_vote_score(engine_conf)
        rows.append(
            {
                "index": index,
                "record": record,
                "keyword": keyword,
                "engine_lang": engine_lang,
                "declared": False,
                "it_score": it_score,
                "engine_score": engine_score,
                "engine_conf": engine_conf,
            }
        )

        # Conservative, strictly-greater: Italian must beat the engine's vote.
        if it_score <= 0 or it_score <= engine_score:
            continue

        detected_italian += 1
        _flip_to_italian(
            record,
            index,
            keyword,
            engine_lang,
            _italian_confidence(it_score),
            it_score,
            engine_score,
            "lexical_vote",
            markers,
            pronouns,
            language_changes,
            intent_changes,
        )

    # The corpus prior. Evidence: an Italian cue (it_score >= 1) or a real
    # engine vote (confidence >= 0.65; a declared language counts as engine
    # evidence, never as Italian evidence). The no-signal English fallback
    # (0.4) bears no evidence at all.
    italian_evidence = sum(1 for r in rows if not r["declared"] and r["it_score"] >= 1)
    engine_evidence = sum(
        1
        for r in rows
        if r["declared"] or r["engine_conf"] >= _ENGINE_EVIDENCE_CONFIDENCE
    )
    bearing = sum(
        1
        for r in rows
        if (not r["declared"] and r["it_score"] >= 1)
        or r["declared"]
        or r["engine_conf"] >= _ENGINE_EVIDENCE_CONFIDENCE
    )
    share = round(italian_evidence / bearing, 4) if bearing else 0.0
    prior_active = (
        cfg["prior_enabled"]
        and bearing >= cfg["prior_min_evidence"]
        and share >= cfg["prior_share_threshold"]
    )

    # Pass 2: the prior bites ONLY on exact vote ties and on zero-signal
    # keywords with positive Italian form evidence (morphology or shape).
    # Never against a contrary engine vote, however weak; never on a
    # declared language.
    tie_breaks = morphology_hits = shape_hits = 0
    if prior_active:
        for row in rows:
            record = row["record"]
            if row["declared"] or record.get("language") == "it":
                continue
            it_score, engine_score = row["it_score"], row["engine_score"]
            if it_score >= 1 and it_score == engine_score:
                reason = "corpus_prior:tie_break"
                tie_breaks += 1
            elif it_score == 0 and engine_score == 0:
                suffix = _morphology_cue(row["keyword"], suffixes, foreign_letters)
                if suffix is not None:
                    reason = f"corpus_prior:morphology:{suffix}"
                    morphology_hits += 1
                elif _italian_shape(
                    row["keyword"], vowels, foreign_letters, foreign_sequences
                ):
                    reason = "corpus_prior:italian_shape"
                    shape_hits += 1
                else:
                    continue
            else:
                continue  # a contrary engine vote, however weak, always holds

            detected_italian += 1
            _flip_to_italian(
                record,
                row["index"],
                row["keyword"],
                row["engine_lang"],
                cfg["prior_confidence"],
                it_score,
                engine_score,
                reason,
                markers,
                pronouns,
                language_changes,
                intent_changes,
            )

    _recompute_aggregates(engine)

    reclassified_by_prior = tie_breaks + morphology_hits + shape_hits
    state["modules"]["language_layer"] = {
        "language": "it",
        "summary": {
            "keywords_total": len(keywords),
            "detected_italian": detected_italian,
            "language_reclassified": len(language_changes),
            "intent_reclassified": len(intent_changes),
            "reclassified_by_prior": reclassified_by_prior,
            "by_language": dict(sorted(_counter_by_language(keywords).items())),
            "by_intent": dict(sorted(_counter_by_intent(keywords).items())),
        },
        "language_changes": language_changes,
        "intent_changes": intent_changes,
        "prior": {
            "enabled": prior_active,
            "share": share,
            "evidence": {
                "italian": italian_evidence,
                "engine": engine_evidence,
                "bearing": bearing,
            },
            "tie_breaks": tie_breaks,
            "morphology": morphology_hits,
            "italian_shape": shape_hits,
        },
        "params": {
            "prior_enabled": cfg["prior_enabled"],
            "prior_share_threshold": cfg["prior_share_threshold"],
            "prior_min_evidence": cfg["prior_min_evidence"],
            "prior_confidence": cfg["prior_confidence"],
            "engine_evidence_confidence": _ENGINE_EVIDENCE_CONFIDENCE,
            "provenance": (
                "The corpus prior and its thresholds are project parameters, "
                "not search-engine facts. The prior fires only when the "
                "Italian share of evidence-bearing keywords reaches the "
                "threshold, and only on exact vote ties or zero-signal "
                "keywords with positive Italian form evidence (morphology or "
                "orthographic shape from the gazetteer). It never overrides "
                "a contrary engine vote. Override any value through 'params'."
            ),
        },
        "rules": {
            "detection": "strictly-greater Italian vote over the engine vote; declared language (confidence 1.0) untouched",
            "intent_override": "only on positive Italian lexical evidence (marker or question pronoun); otherwise the engine intent is kept",
            "corpus_prior": "zero-signal keywords need Italian morphology or shape; exact ties break to Italian; a contrary engine vote always holds",
            "diacritic_vote": _DIACRITIC_VOTE,
            "gazetteer": _GAZETTEER_PATH.name,
            "gazetteer_version": str(gaz.get("version", "")),
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
