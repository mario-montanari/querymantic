#!/usr/bin/env python3
"""Sprint 8 tests: the determinism guarantee and the expected_outputs/ sample.

Determinism is proven by generating the artifacts twice and comparing: two runs on
the same input produce byte-identical output. This holds on any platform because it
compares two fresh runs in the same environment, not against a committed file (a
different OS or Python build can reproduce the same numbers with last-bit float
differences, which a byte gate would flag as drift).

The files under expected_outputs/ are a readable sample of the output. Structural
checks below assert their shape (the engine block dropped, every module slot filled,
the manifest carrying a digest), not their exact bytes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

EXPECTED_DIR = PLUGIN_ROOT / "expected_outputs"


def _load_regen():
    path = PLUGIN_ROOT / "scripts" / "regenerate_expected_outputs.py"
    spec = importlib.util.spec_from_file_location("regenerate_expected_outputs", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_files_exist() -> None:
    assert (EXPECTED_DIR / "sample_run.trimmed.json").is_file()
    assert (EXPECTED_DIR / "sample_dashboard.html").is_file()


def test_trimmed_has_modules_and_no_engine() -> None:
    import json

    data = json.loads(
        (EXPECTED_DIR / "sample_run.trimmed.json").read_text(encoding="utf-8")
    )
    assert set(data) == {"querymantic", "modules"}, (
        "the engine block must be dropped from the proof"
    )
    assert data["querymantic"]["generated_at"] == "2026-06-08T00:00:00+00:00"
    # Every offline module ran and filled its slot.
    for name in (
        "entity_web",
        "fan_out_radar",
        "citation_grid",
        "click_ceiling",
        "output_forge",
    ):
        assert data["modules"][name] is not None, (
            f"{name} slot should be populated in the proof"
        )
    # The HTML artifact is recorded in the manifest with a digest.
    arts = data["modules"]["output_forge"]["artifacts"]
    assert any(a["format"] == "html" and len(a["sha256"]) == 64 for a in arts)


def test_fresh_run_is_reproducible() -> None:
    # Two fresh runs on the same input must be byte-identical. This is the
    # determinism guarantee, and it holds on any platform.
    import tempfile

    regen = _load_regen()
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        trimmed_a, html_a = regen._build(Path(a))
        trimmed_b, html_b = regen._build(Path(b))
    assert trimmed_a == trimmed_b, "trimmed run-state must be reproducible across runs"
    assert html_a == html_b, "dashboard HTML must be reproducible across runs"
