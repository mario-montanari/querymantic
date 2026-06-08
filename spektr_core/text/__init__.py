"""Text utilities for Spektr modules: tokenizing, stopwords, and BM25 scoring.

These are stdlib-only building blocks shared by the analysis modules. The Sprint 0
scaffold leaves the implementations to the sprint that first needs them (Entity Web
introduces tokenizing and co-occurrence; Fan-Out Radar introduces BM25), so this
package starts as a declared seam rather than speculative code.
"""

from __future__ import annotations

__all__: list[str] = []
