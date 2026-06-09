#!/usr/bin/env python3
"""Run-state contract for Querymantic.

The run-state is the single canonical object for one analysis run, stored as
``run.json``. It carries three parts:

- ``querymantic``: suite metadata (schema and plugin versions, a deterministic hash
  of the input files, the input paths, and the list of modules that have run).
- ``engine``: the vendored keyword-intelligence engine output (the contents of
  the engine's ``analysis.json``), or ``null`` before the engine runs.
- ``modules``: one slot per Querymantic module, each ``null`` until that module fills
  it. Every module is a pure function ``run_state -> run_state'`` that writes its
  own slot and appends its name to ``querymantic.modules_run``.

Validation here is structural and uses the standard library only, so the suite
carries no ``jsonschema`` dependency. The JSON Schema at ``schemas/run.schema.json``
is the documentary contract; this module is the executable check that the
pipeline relies on.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The run-state schema version. Bump on any change to the run.json shape.
# 0.2.0 added the language_layer slot (the Italian fifth-language correction).
SCHEMA_VERSION = "0.2.0"

# Module slots, in the approved run order. Every run.json carries all of them;
# a slot stays None until its module runs. language_layer leads because it corrects
# the engine's language and intent before the analysis modules read them.
MODULE_KEYS: tuple[str, ...] = (
    "language_layer",
    "entity_web",
    "fan_out_radar",
    "demand_pulse",
    "citation_grid",
    "click_ceiling",
    "live_wire",
    "output_forge",
)

# Read in 64 KB blocks so the input hash works on large exports without loading
# a whole file into memory.
_HASH_BLOCK_BYTES = 64 * 1024


class RunStateError(Exception):
    """Base error for run-state operations."""


class RunStateValidationError(RunStateError):
    """Raised when a run-state fails structural validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "invalid run-state")


def plugin_version(plugin_root: Path) -> str:
    """Return the plugin version from ``.claude-plugin/plugin.json``.

    The manifest is the single source of truth for the version, so it is read at
    runtime rather than duplicated as a constant.
    """
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunStateError(f"plugin manifest not found: {manifest}") from exc
    except json.JSONDecodeError as exc:
        raise RunStateError(f"plugin manifest is not valid JSON: {manifest}") from exc
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise RunStateError(f"plugin manifest has no usable version: {manifest}")
    return version


def compute_input_hash(paths: list[Path]) -> str:
    """Return a deterministic SHA-256 over the given input files.

    Files are hashed in sorted path order, each preceded by its POSIX path and
    byte length, so the digest depends on both content and identity and does not
    change with the order the caller passes the paths in.
    """
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.as_posix()):
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise RunStateError(f"cannot stat input file: {path}") from exc
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(str(size).encode("utf-8"))
        try:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(_HASH_BLOCK_BYTES), b""):
                    digest.update(block)
        except OSError as exc:
            raise RunStateError(f"cannot read input file: {path}") from exc
    return digest.hexdigest()


def new_run_state(
    inputs: list[str],
    input_hash: str,
    version: str,
    engine: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a fresh run-state with empty module slots.

    ``generated_at`` defaults to the current UTC time in ISO 8601. Pass a fixed
    value to produce a byte-reproducible run.json for tests or expected outputs.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "querymantic": {
            "schema_version": SCHEMA_VERSION,
            "plugin_version": version,
            "generated_at": generated_at,
            "input_hash": input_hash,
            "inputs": list(inputs),
            "modules_run": [],
        },
        "engine": engine,
        "modules": {key: None for key in MODULE_KEYS},
    }


def mark_module_run(state: dict[str, Any], module: str) -> None:
    """Record that ``module`` has populated its slot.

    Appends the module name to ``querymantic.modules_run`` once, preserving order.
    """
    if module not in MODULE_KEYS:
        raise RunStateError(f"unknown module: {module}")
    ran = state["querymantic"]["modules_run"]
    if module not in ran:
        ran.append(module)


STORED_FLOAT_PRECISION = 6


def _round_floats(value: Any, ndigits: int) -> Any:
    """Recursively round every float in a JSON-like structure to ``ndigits``.

    Integers, booleans, strings and ``None`` are left untouched. This makes module
    output reproducible across machines: scores that pass through transcendental
    functions (BM25 and TF-IDF use ``log``) can differ in the last bit between one
    platform's math library and another's, and rounding to a fixed decimal removes
    that noise before it reaches run.json.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, ndigits)
    if isinstance(value, dict):
        return {k: _round_floats(v, ndigits) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats(v, ndigits) for v in value]
    return value


def round_module_slot(state: dict[str, Any], module: str) -> None:
    """Round every float in a module's slot to the stored precision, in place.

    Applied right after a module fills its slot, so downstream modules and the
    renderers read the same rounded numbers a fresh run produces on any platform.
    """
    modules = state.get("modules")
    if isinstance(modules, dict) and isinstance(modules.get(module), (dict, list)):
        modules[module] = _round_floats(modules[module], STORED_FLOAT_PRECISION)


def save_run_state(state: dict[str, Any], path: Path) -> None:
    """Write a run-state to disk as UTF-8 JSON with stable key order.

    Validates before writing so a malformed state never reaches disk. Keys are
    sorted and a trailing newline is added so output is byte-stable across runs.
    """
    errors = collect_validation_errors(state)
    if errors:
        raise RunStateValidationError(errors)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def load_run_state(path: Path) -> dict[str, Any]:
    """Read and validate a run-state from disk."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunStateError(f"run-state not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunStateError(f"run-state is not valid JSON: {path}") from exc
    errors = collect_validation_errors(data)
    if errors:
        raise RunStateValidationError(errors)
    return data


def collect_validation_errors(state: Any) -> list[str]:
    """Return a list of structural problems with ``state`` (empty if valid)."""
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["run-state must be a JSON object"]

    querymantic = state.get("querymantic")
    if not isinstance(querymantic, dict):
        errors.append("'querymantic' must be an object")
    else:
        for field, expected in (
            ("schema_version", str),
            ("plugin_version", str),
            ("generated_at", str),
            ("input_hash", str),
        ):
            value = querymantic.get(field)
            if not isinstance(value, expected) or value == "":
                errors.append(f"'querymantic.{field}' must be a non-empty string")
        if not isinstance(querymantic.get("inputs"), list):
            errors.append("'querymantic.inputs' must be an array")
        modules_run = querymantic.get("modules_run")
        if not isinstance(modules_run, list):
            errors.append("'querymantic.modules_run' must be an array")
        else:
            for name in modules_run:
                if name not in MODULE_KEYS:
                    errors.append(
                        f"'querymantic.modules_run' has unknown module: {name!r}"
                    )

    if "engine" not in state:
        errors.append("'engine' key is required (object or null)")
    elif state["engine"] is not None and not isinstance(state["engine"], dict):
        errors.append("'engine' must be an object or null")

    modules = state.get("modules")
    if not isinstance(modules, dict):
        errors.append("'modules' must be an object")
    else:
        missing = [key for key in MODULE_KEYS if key not in modules]
        if missing:
            errors.append("'modules' is missing slots: " + ", ".join(missing))
        unexpected = [key for key in modules if key not in MODULE_KEYS]
        if unexpected:
            errors.append("'modules' has unexpected slots: " + ", ".join(unexpected))

    return errors


def validate_run_state(state: Any) -> bool:
    """Return True if ``state`` is structurally valid, else raise."""
    errors = collect_validation_errors(state)
    if errors:
        raise RunStateValidationError(errors)
    return True
