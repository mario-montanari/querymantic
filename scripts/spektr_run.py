#!/usr/bin/env python3
"""Spektr command-line entry point.

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

# Make the plugin root importable so ``spektr_core`` resolves whether the script
# is run from the repo root or elsewhere.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from spektr_core import pipeline, run_state  # noqa: E402  (path set above)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spektr",
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
        help="modules to run, in order (none available in the scaffold)",
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

    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    inputs = [Path(p) for p in args.inputs]
    output = Path(args.output)
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
        )
    except (pipeline.PipelineError, run_state.RunStateError) as exc:
        _fail(str(exc), as_json=args.json)
        return 1

    engine = state.get("engine") or {}
    corpus = engine.get("corpus_summary") or {}
    summary = {
        "status": "ok",
        "output": str(output),
        "input_hash": state["spektr"]["input_hash"],
        "input_files": len(state["spektr"]["inputs"]),
        "total_keywords": corpus.get("total_keywords"),
        "modules_run": state["spektr"]["modules_run"],
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
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
