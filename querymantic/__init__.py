"""Querymantic shared core: run-state contract, engine adapter, and pipeline runner.

This package is stdlib-only. Optional third-party libraries, when a module needs
one, are reached through ``querymantic.ports`` so they can degrade when absent.
"""

from __future__ import annotations

__all__ = ["run_state", "engine_adapter", "pipeline"]
