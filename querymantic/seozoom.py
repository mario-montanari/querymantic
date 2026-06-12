#!/usr/bin/env python3
"""SEOZoom export support: detection, engine column mapping, monthly series.

A SEOZoom keyword export ships Italian headers: ``Keyword``, ``Intent``,
``Vol``, ``Concorrenza`` (competition on the 0 to 1 scale, the export's
difficulty), ``CPC`` and the twelve month columns ``Gen`` through ``Dic``.
The vendored engine's generic mapping knows none of the Italian columns, so
without help it drops Concorrenza, the declared Intent labels and the whole
monthly series.

This module closes that gap without touching the read-only engine and without
rewriting the user's file. Detection looks at the header signature only. The
column mapping is handed to the engine through its own ``--mapping`` override,
so the ORIGINAL export stays the engine input: file hashes, the input manifest
and per-keyword source rows keep pointing at what the user provided. The
Concorrenza values travel verbatim; the engine's column-level difficulty
normalization reads the 0 to 1 scale and scales it to 0 to 100 itself. The
declared Intent labels reach the engine as ``intent_label_raw`` and follow the
engine's own label semantics, the same treatment a Semrush or Ahrefs export
gets. The month columns, which the engine has no concept for, are extracted
here into the parsed-series mapping Demand Pulse already accepts.

The export carries no year, so series periods default to the neutral labels
``m01`` through ``m12``; a caller that knows the calendar year can declare it
(the CLI exposes ``--seozoom-year``) and the periods become ``YYYY-MM``. An
explicitly provided series always wins over the extracted one.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .text import tokenize

# The distinctive SEOZoom headers, lowercased. ``concorrenza`` is the Italian
# column no other supported export ships, so keyword + concorrenza is the
# detection signature.
_SIGNATURE = frozenset({"keyword", "concorrenza"})

# The twelve month columns of the export, in calendar order, lowercased.
MONTH_HEADERS = (
    "gen",
    "feb",
    "mar",
    "apr",
    "mag",
    "giu",
    "lug",
    "ago",
    "set",
    "ott",
    "nov",
    "dic",
)

# SEOZoom header -> engine canonical field, merged into the engine's own
# mapping through its ``--mapping`` override (the engine lowercases the keys).
_ENGINE_MAPPING = {
    "keyword": "keyword",
    "intent": "intent_label_raw",
    "vol": "volume",
    "volume": "volume",
    "concorrenza": "difficulty",
    "cpc": "cpc",
}


class SeozoomError(Exception):
    """Raised when a detected SEOZoom export cannot be read coherently."""


def _norm(text: str) -> str:
    """Normalize a keyword exactly as Demand Pulse joins series to corpus."""
    return " ".join(tokenize(text))


def _read_header(path: Path) -> list[str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.reader(fh):
                return row
    except (OSError, UnicodeDecodeError, csv.Error):
        return []
    return []


def is_seozoom_export(path: Path) -> bool:
    """True when the file's header carries the SEOZoom signature."""
    header = {cell.strip().lower() for cell in _read_header(path)}
    return _SIGNATURE.issubset(header)


def engine_mapping() -> dict[str, str]:
    """The column override to hand the engine for SEOZoom inputs."""
    return dict(_ENGINE_MAPPING)


def _parse_cell(cell: str, path: Path, row_index: int) -> float | None:
    """One monthly cell: empty is a gap, anything else must be a non-negative number."""
    raw = cell.strip().replace(",", "").replace(" ", "")
    if raw == "":
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise SeozoomError(
            f"{path} row {row_index}: non-numeric monthly value {cell!r}"
        ) from exc
    if value < 0:
        raise SeozoomError(f"{path} row {row_index}: negative monthly value {cell!r}")
    return value


def extract_series(paths: list[Path], year: str | None = None) -> dict[str, Any] | None:
    """Extract the monthly series from SEOZoom exports for Demand Pulse.

    Returns the parsed-series mapping Demand Pulse accepts
    (``{"periods": [...], "by_keyword": {normalized_keyword: [value | None, ...]}}``)
    or ``None`` when no file carries at least two month columns or no usable
    row exists. Keywords are normalized with the same rule Demand Pulse uses
    for the join; a keyword appearing twice keeps its last occurrence,
    mirroring the series-file loader. Periods are ``YYYY-MM`` when ``year`` is
    declared, otherwise the neutral ``m01`` through ``m12`` (the export
    carries no year and one is never invented).
    """
    periods: list[str] | None = None
    by_keyword: dict[str, list[float | None]] = {}

    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            continue
        header = [cell.strip().lower() for cell in rows[0]]
        month_cols = [
            (header.index(month), position)
            for position, month in enumerate(MONTH_HEADERS, start=1)
            if month in header
        ]
        if len(month_cols) < 2:
            continue
        try:
            keyword_col = header.index("keyword")
        except ValueError:
            continue

        file_periods = [
            f"{year}-{position:02d}" if year else f"m{position:02d}"
            for _, position in month_cols
        ]
        if periods is None:
            periods = file_periods
        elif periods != file_periods:
            raise SeozoomError(
                f"{path}: month columns differ from the first SEOZoom input"
            )

        for row_index, row in enumerate(rows[1:], start=2):
            if len(row) <= keyword_col:
                continue
            keyword = _norm(row[keyword_col])
            if not keyword:
                continue
            by_keyword[keyword] = [
                _parse_cell(row[col], path, row_index) if col < len(row) else None
                for col, _ in month_cols
            ]

    if periods is None or not by_keyword:
        return None
    return {"periods": periods, "by_keyword": by_keyword}
