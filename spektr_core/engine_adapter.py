#!/usr/bin/env python3
"""Adapter for the vendored keyword-intelligence engine.

Spektr does not reimplement the engine. It runs the vendored copy under
``engine/keyword-intelligence/`` as a separate process and reads its canonical
``analysis.json``. The engine is stdlib-only, so it runs under the same Python
interpreter as the suite (``sys.executable``).

The subprocess is always called with a list of arguments and ``shell=False`` so
no input is ever passed through a shell.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Engine location relative to the plugin root.
ENGINE_SUBDIR = Path("engine") / "keyword-intelligence"
ANALYZE_SCRIPT = Path("scripts") / "analyze.py"

# The sample corpus analyses in well under a minute; a real export is larger but
# still local and offline. This ceiling stops a hung subprocess without cutting
# off a legitimate large run.
ENGINE_TIMEOUT_SECONDS = 600


class EngineError(Exception):
    """Raised when the vendored engine fails to produce a usable analysis."""


def engine_root(plugin_root: Path) -> Path:
    """Return the absolute path to the vendored engine directory."""
    return (plugin_root / ENGINE_SUBDIR).resolve()


def run_engine(
    plugin_root: Path,
    inputs: list[Path],
    label: str = "",
    client_domain: str = "",
    brand_list: str = "",
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the engine on ``inputs`` and return the parsed ``analysis.json``.

    A temporary output directory is used unless ``work_dir`` is given. Only
    ``analysis.json`` is read back; the engine is invoked with ``--json-only`` so
    it does not write the human-facing artifacts.
    """
    if not inputs:
        raise EngineError("no input files provided to the engine")

    root = engine_root(plugin_root)
    analyze_py = root / ANALYZE_SCRIPT
    if not analyze_py.is_file():
        raise EngineError(f"vendored engine script not found: {analyze_py}")

    missing = [p for p in inputs if not p.is_file()]
    if missing:
        listed = ", ".join(str(p) for p in missing)
        raise EngineError(f"input files not found: {listed}")

    if work_dir is None:
        with tempfile.TemporaryDirectory(prefix="spektr-engine-") as tmp:
            return _invoke(
                root, analyze_py, inputs, Path(tmp), label, client_domain, brand_list
            )
    work_dir.mkdir(parents=True, exist_ok=True)
    return _invoke(root, analyze_py, inputs, work_dir, label, client_domain, brand_list)


def _invoke(
    root: Path,
    analyze_py: Path,
    inputs: list[Path],
    out_dir: Path,
    label: str,
    client_domain: str,
    brand_list: str,
) -> dict[str, Any]:
    """Run analyze.py once and parse the resulting analysis.json."""
    cmd: list[str] = [
        sys.executable,
        str(analyze_py),
        "--inputs",
        *[str(p.resolve()) for p in inputs],
        "--output",
        str(out_dir.resolve()),
        "--json-only",
        "--quiet",
    ]
    if label:
        cmd += ["--label", label]
    if client_domain:
        cmd += ["--client-domain", client_domain]
    if brand_list:
        cmd += ["--brand-list", brand_list]

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EngineError(
            f"engine timed out after {ENGINE_TIMEOUT_SECONDS} seconds"
        ) from exc
    except OSError as exc:
        raise EngineError(f"could not start the engine process: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        raise EngineError(f"engine exited with code {completed.returncode}: {detail}")

    analysis_path = out_dir / "analysis.json"
    if not analysis_path.is_file():
        raise EngineError(f"engine did not produce analysis.json in {out_dir}")
    try:
        return json.loads(analysis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineError("engine produced invalid analysis.json") from exc
