---
name: entity-web
description: "Use when analysing which entities a keyword corpus owns versus only demands, mapping topical authority per cluster, or finding entity gaps to close. Triggers: entity coverage, entity gap, co-occurrence, topical authority, owned vs demand entities, named entities from keywords, entity graph, semantic coverage."
user-invokable: true
argument-hint: "[inputs] [output]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Entity Web

## Overview

Entity Web extracts the entities a keyword corpus is built around, attaches demand
and ownership to each, builds a co-occurrence graph, lists the entity gaps, and scores
topical authority per cluster. It runs offline on the engine analysis already in
`run.json` and writes the `entity_web` slot.

## When to use

- A corpus needs an entity-level view, not just a keyword list: which entities the site
  already ranks for (owned) against those it only has demand for.
- A content plan needs the gap entities to close, ranked by demand.
- A cluster needs a topical-authority read for prioritisation.

## Run it

```bash
python scripts/spektr_run.py run --inputs exports/ --output run.json --modules entity_web
```

Add `--client-domain example.com` so ownership reflects the client. Entity Web is the
first analysis module, so run it before Fan-Out Radar and Citation Grid, which read its
graph when present.

## What it writes

The `entity_web` slot: `entities` (each with demand volume, ownership, degree, and the
clusters it appears in), a co-occurrence `graph` (nodes and edges), `entity_gaps`
(demand entities not yet owned, with a suggested cluster), and `topical_authority` per
cluster. The extractor is interchangeable; the default is `tfidf_position`.

## Methodology

For the extractor interface, the ownership and authority definitions, and the
limitations (ownership is corpus-bounded), see
[references/entity-web.md](../../references/entity-web.md).
