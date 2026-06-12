#!/usr/bin/env python3
"""SEOZoom export eval: what the suite reads from a real-shaped export.

A SEOZoom keyword export ships Italian headers (Keyword, Intent, Vol,
Concorrenza, CPC, then the twelve month columns Gen through Dic). The engine's
generic mapping used to read Keyword, Vol and CPC and silently drop the rest;
the previous commit of this file pins that loss (difficulty None everywhere,
every keyword informational at 0.3, Demand Pulse unknown with zero series
points). The dedicated SEOZoom path closes it: the export is detected from its
header signature, the engine receives the SEOZoom column mapping through its
own override (the user's file is never rewritten, so hashes and per-row
traceability keep pointing at the original), Concorrenza becomes the
difficulty column on the engine's own column-level 0-1 scaling, the declared
Intent labels reach the engine as intent_label_raw under the engine's own
label semantics, and the month columns feed Demand Pulse when no explicit
series is given.

Declared engine-semantics limits, pinned as documented behavior rather than
hidden: a "Commercial" label does not move the engine's
commercial_investigation axis, and a multi-label cell nudges every named axis
so ties resolve to informational. Both follow the engine's own
intent_label_raw matching, the same treatment a Semrush or Ahrefs export gets.

The fixture in fixtures/seozoom_export.csv carries the exact real header
signature with invented keywords and values; no real export ever enters the
repository in any form. The eval-then-fix history is the fail-before /
pass-after proof.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import pipeline, seozoom  # noqa: E402

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


def _run_state(tmp: Path, modules: tuple[str, ...] = (), **kwargs) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [FIXTURE_PATH],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        **kwargs,
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


def test_detection_is_signature_based() -> None:
    """SEOZoom is detected from its header; the supported tool exports are not."""
    assert seozoom.is_seozoom_export(FIXTURE_PATH)
    samples = PLUGIN_ROOT / "assets" / "samples"
    for sample in sorted(samples.glob("*.csv")):
        assert not seozoom.is_seozoom_export(sample), sample.name


def test_difficulty_reads_concorrenza_through_the_engine_mapping(
    tmp_path: Path,
) -> None:
    """Concorrenza reaches the engine as the difficulty column.

    The values travel verbatim and the engine's column-level normalization
    reads the 0 to 1 scale and scales to 0 to 100 (ROUND_HALF_UP), bare 1 and
    0 included because the column carries decimal values.
    """
    state = _run_state(tmp_path)
    difficulties = [k["metrics"]["difficulty"] for k in state["engine"]["keywords"]]
    assert difficulties == [8, 45, 50, 90, 100, 0, 66, 9, 30, 12, 25, 70]
    # The mapping override is recorded portably: the bare file name, no path.
    assert state["engine"]["parameters"].get("mapping") == "column_mapping.json"


def test_intent_labels_reach_the_engine(tmp_path: Path) -> None:
    """Declared Intent labels are read under the engine's own label semantics.

    Transactional and Navigational singles decide their zero-signal keywords.
    The two declared limits stay pinned: "Commercial" does not move
    commercial_investigation, and the multi-label row resolves its tie to
    informational.
    """
    state = _run_state(tmp_path)
    vectors = [
        (
            k["enrichment"]["intent_vector"]["query_type"],
            k["enrichment"]["intent_confidence"],
        )
        for k in state["engine"]["keywords"]
    ]
    assert vectors == [
        ("informational", 0.1),  # Informational label
        ("informational", 0.1),  # Informational label
        ("informational", 0.3),  # empty label: no-signal default
        ("transactional", 0.1),  # Transactional label, recovered
        ("informational", 0.3),  # Commercial label: declared engine limit
        ("navigational", 0.1),  # Navigational label, recovered
        ("informational", 0.1),  # multi-label tie: declared engine limit
        ("informational", 0.1),
        ("informational", 0.3),  # empty label
        ("informational", 0.1),
        ("informational", 0.1),
        ("informational", 0.1),
    ]


def test_month_columns_feed_demand_pulse(tmp_path: Path) -> None:
    """The twelve month columns become the Demand Pulse series automatically.

    Periods default to the neutral m01 to m12 labels (the export carries no
    year and one is never invented). The sparse row keeps its gaps and still
    clears the minimum-points threshold.
    """
    state = _run_state(tmp_path, modules=("demand_pulse",))
    slot = state["modules"]["demand_pulse"]
    series = slot["series"]
    assert series["periods"] == [f"m{i:02d}" for i in range(1, 13)]
    assert series["keywords_with_series"] == 12
    clusters = slot["clusters"]
    assert len(clusters) == 12
    assert Counter(c["state"] for c in clusters) == Counter({"rising": 12})
    assert sorted(c["series_points"] for c in clusters) == [10] + [12] * 11
    assert all("no usable series" not in (c.get("note") or "") for c in clusters)


def test_declared_year_labels_the_periods(tmp_path: Path) -> None:
    state = _run_state(tmp_path, modules=("demand_pulse",), seozoom_year="2025")
    periods = state["modules"]["demand_pulse"]["series"]["periods"]
    assert periods == [f"2025-{i:02d}" for i in range(1, 13)]


def test_explicit_series_wins_over_extraction(tmp_path: Path) -> None:
    explicit = {
        "periods": ["2024-01", "2024-02", "2024-03"],
        "by_keyword": {"impastatrice planetaria dosi": [1.0, 2.0, 3.0]},
    }
    state = _run_state(
        tmp_path,
        modules=("demand_pulse",),
        module_kwargs={"demand_pulse": {"series": explicit}},
    )
    periods = state["modules"]["demand_pulse"]["series"]["periods"]
    assert periods == ["2024-01", "2024-02", "2024-03"]


def test_series_extraction_contract(tmp_path: Path) -> None:
    """Unit contract: gaps stay None, junk raises, non-seozoom yields None."""
    series = seozoom.extract_series([FIXTURE_PATH])
    sparse = series["by_keyword"]["compostiera domestica odori"]
    assert sparse[0] is None and sparse[1] is None and sparse[2] == 100.0

    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Keyword,Concorrenza,Gen,Feb\nfioriera balcone legno,0.2,12,not-a-number\n",
        encoding="utf-8",
    )
    try:
        seozoom.extract_series([bad])
    except seozoom.SeozoomError as exc:
        assert "non-numeric monthly value" in str(exc)
    else:
        raise AssertionError("junk monthly value must raise SeozoomError")

    plain = tmp_path / "plain.csv"
    plain.write_text("keyword,volume\nfioriera balcone legno,10\n", encoding="utf-8")
    assert seozoom.extract_series([plain]) is None
