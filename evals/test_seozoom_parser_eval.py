#!/usr/bin/env python3
"""SEOZoom export eval: what the suite reads from a real-shaped export.

A SEOZoom keyword export ships Italian headers (Keyword, Intent, Vol,
Concorrenza, CPC, then the twelve month columns Gen through Dic). The engine's
generic mapping reads Keyword, Vol and CPC and silently drops the rest: the
Concorrenza column (competition on the 0 to 1 scale, the export's difficulty),
the declared Intent labels, and the whole monthly series, so difficulty stays
empty, every keyword flattens to informational, and Demand Pulse reports
unknown for lack of a series.

The fixture in fixtures/seozoom_export.csv carries the exact real header
signature with invented keywords and values; no real export ever enters the
repository in any form. The assertions are an exact snapshot of the CURRENT
generic-path behavior, so this eval documents the loss rather than failing
yet; the fix commit updates them to the recovered values, and the
eval-then-fix history is the fail-before/pass-after proof.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import pipeline  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "seozoom_export.csv"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"

# The header signature of a real SEOZoom keyword export, verbatim.
SEOZOOM_HEADER = [
    "Keyword",
    "Intent",
    "Vol",
    "Concorrenza",
    "CPC",
    "Gen",
    "Feb",
    "Mar",
    "Apr",
    "Mag",
    "Giu",
    "Lug",
    "Ago",
    "Set",
    "Ott",
    "Nov",
    "Dic",
]


def _run_state(tmp: Path, modules: tuple[str, ...] = ()) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [FIXTURE_PATH],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
    )


def test_fixture_matches_the_seozoom_signature() -> None:
    """The fixture must keep the real header shape, or the eval proves nothing."""
    with FIXTURE_PATH.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == SEOZOOM_HEADER
    keywords = [r[0] for r in rows[1:] if r and r[0].strip()]
    assert len(keywords) == 12
    assert len(set(keywords)) == 12, "fixture keywords must be unique"
    # Every Concorrenza value sits on the export's 0 to 1 scale.
    concorrenza = [r[3] for r in rows[1:] if r[3].strip() != ""]
    assert len(concorrenza) == 12
    assert all(0.0 <= float(c) <= 1.0 for c in concorrenza)


def test_difficulty_baseline_concorrenza_is_dropped(tmp_path: Path) -> None:
    """Baseline: the generic mapping has no Concorrenza synonym, difficulty stays empty."""
    state = _run_state(tmp_path)
    difficulties = [k["metrics"]["difficulty"] for k in state["engine"]["keywords"]]
    assert difficulties == [None] * 12
    # No column mapping reaches the engine on the generic path.
    assert state["engine"]["parameters"].get("mapping") is None


def test_intent_baseline_declared_labels_are_dropped(tmp_path: Path) -> None:
    """Baseline: the Intent column is unmapped, every keyword flattens to informational.

    The fixture declares Transactional, Navigational, Commercial and a
    multi-label row; none of them reaches the engine, so all twelve keywords
    land on the no-signal default (informational at confidence 0.3).
    """
    state = _run_state(tmp_path)
    vectors = [
        (
            k["enrichment"]["intent_vector"]["query_type"],
            k["enrichment"]["intent_confidence"],
        )
        for k in state["engine"]["keywords"]
    ]
    assert vectors == [("informational", 0.3)] * 12


def test_series_baseline_month_columns_are_dropped(tmp_path: Path) -> None:
    """Baseline: the twelve month columns feed nothing, Demand Pulse reports unknown."""
    state = _run_state(tmp_path, modules=("demand_pulse",))
    slot = state["modules"]["demand_pulse"]
    clusters = slot["clusters"]
    assert len(clusters) == 12
    assert Counter(c["state"] for c in clusters) == Counter({"unknown": 12})
    assert all(c["series_points"] == 0 for c in clusters)
    assert all("no usable series" in c["note"] for c in clusters)
