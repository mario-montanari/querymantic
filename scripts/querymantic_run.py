#!/usr/bin/env python3
"""Querymantic command-line entry point.

Subcommands:

- ``run``: ingest keyword exports, run the vendored engine, and write a validated
  ``run.json``. In the Sprint 0 scaffold no analysis modules run yet, so the
  output carries the engine analysis with empty module slots.
- ``validate``: check that an existing ``run.json`` satisfies the run-state
  contract.

Both subcommands print a human-readable summary by default and a machine-readable
JSON object with ``--json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the plugin root importable so ``querymantic`` resolves whether the script
# is run from the repo root or elsewhere.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import pipeline, run_state  # noqa: E402  (path set above)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="querymantic",
        description="Offline keyword and demand intelligence suite.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run the pipeline and write run.json")
    run_p.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="input CSV/TSV files or directories of them",
    )
    run_p.add_argument(
        "--output",
        required=True,
        help="path to write run.json",
    )
    run_p.add_argument("--label", default="", help="label for this run")
    run_p.add_argument(
        "--client-domain", default="", help="client domain for gap analysis"
    )
    run_p.add_argument(
        "--brand-list",
        default="",
        help="comma-separated brand terms for branded split",
    )
    run_p.add_argument(
        "--modules",
        nargs="*",
        default=[],
        help="modules to run, in order",
    )
    run_p.add_argument(
        "--series",
        default=None,
        help="optional monthly-series CSV for demand_pulse (wide: keyword + YYYY-MM columns)",
    )
    run_p.add_argument(
        "--livewire",
        default=None,
        help="optional livewire_capture.json with observed Search Console and AI-citation data",
    )
    run_p.add_argument(
        "--forge-out",
        default=None,
        help="output directory for Output Forge artifacts (defaults to a 'forge_output' folder beside run.json)",
    )
    run_p.add_argument(
        "--brand",
        default=None,
        help="optional brand.json for white-label Output Forge output",
    )
    run_p.add_argument(
        "--forge-formats",
        nargs="*",
        default=None,
        help="Output Forge formats to render (subset of: html pptx docx xlsx); default renders all available",
    )
    run_p.add_argument(
        "--forge-interactive",
        action="store_true",
        help="also render the interactive Plotly HTML dashboard (needs the vendored plotly.js bundle; the default HTML stays script-free SVG)",
    )
    run_p.add_argument(
        "--deterministic-timestamp",
        default=None,
        help="fixed ISO 8601 timestamp for reproducible output",
    )
    run_p.add_argument("--json", action="store_true", help="emit JSON summary")
    run_p.add_argument("--quiet", action="store_true", help="suppress the summary")

    val_p = sub.add_parser("validate", help="validate an existing run.json")
    val_p.add_argument("path", help="path to a run.json file")
    val_p.add_argument("--json", action="store_true", help="emit JSON result")

    forge_p = sub.add_parser(
        "forge", help="render deliverables from an existing run.json"
    )
    forge_p.add_argument("path", help="path to a run.json file")
    forge_p.add_argument(
        "--out",
        default=None,
        help="output directory for artifacts (default: forge_output beside run.json)",
    )
    forge_p.add_argument(
        "--brand", default=None, help="optional brand.json for white-label output"
    )
    forge_p.add_argument(
        "--formats",
        nargs="*",
        default=None,
        help="formats to render (subset of: html pptx docx xlsx)",
    )
    forge_p.add_argument(
        "--interactive",
        action="store_true",
        help="also render the interactive Plotly HTML dashboard (needs the vendored plotly.js bundle; the default HTML stays script-free SVG)",
    )
    forge_p.add_argument(
        "--output",
        default=None,
        help="where to write the updated run.json (default: in place)",
    )
    forge_p.add_argument("--json", action="store_true", help="emit JSON summary")
    forge_p.add_argument("--quiet", action="store_true", help="suppress the summary")

    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    inputs = [Path(p) for p in args.inputs]
    output = Path(args.output)

    module_kwargs: dict[str, dict] = {}
    if args.series and "demand_pulse" in args.modules:
        from modules.demand_pulse import DemandPulseError, load_series

        try:
            module_kwargs["demand_pulse"] = {"series": load_series(Path(args.series))}
        except DemandPulseError as exc:
            _fail(str(exc), as_json=args.json)
            return 1

    if args.livewire and "live_wire" in args.modules:
        from modules.live_wire import LiveWireError, load_capture

        try:
            module_kwargs["live_wire"] = {"capture": load_capture(Path(args.livewire))}
        except LiveWireError as exc:
            _fail(str(exc), as_json=args.json)
            return 1

    if "output_forge" in args.modules:
        from modules.output_forge import FORMATS
        from modules.output_forge.brand import BrandError, load_brand

        forge_kwargs: dict = {}
        forge_kwargs["out_dir"] = (
            Path(args.forge_out) if args.forge_out else output.parent / "forge_output"
        )
        if args.brand:
            try:
                forge_kwargs["brand"] = load_brand(Path(args.brand))
            except BrandError as exc:
                _fail(str(exc), as_json=args.json)
                return 1
        forge_formats = (
            list(args.forge_formats) if args.forge_formats is not None else None
        )
        if forge_formats is not None:
            unknown = [f for f in forge_formats if f not in FORMATS]
            if unknown:
                _fail(
                    f"unknown --forge-formats value(s): {', '.join(sorted(unknown))}",
                    as_json=args.json,
                )
                return 1
        if args.forge_interactive:
            base = (
                forge_formats
                if forge_formats is not None
                else ["html", "pptx", "docx", "xlsx"]
            )
            if "interactive_html" not in base:
                base = base + ["interactive_html"]
            forge_formats = base
        if forge_formats is not None:
            forge_kwargs["formats"] = tuple(forge_formats)
        module_kwargs["output_forge"] = forge_kwargs

    try:
        state = pipeline.run_pipeline(
            PLUGIN_ROOT,
            inputs,
            output,
            label=args.label,
            client_domain=args.client_domain,
            brand_list=args.brand_list,
            modules_to_run=tuple(args.modules),
            generated_at=args.deterministic_timestamp,
            module_kwargs=module_kwargs,
        )
    except (pipeline.PipelineError, run_state.RunStateError) as exc:
        _fail(str(exc), as_json=args.json)
        return 1

    engine = state.get("engine") or {}
    corpus = engine.get("corpus_summary") or {}
    summary = {
        "status": "ok",
        "output": str(output),
        "input_hash": state["querymantic"]["input_hash"],
        "input_files": len(state["querymantic"]["inputs"]),
        "total_keywords": corpus.get("total_keywords"),
        "modules_run": state["querymantic"]["modules_run"],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif not args.quiet:
        print(f"Wrote {output}")
        print(f"  input files:    {summary['input_files']}")
        print(f"  input hash:     {summary['input_hash']}")
        print(f"  total keywords: {summary['total_keywords']}")
        ran = ", ".join(summary["modules_run"]) or "(none)"
        print(f"  modules run:    {ran}")
        forge = (state.get("modules") or {}).get("output_forge")
        if isinstance(forge, dict):
            produced = (
                ", ".join(a["format"] for a in forge.get("artifacts", [])) or "(none)"
            )
            print(f"  forge artifacts: {produced}")
            for s in forge.get("skipped", []):
                print(f"    skipped {s['format']}: {s['reason']}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        run_state.load_run_state(path)
    except run_state.RunStateValidationError as exc:
        result = {"status": "invalid", "path": str(path), "errors": exc.errors}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"INVALID: {path}")
            for err in exc.errors:
                print(f"  - {err}")
        return 1
    except run_state.RunStateError as exc:
        _fail(str(exc), as_json=args.json, path=str(path))
        return 1

    result = {"status": "valid", "path": str(path)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"VALID: {path}")
    return 0


def _cmd_forge(args: argparse.Namespace) -> int:
    from modules.output_forge import (
        FORMATS,
        ModuleError,
        OutputForgeError,
        output_forge,
    )
    from modules.output_forge.brand import BrandError, load_brand

    path = Path(args.path)
    try:
        state = run_state.load_run_state(path)
    except run_state.RunStateError as exc:
        _fail(str(exc), as_json=args.json, path=str(path))
        return 1

    out_dir = Path(args.out) if args.out else path.parent / "forge_output"
    brand = None
    if args.brand:
        try:
            brand = load_brand(Path(args.brand))
        except BrandError as exc:
            _fail(str(exc), as_json=args.json)
            return 1
    formats = (
        tuple(args.formats)
        if args.formats is not None
        else ("html", "pptx", "docx", "xlsx")
    )
    if args.interactive and "interactive_html" not in formats:
        formats = formats + ("interactive_html",)
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        _fail(
            f"unknown --formats value(s): {', '.join(sorted(unknown))}",
            as_json=args.json,
        )
        return 1

    try:
        output_forge(state, out_dir=out_dir, brand=brand, formats=formats)
    except (ModuleError, OutputForgeError) as exc:
        _fail(str(exc), as_json=args.json)
        return 1
    run_state.mark_module_run(state, "output_forge")

    dest = Path(args.output) if args.output else path
    run_state.save_run_state(state, dest)

    forge = state["modules"]["output_forge"]
    summary = {
        "status": "ok",
        "run_json": str(dest),
        "out_dir": str(out_dir),
        "artifacts": [a["format"] for a in forge["artifacts"]],
        "skipped": [s["format"] for s in forge["skipped"]],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif not args.quiet:
        print(f"Rendered into {out_dir}")
        print(f"  artifacts: {', '.join(summary['artifacts']) or '(none)'}")
        for s in forge["skipped"]:
            print(f"  skipped {s['format']}: {s['reason']}")
        print(f"  updated:   {dest}")
    return 0


def _fail(message: str, as_json: bool, path: str | None = None) -> None:
    if as_json:
        payload = {"status": "error", "error": message}
        if path is not None:
            payload["path"] = path
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Error: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "forge":
        return _cmd_forge(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
