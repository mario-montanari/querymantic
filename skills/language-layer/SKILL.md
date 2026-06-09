---
name: language-layer
description: "Use when an Italian keyword export is misread by the four-language engine, to detect Italian and reclassify Italian intent before the other modules run. Triggers: Italian keywords, Italian SEO, italiano, fifth language, Italian intent, language detection, Italian export, multilingual corpus, prezzo, migliori, recensioni, come, Italian search intent."
user-invokable: true
argument-hint: "[inputs] [output] (list language_layer first in --modules)"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Language Layer

## Overview

Language Layer corrects Italian keywords that the bundled four-language engine misreads:
it votes them to English or French and flattens their intent to informational. The layer
re-detects Italian and reclassifies Italian intent, offline, then records every change in
an audit slot. It runs first so the analysis modules read corrected values, and writes the
`language_layer` slot.

## When to use

- An Italian or mixed export comes back with most keywords tagged English or French and
  almost everything marked informational.
- Italian intent words (`prezzo`, `migliori`, `recensioni`, `come`) should drive intent
  rather than being unseen.

## Run it

List `language_layer` first, before the analysis modules, so they read corrected values.

```bash
python scripts/spektr_run.py run --inputs exports/ --output run.json \
  --modules language_layer entity_web fan_out_radar citation_grid click_ceiling
```

It is conservative: a keyword is re-detected as Italian only when its Italian vote beats
the engine's, and the intent is overridden only when an Italian marker fires, so a corpus
in English, French, German, or Spanish is left untouched. A telegraphic Italian phrase
with no Italian function word or marker stays as the engine classified it; a language or
intent column resolves that case. A sample Italian export is at `assets/samples/it/`.

## What it writes

The `language_layer` slot: a `summary` with the totals and the recomputed `by_language`
and `by_intent`, a `language_changes` list (from, to, the Italian and engine vote scores,
the new confidence), and an `intent_changes` list (from, to, the confidences, and the cue
that fired, such as `commercial:recensioni`). It also recomputes the corpus counts and
each cluster's dominant intent in the produced state. The Italian lexicon lives in
`data/gazetteer/it.json`.

## Methodology

For the detection vote and the strictly-greater rule, the evidence-gated intent override,
what the layer does not touch, and the limitations and escape hatches, see
[references/language-layer.md](../../references/language-layer.md).
