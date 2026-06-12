#!/usr/bin/env python3
"""The provenance tripwire: a committed proof can no longer go stale silently.

Closes the blind spot that let commit 4f06de2 change the xlsx renderer while the
committed proof under expected_outputs/ stayed untouched and CI stayed green:
the determinism check compares two fresh runs with each other by declared design
(cross-platform float rationale), the shape test never compares committed
content to current output, and no CI step regenerates.

The guard: regeneration writes expected_outputs/_provenance.json with the sha256
of every source file that determines the proof bytes (the perimeter is declared
inside the manifest itself, including what is explicitly out and why), plus the
sha256 of the two written artifacts. These tests recompute everything and fail
on the first divergence, in any direction: a changed source, a new or deleted
source inside the perimeter, a retouched manifest, or a committed artifact that
no longer matches the bytes recorded at regeneration time. Source and committed
bytes are platform independent (the repo normalizes line endings to LF), so the
tripwire runs everywhere, including CI.

The perimeter definition lives in the regenerate script and is imported here, so
the writer and the checker cannot drift apart.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

EXPECTED_DIR = PLUGIN_ROOT / "expected_outputs"
MANIFEST_PATH = EXPECTED_DIR / "_provenance.json"


def _load_regen():
    path = PLUGIN_ROOT / "scripts" / "regenerate_expected_outputs.py"
    spec = importlib.util.spec_from_file_location("regenerate_expected_outputs", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_exists_and_declares_its_perimeter() -> None:
    """The manifest carries its own perimeter: what is hashed, what is out, why."""
    assert MANIFEST_PATH.is_file(), "_provenance.json must be committed"
    data = _manifest()
    assert set(data) == {"written_by", "perimeter", "sources", "artifacts"}
    assert "regenerate_expected_outputs.py" in data["written_by"]
    assert data["perimeter"]["included"], "the hashed perimeter must be declared"
    excluded = data["perimeter"]["excluded"]
    # The declared limit: third-party renderers are covered through their pins
    # only, and the residual gap is named, not hidden.
    assert "third_party_runtime" in excluded
    assert "pins" in excluded["third_party_runtime"]
    assert "interpreter_and_os" in excluded
    for digest in data["sources"].values():
        assert len(digest) == 64 and set(digest) <= set("0123456789abcdef")
    assert set(data["artifacts"]) == {
        "sample_run.trimmed.json",
        "sample_dashboard.html",
    }


def test_recorded_sources_match_the_tree() -> None:
    """Any divergence between the tree and the manifest is a red, in BOTH directions.

    A changed generating source without regeneration (the 4f06de2 case), a new
    source file inside the perimeter, a deleted one, or a hand-retouched hash
    all land here as a readable diff.
    """
    regen = _load_regen()
    current = {
        p.relative_to(PLUGIN_ROOT).as_posix(): _sha(p)
        for p in regen._provenance_sources()
    }
    recorded = _manifest()["sources"]

    missing = sorted(set(recorded) - set(current))
    extra = sorted(set(current) - set(recorded))
    changed = sorted(
        path for path in set(recorded) & set(current) if recorded[path] != current[path]
    )
    problems = []
    if changed:
        problems.append(f"changed since regeneration: {changed}")
    if extra:
        problems.append(f"in the perimeter but not recorded: {extra}")
    if missing:
        problems.append(f"recorded but gone from the tree: {missing}")
    assert not problems, (
        "STALE PROOF, regenerate expected_outputs "
        "(python scripts/regenerate_expected_outputs.py): " + "; ".join(problems)
    )


def test_recorded_artifacts_match_the_committed_files() -> None:
    """The committed artifacts are pinned to the regeneration event that wrote them.

    This is the internal-coherence guard: retouching a source hash by hand
    cannot help, because the artifacts written in the same regeneration are
    recorded too and verified against the committed bytes.
    """
    recorded = _manifest()["artifacts"]
    for name, digest in recorded.items():
        path = EXPECTED_DIR / name
        assert path.is_file(), f"{name} is recorded but not committed"
        assert _sha(path) == digest, (
            f"{name} does not match the bytes recorded at regeneration time; "
            "regenerate expected_outputs instead of editing anything by hand"
        )
