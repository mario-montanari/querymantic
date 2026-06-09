#!/usr/bin/env python3
"""Sprint 0 smoke test: the empty pipeline produces a valid run.json.

Runs the real pipeline on the bundled sample corpus, then checks the run-state
contract, the engine population, the empty module slots, and the determinism of
the input hash.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import pipeline, run_state  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def test_pipeline_produces_valid_run(tmp_path: Path) -> None:
    output = tmp_path / "run.json"
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        output,
        label="smoke",
        generated_at=FIXED_TIMESTAMP,
    )

    # The written file loads and validates against the contract.
    loaded = run_state.load_run_state(output)
    run_state.validate_run_state(loaded)

    # Metadata.
    assert loaded["querymantic"]["schema_version"] == run_state.SCHEMA_VERSION
    assert len(loaded["querymantic"]["input_hash"]) == 64
    assert loaded["querymantic"]["modules_run"] == []
    assert loaded["querymantic"]["inputs"], "inputs should list the sample files"

    # Engine populated with a real corpus.
    engine = loaded["engine"]
    assert isinstance(engine, dict)
    assert engine["corpus_summary"]["total_keywords"] > 0

    # Every module slot is present and null.
    for key in run_state.MODULE_KEYS:
        assert loaded["modules"][key] is None

    # The returned state matches the written one.
    assert state["querymantic"]["input_hash"] == loaded["querymantic"]["input_hash"]


def test_input_hash_is_deterministic() -> None:
    files = pipeline.expand_inputs([SAMPLES])
    first = run_state.compute_input_hash(files)
    second = run_state.compute_input_hash(list(reversed(files)))
    assert first == second, "hash must not depend on input order"
    assert len(first) == 64
