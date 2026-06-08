#!/usr/bin/env python3
"""Sprint 1 tests: the entity extractor and the Entity Web module.

Covers the extractor scoring on a tiny known corpus, the module's output contract
on the bundled sample corpus, and determinism across two runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from spektr_core import pipeline, run_state  # noqa: E402
from spektr_core.entity_extractor import tfidf_position_extract  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def test_extractor_counts_and_idf() -> None:
    docs = [
        {"text": "running shoes", "language": "en"},
        {"text": "trail running shoes", "language": "en"},
        {"text": "best shoes", "language": "en"},
    ]
    result = tfidf_position_extract(docs, min_df=2, max_ngram=2)

    # "shoes" appears in all three documents; "running" and "running shoes" in two.
    assert result["shoes"]["df"] == 3
    assert result["running"]["df"] == 2
    assert result["running shoes"]["df"] == 2

    # A term present in every document has zero inverse document frequency.
    assert result["shoes"]["idf"] == 0.0

    # Singletons are dropped at min_df = 2.
    assert "best" not in result
    assert "trail" not in result

    # Scores are positive and deterministic.
    assert result["shoes"]["score"] > 0


def test_entity_web_contract_on_samples(tmp_path: Path) -> None:
    output = tmp_path / "run.json"
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        output,
        modules_to_run=("entity_web",),
        generated_at=FIXED_TIMESTAMP,
    )
    loaded = run_state.load_run_state(output)
    run_state.validate_run_state(loaded)

    assert loaded["spektr"]["modules_run"] == ["entity_web"]
    ew = loaded["modules"]["entity_web"]
    assert isinstance(ew, dict)

    summary = ew["summary"]
    assert summary["entities_total"] == len(ew["entities"])
    assert summary["owned_entities"] + summary["demand_only_entities"] == summary["entities_total"]
    assert summary["gap_count"] == len(ew["entity_gaps"])

    # Every gap entity is genuinely unowned.
    owned_by_name = {e["entity"]: e["owned"] for e in ew["entities"]}
    for gap in ew["entity_gaps"]:
        assert owned_by_name.get(gap["entity"]) is False

    # The central entity of the sample corpus is present.
    names = {e["entity"] for e in ew["entities"]}
    assert "running shoes" in names

    # The graph respects its node cap.
    assert len(ew["graph"]["nodes"]) <= ew["params"]["graph_max_nodes"]

    # Authority ratios are bounded.
    for cluster in ew["topical_authority"]:
        assert 0.0 <= cluster["authority"] <= 1.0

    # The returned state matches the file.
    assert state["modules"]["entity_web"]["summary"] == summary


def test_entity_web_is_deterministic(tmp_path: Path) -> None:
    first = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp_path / "a.json",
        modules_to_run=("entity_web",),
        generated_at=FIXED_TIMESTAMP,
    )
    second = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp_path / "b.json",
        modules_to_run=("entity_web",),
        generated_at=FIXED_TIMESTAMP,
    )
    assert first["modules"]["entity_web"] == second["modules"]["entity_web"]
