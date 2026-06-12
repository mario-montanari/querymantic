#!/usr/bin/env python3
"""Adapter-level regression tests for the engine's difficulty scale handling.

The vendored engine used to corrupt a difficulty column exported on the 0-1
decimal scale: the decimal point was stripped as a thousands separator, so
"0.5" became 5 and "1.0" became 10. Fixed upstream in mario-montanari/
keyword-intelligence commit 798db1d (the full test matrix lives there in
tests/); these tests pin the behavior through the adapter with synthetic
fixtures so a future engine re-vendor cannot silently reintroduce the bug.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import engine_adapter  # noqa: E402


def _write_csv(tmp_path: Path, difficulties: list[str]) -> Path:
    path = tmp_path / "synthetic.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["keyword", "difficulty"])
        for i, value in enumerate(difficulties):
            writer.writerow([f"synthetic keyword {i}", value])
    return path


def _difficulties(tmp_path: Path, values: list[str]) -> list[int]:
    analysis = engine_adapter.run_engine(PLUGIN_ROOT, [_write_csv(tmp_path, values)])
    return [k["metrics"]["difficulty"] for k in analysis["keywords"]]


def test_decimal_scale_difficulty_survives_through_the_adapter(
    tmp_path: Path,
) -> None:
    """The bug footprint was [8, 45, 5, 9, 10] before the upstream fix."""
    values = ["0.08", "0.45", "0.5", "0.9", "1.0"]
    assert _difficulties(tmp_path, values) == [8, 45, 50, 90, 100]


def test_integer_scale_difficulty_is_unchanged(tmp_path: Path) -> None:
    assert _difficulties(tmp_path, ["8", "45", "50"]) == [8, 45, 50]


def test_zero_one_integer_column_reads_as_decimal_scale(
    tmp_path: Path,
) -> None:
    """A column of bare 0 and 1 is treated as a 0-1 scale by design."""
    assert _difficulties(tmp_path, ["0", "1", "1", "0"]) == [0, 100, 100, 0]
