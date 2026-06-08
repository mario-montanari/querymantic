#!/usr/bin/env python3
"""Sprint 8 tests: the committed determinism proof in expected_outputs/.

A fresh deterministic run must match the committed trimmed run-state and HTML
dashboard byte for byte. This is the determinism guarantee made into a committed,
CI-checked artifact, rather than a property proven only by the per-module tests.

The committed proof is generated on a machine without the optional Office backends
(HTML produced, Office formats skipped). When the backends are installed, Output
Forge also emits the Office artifacts, which changes the trimmed run-state's
output_forge manifest; the proof is then environment-specific, so this test skips the
byte comparison when a backend is present and falls back to structural checks.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from spektr_core.ports import ooxml  # noqa: E402

EXPECTED_DIR = PLUGIN_ROOT / "expected_outputs"


def _load_regen():
    path = PLUGIN_ROOT / "scripts" / "regenerate_expected_outputs.py"
    spec = importlib.util.spec_from_file_location("regenerate_expected_outputs", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _office_backend_present() -> bool:
    return any(ooxml.ooxml_capabilities().values())


def test_committed_files_exist() -> None:
    assert (EXPECTED_DIR / "sample_run.trimmed.json").is_file()
    assert (EXPECTED_DIR / "sample_dashboard.html").is_file()


def test_trimmed_has_modules_and_no_engine() -> None:
    import json

    data = json.loads((EXPECTED_DIR / "sample_run.trimmed.json").read_text(encoding="utf-8"))
    assert set(data) == {"spektr", "modules"}, "the engine block must be dropped from the proof"
    assert data["spektr"]["generated_at"] == "2026-06-08T00:00:00+00:00"
    # Every offline module ran and filled its slot.
    for name in ("entity_web", "fan_out_radar", "citation_grid", "click_ceiling", "output_forge"):
        assert data["modules"][name] is not None, f"{name} slot should be populated in the proof"
    # The HTML artifact is recorded in the manifest with a digest.
    arts = data["modules"]["output_forge"]["artifacts"]
    assert any(a["format"] == "html" and len(a["sha256"]) == 64 for a in arts)


def test_fresh_run_matches_committed_proof() -> None:
    regen = _load_regen()
    if _office_backend_present():
        # Office backends change the manifest; byte comparison is environment-bound.
        # Still prove that a fresh run reproduces itself (internal determinism).
        import tempfile

        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ta, ha = regen._build(Path(a))
            tb, hb = regen._build(Path(b))
        assert ta == tb and ha == hb
        return
    # Stdlib-only machine: the committed bytes must match a fresh run exactly.
    assert regen.check() == 0
