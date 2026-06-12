#!/usr/bin/env python3
"""Regenerate (or check) the committed determinism proof in expected_outputs/.

The whole ``run.json`` is byte-deterministic on the same input: the pipeline makes the
run-state portable (it rewrites the absolute paths the engine echoes back, drops the
engine's temp output directory, and pins the engine timestamp). The committed proof is
still a trimmed artifact, because the engine block is large and is the engine's own
output, not the part Querymantic owns:

- ``sample_run.trimmed.json``: the ``querymantic`` metadata (with a pinned timestamp and the
  input hash) plus every ``modules`` slot, with the ``engine`` block dropped for size.
- ``sample_dashboard.html``: the Output Forge HTML dashboard, byte for byte.

Run with no flag to refresh the committed sample files. Run with ``--check`` to
prove determinism: it generates the artifacts twice in temporary directories and
compares the two fresh runs, exiting non-zero if they differ. The committed files
are a readable sample of the output, not a cross-platform byte gate (a different OS
or Python build can reproduce the same numbers with last-bit float differences), so
``--check`` compares two fresh runs rather than the committed bytes.

PROVENANCE TRIPWIRE. Regeneration also writes ``expected_outputs/_provenance.json``:
the sha256 of every SOURCE file that determines the proof bytes, plus the sha256 of
the two written artifacts. Only this script writes that manifest; it is never edited
by hand, and the path for a conscious update is regeneration. An eval test recomputes
the hashes and fails on the first divergence, so a change to generating code that is
not folded into the committed proof turns the suite red instead of leaving a stale
proof under a green CI (the blind spot that let commit 4f06de2 change the xlsx
renderer without the committed manifest noticing). Source-byte hashes are platform
independent, so this guard runs everywhere, including CI.

DECLARED LIMIT of the provenance perimeter: the third-party libraries that render
the OOXML bytes (openpyxl, python-docx, python-pptx) are runtime code, not project
sources; the perimeter covers their DECLARED PINS (``requirements-optional.txt``),
so a pin bump trips the wire, but an environment whose installed versions diverge
from the pins can still produce different bytes without moving any source hash. The
interpreter and OS are likewise outside the perimeter. That residual gap is why
``--check-committed`` exists: an OPT-IN comparison of one fresh build against the
committed bytes, meant for the pinned local regeneration environment (Thonny Python
3.10 with the pinned backends). It is deliberately NEVER wired into CI: the
committed bytes were produced on one OS and Python build, and a different platform
can reproduce the same numbers with last-bit float differences that a byte gate
would misreport as drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.output_forge.brand import load_brand  # noqa: E402
from querymantic import pipeline  # noqa: E402

# The fixed inputs that define the committed proof. Changing any of these changes
# the expected bytes, so they live here as the single source of truth.
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"
MODULES = (
    "language_layer",
    "entity_web",
    "fan_out_radar",
    "citation_grid",
    "click_ceiling",
    "output_forge",
)
CLIENT_DOMAIN = "example-shoes.com"
BRAND_LIST = "hoka,nike,brooks"

EXPECTED_DIR = PLUGIN_ROOT / "expected_outputs"
TRIMMED_NAME = "sample_run.trimmed.json"
HTML_NAME = "sample_dashboard.html"
PROVENANCE_NAME = "_provenance.json"

# The declared provenance perimeter, mirrored verbatim into the manifest so the
# reader of _provenance.json sees what is hashed and what is explicitly out.
PROVENANCE_INCLUDED = [
    "scripts/regenerate_expected_outputs.py (this script: fixed inputs and trim shape)",
    "modules/**/*.py (the module code that fills every slot and renders the artifacts)",
    "querymantic/**/*.py (pipeline, run-state, adapters, ports)",
    "engine/keyword-intelligence/scripts/*.py (the vendored engine the slots derive from)",
    "assets/samples/*.csv|*.tsv (the proof inputs, non-recursive, as the pipeline expands them)",
    "data/gazetteer/it.json (read by language_layer)",
    "forge/templates/brand.json (the brand the proof renders with)",
    ".claude-plugin/plugin.json (the version source recorded in the run-state)",
    "requirements-optional.txt (the declared third-party pins; see excluded)",
]
PROVENANCE_EXCLUDED = {
    "third_party_runtime": (
        "openpyxl, python-docx, python-pptx and statsmodels render bytes but are "
        "runtime code, not project sources. The perimeter hashes their DECLARED "
        "pins (requirements-optional.txt), so a pin bump trips the wire; an "
        "environment whose installed versions diverge from the pins can still "
        "change bytes without moving any source hash. Residual gap covered "
        "opt-in by --check-committed in the pinned local environment."
    ),
    "interpreter_and_os": (
        "A different OS or Python build can reproduce the same numbers with "
        "last-bit float differences; that is why this manifest hashes sources, "
        "not cross-platform output bytes."
    ),
    "vendor_plotly": (
        "vendor/plotly is consumed only by the opt-in interactive dashboard, "
        "which is not one of the proof formats."
    ),
    "schemas": ("schemas/ validate the run-state; they do not shape the proof bytes."),
}


def _provenance_sources() -> list[Path]:
    """Every source file that determines the proof bytes, sorted and de-duplicated.

    This single definition is shared by the writer (regenerate) and the checker
    (the provenance eval test imports it), so the two cannot drift apart.
    """
    sources: list[Path] = [Path(__file__).resolve()]
    for root, pattern in (
        (PLUGIN_ROOT / "modules", "**/*.py"),
        (PLUGIN_ROOT / "querymantic", "**/*.py"),
        (PLUGIN_ROOT / "engine" / "keyword-intelligence" / "scripts", "*.py"),
    ):
        sources.extend(p for p in root.glob(pattern) if "__pycache__" not in p.parts)
    sources.extend(
        p
        for p in (PLUGIN_ROOT / "assets" / "samples").iterdir()
        if p.is_file() and p.suffix.lower() in (".csv", ".tsv")
    )
    sources.append(PLUGIN_ROOT / "data" / "gazetteer" / "it.json")
    sources.append(PLUGIN_ROOT / "forge" / "templates" / "brand.json")
    sources.append(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    sources.append(PLUGIN_ROOT / "requirements-optional.txt")
    return sorted(set(sources), key=lambda p: p.relative_to(PLUGIN_ROOT).as_posix())


def _build(work_dir: Path) -> tuple[bytes, bytes]:
    """Run the deterministic pipeline and return (trimmed_json_bytes, html_bytes)."""
    run_path = work_dir / "run.json"
    forge_dir = work_dir / "forge"
    brand = load_brand(PLUGIN_ROOT / "forge" / "templates" / "brand.json")
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [PLUGIN_ROOT / "assets" / "samples"],
        run_path,
        client_domain=CLIENT_DOMAIN,
        brand_list=BRAND_LIST,
        modules_to_run=MODULES,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs={"output_forge": {"out_dir": forge_dir, "brand": brand}},
    )
    # The pipeline already makes the run-state portable: input paths are stored
    # relative to the plugin root (POSIX), so the proof is byte-identical across
    # machines and directories. The proof keeps the querymantic metadata and the
    # module slots, and drops the engine block, which is the engine's own output.
    trimmed = {"querymantic": dict(state["querymantic"]), "modules": state["modules"]}
    trimmed_bytes = (
        json.dumps(trimmed, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    html_bytes = (forge_dir / "dashboard.html").read_bytes()
    return trimmed_bytes, html_bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _provenance_manifest(trimmed_bytes: bytes, html_bytes: bytes) -> bytes:
    """Build the provenance manifest for the artifacts just written."""
    manifest = {
        "written_by": (
            "scripts/regenerate_expected_outputs.py. Never edit by hand: the "
            "path for a conscious update is regeneration, not retouching a hash."
        ),
        "perimeter": {
            "included": PROVENANCE_INCLUDED,
            "excluded": PROVENANCE_EXCLUDED,
        },
        "sources": {
            p.relative_to(PLUGIN_ROOT).as_posix(): _sha(p.read_bytes())
            for p in _provenance_sources()
        },
        "artifacts": {
            TRIMMED_NAME: _sha(trimmed_bytes),
            HTML_NAME: _sha(html_bytes),
        },
    }
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def regenerate() -> int:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        trimmed_bytes, html_bytes = _build(Path(td))
    provenance_bytes = _provenance_manifest(trimmed_bytes, html_bytes)
    (EXPECTED_DIR / TRIMMED_NAME).write_bytes(trimmed_bytes)
    (EXPECTED_DIR / HTML_NAME).write_bytes(html_bytes)
    (EXPECTED_DIR / PROVENANCE_NAME).write_bytes(provenance_bytes)
    print(f"Wrote {EXPECTED_DIR / TRIMMED_NAME} (sha256 {_sha(trimmed_bytes)})")
    print(f"Wrote {EXPECTED_DIR / HTML_NAME} (sha256 {_sha(html_bytes)})")
    print(f"Wrote {EXPECTED_DIR / PROVENANCE_NAME} (sha256 {_sha(provenance_bytes)})")
    return 0


def check_committed() -> int:
    """OPT-IN: compare one fresh build against the committed bytes.

    Meant for the pinned local regeneration environment only (Thonny Python 3.10
    with the pinned backends). NEVER wired into CI: the committed bytes were
    produced on one OS and Python build, and a different platform can reproduce
    the same numbers with last-bit float differences that this byte comparison
    would misreport as drift.
    """
    with tempfile.TemporaryDirectory() as td:
        trimmed_bytes, html_bytes = _build(Path(td))
    problems: list[str] = []
    for name, fresh in ((TRIMMED_NAME, trimmed_bytes), (HTML_NAME, html_bytes)):
        committed_path = EXPECTED_DIR / name
        if not committed_path.is_file():
            problems.append(f"{name} is not committed")
            continue
        committed = committed_path.read_bytes()
        if committed != fresh:
            problems.append(
                f"{name} is STALE: committed sha256 {_sha(committed)}, "
                f"fresh build {_sha(fresh)}"
            )
    if problems:
        for p in problems:
            print(f"STALE PROOF: {p}", file=sys.stderr)
        print(
            "Regenerate with: python scripts/regenerate_expected_outputs.py",
            file=sys.stderr,
        )
        return 1
    print("Committed proof matches a fresh build in this environment.")
    return 0


def check() -> int:
    """Prove determinism by generating the artifacts twice and comparing.

    Two runs on the same input must produce byte-identical output. This is the
    determinism guarantee, and it holds on any platform because it compares two
    fresh runs in the same environment rather than against a committed file (which
    a different OS or Python build could reproduce with last-bit float differences).
    """
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        trimmed_a, html_a = _build(Path(a))
        trimmed_b, html_b = _build(Path(b))
    problems: list[str] = []
    for name, first, second in (
        (TRIMMED_NAME, trimmed_a, trimmed_b),
        (HTML_NAME, html_a, html_b),
    ):
        if first != second:
            problems.append(
                f"{name} is not reproducible: run-1 sha256 {_sha(first)}, run-2 {_sha(second)}"
            )
    if problems:
        for p in problems:
            print(f"NON-DETERMINISTIC: {p}", file=sys.stderr)
        return 1
    print("Two fresh runs produced byte-identical output (deterministic).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate or check the determinism proof."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="prove determinism by building twice and comparing the two fresh runs, without writing",
    )
    parser.add_argument(
        "--check-committed",
        action="store_true",
        help=(
            "opt-in: compare one fresh build against the committed bytes; only "
            "meaningful in the pinned local regeneration environment, never in CI "
            "(cross-platform float differences would misreport as drift)"
        ),
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    if args.check_committed:
        return check_committed()
    return regenerate()


if __name__ == "__main__":
    sys.exit(main())
