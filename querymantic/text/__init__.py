"""Text utilities for Querymantic modules: tokenizing, stopwords, and candidate terms.

Stdlib-only building blocks shared by the analysis modules. BM25 scoring is added
in the sprint that first needs it (Fan-Out Radar).
"""

from __future__ import annotations

from .stopwords import stopwords_for
from .tokenize import candidates, tokenize

__all__ = ["stopwords_for", "tokenize", "candidates"]
