#!/usr/bin/env python3
"""Regenerate (or check) the committed determinism proof in expected_outputs/.

The full ``run.json`` is not byte-deterministic, because the vendored engine writes
a temporary output path and its own timestamp into ``engine.run_metadata``. The parts
Querymantic owns are deterministic: every module slot, and the Output Forge HTML dashboard.
So the committed proof is a trimmed artifact, not the raw run.json:

- ``sample_run.trimmed.json``: the ``querymantic`` metadata (with a pinned timestamp and the
  input hash) plus every ``modules`` slot, with the non-deterministic ``engine`` block
  dropped.
- ``sample_dashboard.html``: the Output Forge HTML dashboard, byte for byte.

Run with no flag to refresh the committed sample files. Run with ``--check`` to
prove determinism: it generates the artifacts twice in temporary directories and
compares the two fresh runs, exiting non-zero if they differ. The committed files
are a readable sample of the output, not a cross-platform byte gate (a different OS
or Python build can reproduce the same numbers with last-bit float differences), so
``--check`` compares two fresh runs rather than the committed bytes.
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
    # The committed proof must be machine-independent: the run-state records the
    # input files as absolute paths, which differ across machines (and would break
    # the cross-machine --check in CI). Store them relative to the plugin root, with
    # forward slashes, so the proof is byte-identical everywhere.
    meta = dict(state["querymantic"])
    meta["inputs"] = [_relative_input(p) for p in meta.get("inputs", [])]
    trimmed = {"querymantic": meta, "modules": state["modules"]}
    trimmed_bytes = (
        json.dumps(trimmed, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    html_bytes = (forge_dir / "dashboard.html").read_bytes()
    return trimmed_bytes, html_bytes


def _relative_input(path_str: str) -> str:
    """Return an input path relative to the plugin root, posix-style.

    Falls back to the file name if the path is not under the plugin root, so the
    proof never carries an absolute, machine-specific path.
    """
    try:
        return Path(path_str).resolve().relative_to(PLUGIN_ROOT).as_posix()
    except ValueError:
        return Path(path_str).name


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regenerate() -> int:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        trimmed_bytes, html_bytes = _build(Path(td))
    (EXPECTED_DIR / TRIMMED_NAME).write_bytes(trimmed_bytes)
    (EXPECTED_DIR / HTML_NAME).write_bytes(html_bytes)
    print(f"Wrote {EXPECTED_DIR / TRIMMED_NAME} (sha256 {_sha(trimmed_bytes)})")
    print(f"Wrote {EXPECTED_DIR / HTML_NAME} (sha256 {_sha(html_bytes)})")
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
        help="compare against committed files instead of writing",
    )
    args = parser.parse_args(argv)
    return check() if args.check else regenerate()


if __name__ == "__main__":
    sys.exit(main())
