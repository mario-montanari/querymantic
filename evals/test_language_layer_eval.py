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

The corpus prior closed most of that gap. The assertions below are an exact
snapshot of the corrected behavior; the original failing state is pinned in
this file's git history (the eval commit precedes the fix commit). What
remains undetected is a declared trade-off: Italian keywords carrying
loanwords with a foreign shape, and keywords where the engine holds a
contrary vote, which the prior never overrides. Every non-Italian baseline
must stay exactly where it stands.
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


def _run_state(tmp: Path, keywords: list[str]) -> dict:
    """Run the real rail (vendored engine + language_layer) on the given corpus."""
    source = tmp / "corpus.csv"
    with source.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["keyword"])
        for keyword in keywords:
            writer.writerow([keyword])
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [source],
        tmp / "run.json",
        modules_to_run=("language_layer",),
        generated_at=FIXED_TIMESTAMP,
    )


def _predict(tmp: Path, keywords: list[str]) -> dict[str, str]:
    """Map each keyword to the language the suite finally assigns it."""
    state = _run_state(tmp, keywords)
    return {k["keyword"]: k["language"] for k in state["engine"]["keywords"]}


def test_fixture_is_well_formed() -> None:
    fixture = _load_fixture()
    mono = fixture["monolingual_italian"]
    multi = fixture["multilingual"]
    foreign = fixture["foreign_in_italian_corpus"]
    assert len(mono) == 80
    assert len(multi) == 60
    assert len(foreign) == 10
    keywords = (
        [e["keyword"] for e in mono]
        + [e["keyword"] for e in multi]
        + [e["keyword"] for e in foreign]
    )
    assert len(keywords) == len(set(keywords)), "fixture keywords must be unique"
    assert {e["family"] for e in mono} == VALID_FAMILIES
    assert {e["language"] for e in multi} == VALID_LANGUAGES
    assert Counter(e["language"] for e in multi) == Counter(
        {"it": 12, "en": 12, "fr": 12, "de": 12, "es": 12}
    )
    assert {e["language"] for e in foreign} == {"en"}


def test_monolingual_italian_recall_baseline(tmp_path: Path) -> None:
    """A purely Italian corpus, profiled like a real Italian export.

    Snapshot with the corpus prior: 71 of 80 keywords detected as Italian
    (recall 0.8875, up from 18 of 80 on the lexical vote alone; see this
    file's history). The nine misses are the declared trade-off: four
    Italian keywords carrying foreign-shaped loanwords (no morphology, no
    Italian shape), and five where the engine holds a contrary vote the
    prior never overrides.
    """
    mono = _load_fixture()["monolingual_italian"]
    state = _run_state(tmp_path, [e["keyword"] for e in mono])
    pred = {k["keyword"]: k["language"] for k in state["engine"]["keywords"]}
    assert all(e["keyword"] in pred for e in mono), "engine must echo every keyword"

    by_language = Counter(pred[e["keyword"]] for e in mono)
    assert by_language == Counter({"it": 71, "en": 5, "es": 3, "fr": 1})

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
            "bare_content": 44,
            "shared_stopword_trap": 5,
            "function_words": 14,
            "accent_trap": 4,
            "accent_signal": 4,
        }
    )

    recall = by_language["it"] / len(mono)
    assert recall == 71 / 80  # 0.8875, up from 18/80 before the corpus prior

    # The prior is on, its arithmetic is pinned, and every decision is traced.
    slot = state["modules"]["language_layer"]
    assert slot["prior"] == {
        "enabled": True,
        "share": 0.9062,
        "evidence": {"italian": 29, "engine": 21, "bearing": 32},
        "tie_breaks": 9,
        "morphology": 27,
        "italian_shape": 17,
    }
    assert slot["summary"]["reclassified_by_prior"] == 53
    reasons = Counter(c["reason"] for c in slot["language_changes"])
    assert reasons["lexical_vote"] == 18
    assert sum(n for r, n in reasons.items() if r.startswith("corpus_prior:")) == 53


def test_multilingual_corpus_per_language_baseline(tmp_path: Path) -> None:
    """A mixed five-language corpus: per-language confusion snapshot.

    The non-Italian rows are the regression guard for any future detection
    change: their predictions must stay exactly as recorded here. The two
    German keywords read as French (umlauts shared with the engine's French
    character set) and the one Spanish keyword read as French (stop words
    shared with French) are pre-existing engine behavior, documented as is.
    The corpus prior must stay OFF here: the Italian evidence share sits far
    below the threshold, so this corpus is untouched by the second pass and
    the confusion matrix is identical with and without the prior.
    """
    multi = _load_fixture()["multilingual"]
    state = _run_state(tmp_path, [e["keyword"] for e in multi])
    pred = {k["keyword"]: k["language"] for k in state["engine"]["keywords"]}
    assert all(e["keyword"] in pred for e in multi), "engine must echo every keyword"

    prior = state["modules"]["language_layer"]["prior"]
    assert prior["enabled"] is False
    assert prior["share"] == 0.32  # far below the 0.5 threshold
    assert prior["tie_breaks"] == 0
    assert prior["morphology"] == 0
    assert prior["italian_shape"] == 0

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


def test_foreign_zero_signal_keywords_survive_an_italian_corpus(
    tmp_path: Path,
) -> None:
    """The danger case for any corpus-level correction.

    A real Italian site legitimately holds zero-signal brand and English
    keywords (product names, tool names, bare English queries). Inside an
    Italian-majority corpus those are exactly the keywords a corpus prior
    would pull in by mistake: they must never be claimed as Italian, while
    the Italian majority around them is recovered far beyond the
    lexical-evidence baseline of 18 detections in 80.
    """
    fixture = _load_fixture()
    mono = fixture["monolingual_italian"]
    foreign = fixture["foreign_in_italian_corpus"]
    pred = _predict(
        tmp_path,
        [e["keyword"] for e in mono] + [e["keyword"] for e in foreign],
    )

    claimed = [e["keyword"] for e in foreign if pred[e["keyword"]] == "it"]
    assert claimed == [], "no foreign keyword may inherit the Italian prior"

    recall = sum(1 for e in mono if pred[e["keyword"]] == "it") / len(mono)
    assert recall >= 0.75, f"Italian recall {recall:.4f} is below the 0.75 bar"
