#!/usr/bin/env python3
"""Sprint 8 tests: the Language Layer module (the Italian fifth language).

Covers the engine gap this module closes (Italian misread on language and intent),
the conservative strictly-greater detection, the evidence-gated intent override,
the no-override-without-a-marker case, the recomputed aggregates, the audit-slot
contract, the critical guard that an English corpus is untouched, the schema bump,
the helper math, and determinism.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from collections import Counter

from modules.language_layer import (  # noqa: E402
    _engine_vote_score,
    _italian_intent,
    load_gazetteer,
)
from querymantic import pipeline, run_state  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
IT_SAMPLES = SAMPLES / "it"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"


def _run(tmp: Path, inputs: Path, modules: tuple[str, ...]) -> dict:
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [inputs],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
    )


# --- the engine gap this module closes -------------------------------------


def test_engine_misreads_italian_baseline(tmp_path: Path) -> None:
    """With no module, the engine tags no keyword Italian and cannot read Italian markers."""
    state = _run(tmp_path, IT_SAMPLES, ())
    engine = state["engine"]
    assert (
        "it" not in engine["corpus_summary"]["by_language"]
    )  # the engine has no Italian
    by_kw = {
        k["keyword"]: k["enrichment"]["intent_vector"]["query_type"]
        for k in engine["keywords"]
    }
    # The engine's tables hold no Italian markers, so these are misclassified.
    assert by_kw["migliori scarpe da running 2026"] != "commercial_investigation"
    assert by_kw["recensioni scarpe brooks ghost"] != "commercial_investigation"
    assert by_kw["accedi area clienti runner shop"] != "navigational"


# --- detection --------------------------------------------------------------


def test_language_layer_detects_italian(tmp_path: Path) -> None:
    state = _run(tmp_path, IT_SAMPLES, ("language_layer",))
    corpus = state["engine"]["corpus_summary"]
    slot = state["modules"]["language_layer"]
    assert corpus["by_language"].get("it", 0) >= 13
    assert slot["summary"]["detected_italian"] >= 13
    # The telegraphic, function-word-free phrase is left as the engine read it.
    stayed = {
        c
        for k in state["engine"]["keywords"]
        if k["language"] != "it"
        for c in [k["keyword"]]
    }
    assert "scarpe running uomo" in stayed


def test_detection_is_strictly_greater_and_conservative() -> None:
    """The engine vote is recovered from confidence; ties keep the engine."""
    assert _engine_vote_score(0.4) == 0  # no-signal default
    assert _engine_vote_score(0.65) == 1
    assert _engine_vote_score(0.8) == 2
    assert _engine_vote_score(0.95) == 3


# --- intent override --------------------------------------------------------


def test_intent_override_fires_on_italian_markers(tmp_path: Path) -> None:
    state = _run(tmp_path, IT_SAMPLES, ("language_layer",))
    by_kw = {
        k["keyword"]: k["enrichment"]["intent_vector"]["query_type"]
        for k in state["engine"]["keywords"]
    }
    assert by_kw["prezzo scarpe nike pegasus"] == "transactional"
    assert by_kw["migliori scarpe da running 2026"] == "commercial_investigation"
    assert by_kw["recensioni scarpe brooks ghost"] == "commercial_investigation"
    assert by_kw["accedi area clienti runner shop"] == "navigational"


def test_intent_kept_when_no_italian_marker_fires(tmp_path: Path) -> None:
    """A keyword detected as Italian only by function words keeps the engine intent."""
    state = _run(tmp_path, IT_SAMPLES, ("language_layer",))
    slot = state["modules"]["language_layer"]
    lang_kws = {c["keyword"] for c in slot["language_changes"]}
    intent_kws = {c["keyword"] for c in slot["intent_changes"]}
    # This phrase flips to Italian (da, per) but has no intent marker.
    assert "scarpe da corsa per principianti" in lang_kws
    assert "scarpe da corsa per principianti" not in intent_kws


def test_italian_intent_helper_mirrors_engine_weighting() -> None:
    gaz = load_gazetteer()
    markers = gaz["intent_markers"]
    pronouns = frozenset(gaz["question_pronouns"])
    # A transactional marker wins.
    qt, conf, cue = _italian_intent("prezzo scarpe nike", markers, pronouns, [])
    assert qt == "transactional" and cue == "transactional:prezzo"
    # No Italian evidence: the gate returns None so the engine intent is kept.
    qt, conf, cue = _italian_intent("scarpe running uomo", markers, pronouns, [])
    assert cue is None


# --- aggregates -------------------------------------------------------------


def test_aggregates_recomputed(tmp_path: Path) -> None:
    state = _run(tmp_path, IT_SAMPLES, ("language_layer",))
    engine = state["engine"]
    keywords = engine["keywords"]
    expected_lang = Counter(k["language"] for k in keywords)
    expected_intent = Counter(
        k["enrichment"]["intent_vector"]["query_type"] for k in keywords
    )
    assert engine["corpus_summary"]["by_language"] == dict(expected_lang)
    assert engine["corpus_summary"]["by_intent"] == dict(expected_intent)
    for cluster in engine["clusters"]:
        members = cluster["members"]
        intents = [
            keywords[i]["enrichment"]["intent_vector"]["query_type"] for i in members
        ]
        intents = [x for x in intents if x]
        expected = Counter(intents).most_common(1)[0][0] if intents else "unknown"
        assert cluster["dominant_intent"] == expected


# --- the critical guard: a non-Italian corpus is untouched -----------------


def test_english_corpus_untouched(tmp_path: Path) -> None:
    state = _run(tmp_path, SAMPLES, ("language_layer",))
    slot = state["modules"]["language_layer"]
    assert slot["summary"]["detected_italian"] == 0
    assert slot["language_changes"] == []
    assert slot["intent_changes"] == []
    assert "it" not in state["engine"]["corpus_summary"]["by_language"]


def test_english_corpus_extraction_unchanged_by_layer(tmp_path: Path) -> None:
    """language_layer first then entity_web yields the same entities as entity_web alone."""
    with_layer = _run(tmp_path / "a", SAMPLES, ("language_layer", "entity_web"))
    without = _run(tmp_path / "b", SAMPLES, ("entity_web",))
    a = json.dumps(with_layer["modules"]["entity_web"], sort_keys=True)
    b = json.dumps(without["modules"]["entity_web"], sort_keys=True)
    assert a == b


# --- audit-slot contract ----------------------------------------------------


def test_audit_slot_contract(tmp_path: Path) -> None:
    state = _run(tmp_path, IT_SAMPLES, ("language_layer",))
    slot = state["modules"]["language_layer"]
    assert set(slot) >= {
        "language",
        "summary",
        "language_changes",
        "intent_changes",
        "rules",
    }
    assert slot["language"] == "it"
    assert set(slot["summary"]) >= {
        "keywords_total",
        "detected_italian",
        "language_reclassified",
        "intent_reclassified",
        "by_language",
        "by_intent",
    }
    for change in slot["intent_changes"]:
        assert change["cue"] is not None  # every intent change names its cue
        assert ":" in change["cue"]
    for change in slot["language_changes"]:
        assert change["to"] == "it"
        assert change["italian_score"] > change["engine_score"]


# --- contract and determinism ----------------------------------------------


def test_schema_bumped_and_module_first() -> None:
    assert run_state.SCHEMA_VERSION == "0.2.0"
    assert run_state.MODULE_KEYS[0] == "language_layer"
    assert "language_layer" in run_state.MODULE_KEYS


def test_determinism(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", IT_SAMPLES, ("language_layer",))
    b = _run(tmp_path / "b", IT_SAMPLES, ("language_layer",))
    sa = json.dumps(a["modules"]["language_layer"], sort_keys=True, ensure_ascii=False)
    sb = json.dumps(b["modules"]["language_layer"], sort_keys=True, ensure_ascii=False)
    assert sa == sb
