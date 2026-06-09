#!/usr/bin/env python3
"""Pipeline runner for Querymantic.

The pipeline turns input keyword exports into a validated ``run.json``:

1. Expand the input paths into a concrete list of files and hash them.
2. Run the vendored engine to produce the canonical analysis.
3. Build the run-state with the engine output and empty module slots.
4. Apply each requested module in order (none in the Sprint 0 scaffold).
5. Save and return the validated run-state.

Each module is a pure function ``run_state -> run_state'`` registered in
``modules``. The pipeline looks modules up by name so new modules plug in without
changing this file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import engine_adapter, run_state

# Input file extensions the suite accepts. The engine handles separator sniffing
# inside these; other extensions are ignored when expanding a directory.
INPUT_SUFFIXES = (".csv", ".tsv")


class PipelineError(Exception):
    """Raised when the pipeline cannot complete a run."""


def expand_inputs(inputs: list[Path]) -> list[Path]:
    """Expand files and directories into a sorted list of input files.

    A file with an accepted suffix is kept as is. A directory is searched, non
    recursively, for files with accepted suffixes. The result is sorted for
    deterministic ordering.
    """
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            for child in item.iterdir():
                if child.is_file() and child.suffix.lower() in INPUT_SUFFIXES:
                    files.append(child)
        elif item.is_file():
            files.append(item)
        else:
            raise PipelineError(f"input path not found: {item}")
    if not files:
        raise PipelineError("no input files found among the given paths")
    # De-duplicate while keeping a stable, sorted order.
    unique = sorted({f.resolve() for f in files}, key=lambda p: p.as_posix())
    return unique


def run_pipeline(
    plugin_root: Path,
    inputs: list[Path],
    output: Path,
    label: str = "",
    client_domain: str = "",
    brand_list: str = "",
    modules_to_run: tuple[str, ...] = (),
    generated_at: str | None = None,
    module_kwargs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and write ``run.json`` to ``output``.

    ``modules_to_run`` names the modules to apply, in order. Unknown names raise
    before any work begins. ``generated_at`` can be pinned for reproducible
    output. ``module_kwargs`` maps a module name to extra keyword arguments for it
    (for example ``{"demand_pulse": {"series": parsed}}``); modules that take no
    extra options simply receive none.
    """
    # Deferred and anchored to the plugin root on purpose. The modules package imports
    # back into querymantic, so importing it at module top would be circular; and a
    # bare ``import modules`` would resolve off the current working directory. Putting
    # plugin_root on sys.path first makes it resolve to this plugin's registry no
    # matter where the process started.
    import importlib
    import sys

    root = str(plugin_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    module_registry = importlib.import_module("modules")

    for name in modules_to_run:
        if not module_registry.has(name):
            raise PipelineError(f"unknown module requested: {name}")

    files = expand_inputs(inputs)
    input_hash = run_state.compute_input_hash(files)
    version = run_state.plugin_version(plugin_root)

    try:
        analysis = engine_adapter.run_engine(
            plugin_root,
            files,
            label=label,
            client_domain=client_domain,
            brand_list=brand_list,
        )
    except engine_adapter.EngineError as exc:
        raise PipelineError(f"engine stage failed: {exc}") from exc

    state = run_state.new_run_state(
        inputs=[f.as_posix() for f in files],
        input_hash=input_hash,
        version=version,
        engine=analysis,
        generated_at=generated_at,
    )

    for name in modules_to_run:
        module_fn = module_registry.get(name)
        extra = (module_kwargs or {}).get(name, {})
        state = module_fn(state, **extra)
        # Round the slot before the next module (or the renderers) reads it, so the
        # whole pipeline produces the same numbers on any platform.
        run_state.round_module_slot(state, name)
        run_state.mark_module_run(state, name)

    run_state.save_run_state(state, output)
    return state
