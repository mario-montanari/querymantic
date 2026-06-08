#!/usr/bin/env python3
"""Interchangeable entity extractor.

An extractor turns a corpus of short documents (here, keyword phrases) into scored
candidate entities. The interface is a callable:

    extract(documents, min_df, max_ngram) -> dict[str, EntityStat]

where ``documents`` is a list of dicts each carrying ``text`` and ``language``.
Swapping extractors is a registry lookup, so a clean-room YAKE reimplementation or
an opt-in KeyBERT path can replace the default without touching the modules.

The default, ``tfidf_position``, is an own scorer built from first principles:
deterministic, stdlib-only, and vendor-neutral. For each candidate term it computes
term frequency, document frequency, inverse document frequency, and a head-position
factor. The salience used for ranking is term frequency times the head-position
factor, because on a keyword corpus the central entities are common by design and
should not be penalised by IDF; IDF is still reported so a consumer can measure how
distinctive a term is to a subset (used for per-cluster topical authority).
"""

from __future__ import annotations

import math
from typing import Any, Callable

from .text import candidates, stopwords_for

# Minimum number of documents a term must appear in to count as a corpus entity.
# Singletons on a keyword corpus are mostly noise.
DEFAULT_MIN_DF = 2

ExtractorFn = Callable[..., dict[str, dict[str, Any]]]


def tfidf_position_extract(
    documents: list[dict[str, Any]],
    min_df: int = DEFAULT_MIN_DF,
    max_ngram: int = 2,
) -> dict[str, dict[str, Any]]:
    """Extract candidate entities with tf, df, idf, position, and a salience score.

    Each document is a dict with ``text`` (the phrase) and ``language`` (ISO 639-1).
    Returns a mapping ``term -> stats`` for terms with ``df >= min_df``.
    """
    total_docs = len(documents)
    if total_docs == 0:
        return {}

    # Per term: occurrence count, set of supporting doc indices, and the best (lowest)
    # first-token index seen in each supporting doc.
    tf: dict[str, int] = {}
    support: dict[str, set[int]] = {}
    best_index: dict[str, dict[int, int]] = {}

    for doc_index, doc in enumerate(documents):
        stop = stopwords_for(doc.get("language", ""))
        for term, first_index in candidates(doc.get("text", ""), stop, max_ngram):
            tf[term] = tf.get(term, 0) + 1
            support.setdefault(term, set()).add(doc_index)
            per_doc = best_index.setdefault(term, {})
            if doc_index not in per_doc or first_index < per_doc[doc_index]:
                per_doc[doc_index] = first_index

    results: dict[str, dict[str, Any]] = {}
    for term, support_docs in support.items():
        df = len(support_docs)
        if df < min_df:
            continue
        idf = math.log(total_docs / df)
        position_factor = sum(
            1.0 / (1 + idx) for idx in best_index[term].values()
        ) / df
        score = df * position_factor
        results[term] = {
            "tf": tf[term],
            "df": df,
            "idf": round(idf, 6),
            "position_factor": round(position_factor, 6),
            "score": round(score, 6),
            "support": sorted(support_docs),
        }
    return results


def yake_clean_room_extract(*_args: Any, **_kwargs: Any) -> dict[str, dict[str, Any]]:
    """Placeholder for the clean-room YAKE reimplementation.

    Deferred on purpose: a faithful clean-room build requires the Campos 2020 paper,
    which is not available in the workspace. Reconstructing it from a secondary
    summary would violate the project's "never from memory, never invent" rule.
    """
    raise NotImplementedError(
        "clean-room YAKE extractor is not implemented yet; it requires the "
        "Campos 2020 paper. Use the 'tfidf_position' extractor in the meantime."
    )


# Name -> extractor. Add 'yake' and an opt-in 'keybert' here as they land.
EXTRACTORS: dict[str, ExtractorFn] = {
    "tfidf_position": tfidf_position_extract,
}

DEFAULT_EXTRACTOR = "tfidf_position"


def get_extractor(name: str) -> ExtractorFn:
    """Return the extractor registered under ``name``."""
    try:
        return EXTRACTORS[name]
    except KeyError as exc:
        known = ", ".join(sorted(EXTRACTORS)) or "(none)"
        raise KeyError(
            f"unknown extractor {name!r}; available: {known}"
        ) from exc
