#!/usr/bin/env python3
"""Sync and verify the vendored keyword-intelligence engine.

The engine under ``engine/keyword-intelligence/`` is a read-only vendored copy,
meant to stay byte-identical to its source. This script refreshes it from a local
source directory and reports a content manifest. It never touches the network:
the source is always a local path the operator points at.

Subcommands:

- ``verify``: print a sorted manifest (relative path and SHA-256) of the current
  vendored engine, so a drift can be detected by comparing manifests.
- ``sync --source DIR``: copy files from a local source engine directory into the
  vendor, skipping git metadata and Python caches, then print the new manifest.

The byte-identity check between source and vendor is the operator's, by comparing
the two manifests. This script does not delete files, so removing a file that the
source dropped is a manual step.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "keyword-intelligence"

# Names skipped when copying or hashing: git metadata and Python build artifacts.
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}

_HASH_BLOCK_BYTES = 64 * 1024


def _should_skip(rel: Path) -> bool:
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return True
    return rel.suffix in SKIP_FILE_SUFFIXES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_HASH_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest(root: Path) -> list[tuple[str, str]]:
    """Return a sorted list of (relative POSIX path, sha256) for ``root``."""
    rows: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _should_skip(rel):
            continue
        rows.append((rel.as_posix(), _sha256(path)))
    rows.sort(key=lambda r: r[0])
    return rows


def _print_manifest(root: Path) -> None:
    rows = manifest(root)
    for rel, digest in rows:
        print(f"{digest}  {rel}")
    print(f"# {len(rows)} files", file=sys.stderr)


def cmd_verify(_args: argparse.Namespace) -> int:
    if not VENDOR_DIR.is_dir():
        print(f"Error: vendor directory not found: {VENDOR_DIR}", file=sys.stderr)
        return 1
    _print_manifest(VENDOR_DIR)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: source directory not found: {source}", file=sys.stderr)
        return 1
    copied = 0
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if _should_skip(rel):
            continue
        target = VENDOR_DIR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    print(f"# copied {copied} files from {source}", file=sys.stderr)
    _print_manifest(VENDOR_DIR)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sync_engine",
        description="Sync and verify the vendored keyword-intelligence engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="print the vendored engine content manifest")
    sync_p = sub.add_parser("sync", help="copy from a local source engine directory")
    sync_p.add_argument(
        "--source", required=True, help="local path to the source engine directory"
    )
    args = parser.parse_args(argv)
    if args.command == "verify":
        return cmd_verify(args)
    if args.command == "sync":
        return cmd_sync(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
