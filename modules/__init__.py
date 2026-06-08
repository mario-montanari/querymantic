"""Module registry for Spektr.

Each module is a pure function ``run_state -> run_state'`` that fills its own slot
in ``run_state['modules']``. Modules register here by name so the pipeline can
look them up without importing each one directly. The Sprint 0 scaffold ships an
empty registry; sprints 1 to 7 add one entry each, in the approved order.
"""

from __future__ import annotations

from typing import Any, Callable

from .entity_web import entity_web

ModuleFn = Callable[[dict[str, Any]], dict[str, Any]]

# Name -> module function. Each entry is a pure step run_state -> run_state'.
REGISTRY: dict[str, ModuleFn] = {
    "entity_web": entity_web,
}


def has(name: str) -> bool:
    """Return True if a module is registered under ``name``."""
    return name in REGISTRY


def get(name: str) -> ModuleFn:
    """Return the registered module function for ``name``."""
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"no module registered under {name!r}") from exc


def names() -> list[str]:
    """Return the registered module names in insertion order."""
    return list(REGISTRY)
