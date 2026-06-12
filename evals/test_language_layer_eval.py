#!/usr/bin/env python3
"""Language detection eval: per-language recall and precision baselines.

The sprint 8 tests pin the language_layer mechanism on small samples built
around Italian function words. This eval measures the detection quality the
suite actually delivers on realistic corpora, where most keywords are short
content phrases with no function words and almost no accents. On that profile
the engine finds no signal (English at confidence 0.4), the Italian vote
scores zero, and the strictly-greater rule cannot win ties against Spanish,
French, or the French character set, so Italian recall collapses.

The corpora live in fixtures/language_eval_corpora.json. Every keyword is
synthetic and invented for the fixture; real exports are only ever measured
locally and never enter the repository in any form.

The assertions below are an exact snapshot of the CURRENT behavior, so this
eval documents the state rather than failing it. The fix round is expected to
raise the Italian numbers and is required to keep every non-Italian baseline
exactly where it stands.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from querymantic import pipeline  # noqa: E402

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "language_eval_corpora.json"
)
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"

VALID_LANGUAGES = {"it", "en", "fr", "de", "es"}
VALID_FAMILIES = {
    "bare_content",
    "shared_stopword_trap",
    "accent_trap",
    "accent_signal",
    "function_words",
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _predict(tmp: Path, keywords: list[str]) -> dict[str, str]:
    """Run the real rail (vendored engine + language_layer) and map keyword to language."""
    source = tmp / "corpus.csv"
    with source.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["keyword"])
        for keyword in keywords:
            writer.writerow([keyword])
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [source],
        tmp / "run.json",
        modules_to_run=("language_layer",),
        generated_at=FIXED_TIMESTAMP,
    )
    return {k["keyword"]: k["language"] for k in state["engine"]["keywords"]}


def test_fixture_is_well_formed() -> None:
    fixture = _load_fixture()
    mono = fixture["monolingual_italian"]
    multi = fixture["multilingual"]
    assert len(mono) == 80
    assert len(multi) == 60
    keywords = [e["keyword"] for e in mono] + [e["keyword"] for e in multi]
    assert len(keywords) == len(set(keywords)), "fixture keywords must be unique"
    assert {e["family"] for e in mono} == VALID_FAMILIES
    assert {e["language"] for e in multi} == VALID_LANGUAGES
    assert Counter(e["language"] for e in multi) == Counter(
        {"it": 12, "en": 12, "fr": 12, "de": 12, "es": 12}
    )


def test_monolingual_italian_recall_baseline(tmp_path: Path) -> None:
    """A purely Italian corpus, profiled like a real Italian export.

    Baseline snapshot: 18 of 80 keywords detected as Italian (recall 0.225).
    Detection only succeeds where the gazetteer has positive evidence
    (function words or an Italian-only accent); every content-only keyword
    and every shared-signal tie is lost.
    """
    mono = _load_fixture()["monolingual_italian"]
    pred = _predict(tmp_path, [e["keyword"] for e in mono])
    assert all(e["keyword"] in pred for e in mono), "engine must echo every keyword"

    by_language = Counter(pred[e["keyword"]] for e in mono)
    assert by_language == Counter({"en": 50, "it": 18, "es": 6, "fr": 6})

    hits_by_family: Counter = Counter()
    totals_by_family: Counter = Counter()
    for entry in mono:
        totals_by_family[entry["family"]] += 1
        if pred[entry["keyword"]] == "it":
            hits_by_family[entry["family"]] += 1
    assert totals_by_family == Counter(
        {
            "bare_content": 48,
            "shared_stopword_trap": 10,
            "function_words": 14,
            "accent_trap": 4,
            "accent_signal": 4,
        }
    )
    assert hits_by_family == Counter(
        {
            "function_words": 14,
            "accent_signal": 4,
            "bare_content": 0,
            "shared_stopword_trap": 0,
            "accent_trap": 0,
        }
    )

    recall = by_language["it"] / len(mono)
    assert recall == 18 / 80  # 0.225, the figure the fix round must beat


def test_multilingual_corpus_per_language_baseline(tmp_path: Path) -> None:
    """A mixed five-language corpus: per-language confusion snapshot.

    The non-Italian rows are the regression guard for any future detection
    change: their predictions must stay exactly as recorded here. The two
    German keywords read as French (umlauts shared with the engine's French
    character set) and the one Spanish keyword read as French (stop words
    shared with French) are pre-existing engine behavior, documented as is.
    """
    multi = _load_fixture()["multilingual"]
    pred = _predict(tmp_path, [e["keyword"] for e in multi])
    assert all(e["keyword"] in pred for e in multi), "engine must echo every keyword"

    confusion: dict[str, Counter] = defaultdict(Counter)
    for entry in multi:
        confusion[entry["language"]][pred[entry["keyword"]]] += 1

    assert confusion["it"] == Counter({"en": 6, "it": 3, "es": 2, "fr": 1})
    assert confusion["en"] == Counter({"en": 12})
    assert confusion["fr"] == Counter({"fr": 12})
    assert confusion["de"] == Counter({"de": 10, "fr": 2})
    assert confusion["es"] == Counter({"es": 11, "fr": 1})

    # Italian precision: nothing that is not Italian may be claimed as Italian.
    predicted_it = [e for e in multi if pred[e["keyword"]] == "it"]
    assert predicted_it, "the baseline detects at least some Italian"
    assert all(e["language"] == "it" for e in predicted_it)
