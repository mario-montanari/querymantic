"""Module registry for Spektr.

Each module is a pure function ``run_state -> run_state'`` that fills its own slot
in ``run_state['modules']``. Modules register here by name so the pipeline can
look them up without importing each one directly. The Sprint 0 scaffold ships an
empty registry; sprints 1 to 7 add one entry each, and Sprint 8 adds
``language_layer``, which leads the run order because it corrects the engine's
language and intent before the analysis modules read them.
"""

from __future__ import annotations

from typing import Any, Callable

from .citation_grid import citation_grid
from .click_ceiling import click_ceiling
from .demand_pulse import demand_pulse
from .entity_web import entity_web
from .fan_out_radar import fan_out_radar
from .language_layer import language_layer
from .live_wire import live_wire
from .output_forge import output_forge

# A module takes the run-state and returns it. Some modules accept extra keyword
# options (for example demand_pulse takes an optional ``series``); the pipeline
# passes those through ``module_kwargs``, so the callable signature is left open.
ModuleFn = Callable[..., dict[str, Any]]

# Name -> module function. Each entry is a pure step run_state -> run_state'.
REGISTRY: dict[str, ModuleFn] = {
    "language_layer": language_layer,
    "entity_web": entity_web,
    "fan_out_radar": fan_out_radar,
    "demand_pulse": demand_pulse,
    "citation_grid": citation_grid,
    "click_ceiling": click_ceiling,
    "live_wire": live_wire,
    "output_forge": output_forge,
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
