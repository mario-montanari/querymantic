#!/usr/bin/env python3
"""Sprint 2 tests: BM25 and the Fan-Out Radar module.

Covers BM25 scoring sanity, the module output contract on the sample corpus, the
gatekeeper rule, graceful degradation without Entity Web, and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.fan_out_radar import ARCHETYPES, GATEKEEPER_MIN_CENTRALITY  # noqa: E402
from spektr_core import pipeline, run_state  # noqa: E402
from spektr_core.text.bm25 import BM25  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def test_bm25_basic() -> None:
    corpus = [["running", "shoes"], ["trail", "shoes"], ["dog", "food"]]
    bm25 = BM25(corpus)
    # A document with the query term scores higher than one without.
    assert bm25.score(["running"], 0) > 0
    assert bm25.score(["running"], 2) == 0
    # "shoes" appears in two of three docs, so it still scores on those.
    assert bm25.max_score(["shoes"]) > 0
    # Coverage counts documents at or above a threshold.
    assert bm25.coverage_count(["shoes"], 0.0) == 3


def _run(tmp: Path, modules: tuple[str, ...]) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
    )


def test_fan_out_contract(tmp_path: Path) -> None:
    state = _run(tmp_path, ("entity_web", "fan_out_radar"))
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["spektr"]["modules_run"] == ["entity_web", "fan_out_radar"]

    fo = loaded["modules"]["fan_out_radar"]
    assert fo["mode"] == "expected"
    assert set(fo["archetypes"]) == set(ARCHETYPES)
    assert fo["clusters"], "expected at least one cluster report"

    for cluster in fo["clusters"]:
        cov = cluster["coverage"]
        assert 0.0 <= cov["cover_at_tau"] <= 1.0
        assert cov["covered"] <= cov["total"]
        head_norm = " ".join(cluster["head"].lower().split())
        for sq in cluster["sub_queries"]:
            assert sq["archetype"] in ARCHETYPES
            # No sub-query is just the head again.
            assert " ".join(sq["query"].lower().split()) != head_norm
            if sq["gatekeeper"]:
                assert sq["originating_volume"] == 0
                assert sq["centrality"] >= GATEKEEPER_MIN_CENTRALITY


def test_fan_out_degrades_without_entity_web(tmp_path: Path) -> None:
    # Running fan_out_radar alone must still work: related falls back to frequent
    # member tokens when the Entity Web graph is absent.
    state = _run(tmp_path, ("fan_out_radar",))
    fo = state["modules"]["fan_out_radar"]
    assert fo["clusters"]
    assert any(c["sub_queries"] for c in fo["clusters"])


def test_fan_out_deterministic(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", ("entity_web", "fan_out_radar"))
    b = _run(tmp_path / "b", ("entity_web", "fan_out_radar"))
    assert a["modules"]["fan_out_radar"] == b["modules"]["fan_out_radar"]
