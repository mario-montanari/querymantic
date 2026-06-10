# Language Layer

## Contents

- What it produces
- Why the engine needs the correction
- Language detection: a conservative Italian vote
- Intent: an evidence-gated Italian override
- The audit slot
- What it does not touch
- The lexical resource
- Limitations and escape hatches
- Sources

## What it produces

Language Layer corrects Italian keywords in the run-state and writes
`modules.language_layer`: a per-keyword audit of every language re-detection and
every intent reclassification, with the cue that fired, plus the recomputed
corpus language and intent counts. It runs first, before the analysis modules, so
they read the corrected `language` and `query_type` rather than the engine's
misclassification. It is a pure step and edits only the produced state.

## Why the engine needs the correction

The bundled engine supports four languages: English, French, German, Spanish. Two
of its stages are keyed by that set, so Italian input is misread on two axes.

- Language. The engine votes the language from diacritic characters and from
  function-word overlap across the four supported languages. Italian function
  words are in none of those tables, so an Italian keyword falls to English (with
  the engine's no-signal confidence) or to French.
- Intent. The engine reads intent markers and question pronouns keyed by language
  with an English fallback, so Italian cues such as `prezzo`, `migliori`,
  `recensioni`, or `come` are unseen and the intent collapses to informational.

The one case the engine already handles is a provided intent column: it folds a
declared intent label into the vector as a weak signal. So an Italian export that
carries an Intent column gets a weakly correct intent even without this module;
an export without one does not. Language Layer closes both gaps offline.

## Language detection: a conservative Italian vote

Detection mirrors the engine's own vote structure, extended with an Italian
lexical resource. For each keyword it counts Italian cue tokens (function words
and the distinctly Italian intent words from the gazetteer, plus the question
pronouns) and adds a diacritic vote when an Italian accented character is present,
matching the weight the engine gives its own diacritic cue.

The override rule is conservative and strictly greater. Language Layer replaces
the engine's language with Italian only when the Italian vote is strictly larger
than the engine's winning vote, reconstructed from the confidence the engine
recorded. A tie keeps the engine's choice. A declared language (the engine's
full-confidence case) is never overridden. The effect is that a corpus in one of
the four supported languages is left untouched (the Italian vote does not exceed a
real English, French, German, or Spanish vote), while genuinely Italian phrases
that carry at least one Italian function word or intent word are corrected. The
new confidence is set on the same scale the engine uses.

## Intent: an evidence-gated Italian override

For a keyword detected as Italian, intent is recomputed from the Italian markers,
mirroring the engine's weights exactly: a question pronoun in first position adds
to informational, a transactional marker (`prezzo`, `comprare`, `offerta`, and
the rest) adds to transactional, a commercial marker (`migliori`, `recensioni`,
`confronto`) adds to commercial investigation, a navigational marker (`accedi`,
`accesso`, `sito`) adds to navigational, and an informational marker adds to
informational. The same SERP-feature nudges the engine applies are applied here.
A question word that is also an informational marker contributes on both counts,
exactly as in the engine, which is why a query such as `dove comprare ...` reads
informational rather than transactional: the question word dominates, the same way
the engine treats `where to buy ...` in English.

The override is gated on positive Italian evidence. It replaces the engine's
intent only when an Italian lexical marker or question pronoun actually fires.
When none fires, the engine's intent is kept, because it may carry the signal from
a provided intent column, and inventing an intent from silence would be a guess.
A keyword that is detected as Italian but matches no intent marker therefore keeps
its engine intent and is recorded with a language change only. When the intent is
overridden, the funnel stage is recomputed from the new intent with the engine's
own mapping, so the vector stays internally consistent.

## The audit slot

Nothing is silent. `modules.language_layer` lists, per affected keyword, the
language change (from, to, the Italian and engine vote scores, the new confidence)
and the intent change (from, to, the confidence before and after, and the exact
cue that fired, such as `commercial:recensioni` or `pronoun:come`). The summary
carries the totals and the recomputed `by_language` and `by_intent`. A reader can
reconstruct every decision from the slot.

## What it does not touch

Language Layer corrects the `language` and intent `query_type` fields, their
confidences, and the aggregates of them (the corpus `by_language` and `by_intent`
and each cluster's dominant intent). It does not recompute the engine's per-keyword
scopes, such as quick-win or AIO eligibility labels, which the engine computed
under its original classification; recomputing them would mean reimplementing the
engine, which the suite deliberately keeps read-only. The `modality` and
`temporal` axes of the intent vector are also left as the engine set them: they
key off phrase shape and seasonal markers outside this module's remit. The
vendored engine package is never edited; only the produced run-state is.

## The lexical resource

The Italian cues, question pronouns, and intent markers live in
`data/gazetteer/it.json`, not in code, so the lists are auditable and a further
language is a new file rather than a code change. The module is language-agnostic
and loads the resource at run time. The Italian function words used for entity
extraction live separately in `querymantic/text/stopwords.py`, alongside the four
existing languages.

## Limitations and escape hatches

Detection rests on Italian function words and intent words. A telegraphic query
made only of content words and loanwords, with no Italian function word or marker
(for example a bare `scarpe running uomo`), carries no Italian signal the vote can
read and is left as the engine classified it. This is the conservative choice: a
false negative is safer than flipping a English, French, German, or Spanish
keyword to Italian. Two escape hatches resolve it when the data allows. A language
column is honored by the engine before this module runs, so a declared `it` sets
the language directly. An intent column is folded by the engine into the vector,
so a declared intent survives even when no Italian marker fires. The lexicon is
extensible: a domain with recurring content terms can add them to the gazetteer.

## Sources

- A. Broder, "A taxonomy of web search", ACM SIGIR Forum 36(2), 2002, for the
  informational, navigational, and transactional intent classes; the commercial
  investigation class follows common industry practice on top of that taxonomy.
- W. B. Cavnar and J. M. Trenkle, "N-Gram-Based Text Categorization", 1994, for
  language identification from frequent short tokens, the principle the
  function-word vote rests on.
- Google Search Quality Rater Guidelines, for the understanding of query intent
  that the marker classification operationalises.
