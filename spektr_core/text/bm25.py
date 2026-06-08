#!/usr/bin/env python3
"""BM25 ranking over a small in-memory corpus.

Stdlib-only implementation of Okapi BM25 with the Lucene defaults k1 = 1.2 and
b = 0.75 (Trotman et al., 2014). The IDF uses the Lucene form, which is always
non-negative, so scores never go negative on common terms.

The corpus here is a set of short documents (keyword phrases within a cluster), so
the implementation favours clarity over micro-optimisation.
"""

from __future__ import annotations

import math
from collections import Counter
from statistics import median

# Lucene/Elasticsearch defaults. k1 controls term-frequency saturation; b controls
# length normalisation. These are the standard values, not tuned constants.
K1 = 1.2
B = 0.75


class BM25:
    """A BM25 index over a list of tokenised documents."""

    def __init__(self, corpus: list[list[str]], k1: float = K1, b: float = B) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_count = len(corpus)
        self.doc_freqs: list[Counter[str]] = [Counter(doc) for doc in corpus]
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avgdl = (sum(self.doc_lengths) / self.doc_count) if self.doc_count else 0.0
        self._idf = self._compute_idf()

    def _compute_idf(self) -> dict[str, float]:
        df: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            df.update(freqs.keys())
        idf: dict[str, float] = {}
        for term, n in df.items():
            # Lucene IDF: always positive.
            idf[term] = math.log(1 + (self.doc_count - n + 0.5) / (n + 0.5))
        return idf

    def score(self, query_tokens: list[str], doc_index: int) -> float:
        """Return the BM25 score of a query against one indexed document."""
        if not 0 <= doc_index < self.doc_count or self.avgdl == 0:
            return 0.0
        freqs = self.doc_freqs[doc_index]
        length = self.doc_lengths[doc_index]
        score = 0.0
        for term in query_tokens:
            tf = freqs.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf.get(term, 0.0)
            denom = tf + self.k1 * (1 - self.b + self.b * length / self.avgdl)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def max_score(self, query_tokens: list[str]) -> float:
        """Return the best BM25 score of a query across all documents."""
        if self.doc_count == 0:
            return 0.0
        return max(self.score(query_tokens, i) for i in range(self.doc_count))

    def coverage_count(self, query_tokens: list[str], tau: float) -> int:
        """Return how many documents score at or above ``tau`` for the query."""
        return sum(
            1 for i in range(self.doc_count) if self.score(query_tokens, i) >= tau
        )


def median_value(values: list[float]) -> float:
    """Return the median of ``values``, or 0.0 when empty."""
    return float(median(values)) if values else 0.0
