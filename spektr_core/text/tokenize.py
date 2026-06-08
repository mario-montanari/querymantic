"""Tokenizing and candidate-term generation for entity extraction.

Stdlib only. The tokenizer splits on non-word characters and lowercases. Candidate
generation produces unigrams and bigrams from runs of non-stopword tokens, keeping
the position of each candidate's first token so an extractor can reward head
position.
"""

from __future__ import annotations

import re
import unicodedata

# A token is a run of word characters (Unicode letters and digits). The re.UNICODE
# flag keeps accented letters in French, German, and Spanish keywords.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Drop single-character tokens: they are rarely entities and add noise.
_MIN_TOKEN_LEN = 2

# Highest n-gram length generated. Two captures phrases like "running shoes" while
# keeping the candidate set small on a keyword corpus.
DEFAULT_MAX_NGRAM = 2


def tokenize(text: str) -> list[str]:
    """Return lowercased word tokens of length >= 2 from ``text``."""
    normalized = unicodedata.normalize("NFC", text).lower()
    return [t for t in _TOKEN_RE.findall(normalized) if len(t) >= _MIN_TOKEN_LEN]


def candidates(
    text: str,
    stopwords: frozenset[str],
    max_ngram: int = DEFAULT_MAX_NGRAM,
) -> list[tuple[str, int]]:
    """Return candidate terms with the index of each candidate's first token.

    Unigrams come from every non-stopword token. Bigrams (and higher, up to
    ``max_ngram``) come only from runs of adjacent non-stopword tokens, so a phrase
    never bridges across a removed function word. The index is the position of the
    first token in the full token sequence, used for head-position weighting.

    The same candidate may appear more than once for one text (for example a token
    repeated); callers that want per-text uniqueness deduplicate on the term.
    """
    tokens = tokenize(text)
    # Mark which positions survive stopword removal.
    kept: list[tuple[int, str]] = [
        (i, tok) for i, tok in enumerate(tokens) if tok not in stopwords
    ]
    out: list[tuple[str, int]] = []

    # Unigrams.
    for index, tok in kept:
        out.append((tok, index))

    # Higher n-grams from adjacent kept tokens (contiguous in the original order).
    for n in range(2, max_ngram + 1):
        for start in range(len(kept) - n + 1):
            window = kept[start : start + n]
            indices = [idx for idx, _ in window]
            if indices[-1] - indices[0] != n - 1:
                continue  # not contiguous in the original token sequence
            term = " ".join(tok for _, tok in window)
            out.append((term, indices[0]))

    return out
