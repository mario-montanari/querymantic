---
name: citation-grid
description: "Use when estimating how citation-ready a cluster is for AI answer surfaces (AI Overviews, ChatGPT, Perplexity) and turning that into editorial actions, fully offline. Triggers: AI citation readiness, citability, AI Overviews, GEO readiness, answer-shaped content, structured signals, expected citation share, editorial checklist, generative engine optimization."
user-invokable: true
argument-hint: "[inputs] [output]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Citation Grid

## Overview

Citation Grid estimates per-cluster citation readiness for AI answer surfaces and turns
it into concrete editorial actions, fully offline with no content corpus. Each cluster
gets a six-component structural checklist and an expected readiness from 0 to 100, plus
an expected within-portfolio share. It runs offline and writes the `citation_grid` slot.

## When to use

- A cluster needs a read on how likely it is to be cited by an AI answer, and what to
  change to improve it.
- A plan needs editorial actions keyed off real structural signals, not vibes.

## Run it

```bash
python scripts/spektr_run.py run --inputs exports/ --output run.json \
  --modules entity_web fan_out_radar citation_grid
```

Run the prior modules first for the fullest signal; Citation Grid degrades to the
engine scopes alone when they are absent.

## What it writes

The `citation_grid` slot: per cluster, a `checklist` (six components, each with a
concrete action and its basis), `expected_readiness` (0 to 100), and `expected_share`.
Two of the six components need real passage text and stay checklist-only offline, so the
readiness blends only the signals that have a genuine offline value. The share is
labelled expected and within-portfolio, never a competitor or observed share (that is
the Live Wire path).

## Methodology

For the six components, the offline-value rule, the weighting and renormalisation, and
the honest-positioning note, see [references/citation-grid.md](../../references/citation-grid.md).
