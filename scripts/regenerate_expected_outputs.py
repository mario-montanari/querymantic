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
        help="prove determinism by building twice and comparing the two fresh runs, without writing",
    )
    args = parser.parse_args(argv)
    return check() if args.check else regenerate()


if __name__ == "__main__":
    sys.exit(main())
