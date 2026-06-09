---
name: fan-out-radar
description: "Use when checking how well a cluster covers the sub-queries a search or AI engine would fan out into, or finding gatekeeper sub-queries and missing query archetypes. Triggers: query fan-out, sub-queries, query expansion, coverage, Cover@tau, gatekeeper query, missing archetypes, BM25 coverage, related questions coverage."
user-invokable: true
argument-hint: "[inputs] [output]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Fan-Out Radar

## Overview

Fan-Out Radar generates sub-queries across seven archetypes per cluster, scores how
well the cluster's keywords cover them with a stdlib BM25 index, and flags the
archetypes that are missing and the gatekeeper sub-queries (central sub-queries with no
originating volume). It runs offline and writes the `fan_out_radar` slot.

## When to use

- A cluster needs a coverage read against the way engines expand a query, not just the
  head term.
- A content brief needs the missing angles (comparative, implicit, and the rest) and
  the gatekeeper queries to prioritise.

## Run it

```bash
python scripts/querymantic_run.py run --inputs exports/ --output run.json --modules entity_web fan_out_radar
```

Run `entity_web` first: Fan-Out Radar uses its graph when present and degrades cleanly
without it.

## What it writes

The `fan_out_radar` slot: per cluster, the generated `sub_queries` with their archetype
and BM25 score, a `coverage` block (`cover_at_tau`, `covered`, `total`, the `tau`
threshold), the `missing_archetypes`, and the `gatekeepers`. The sub-query count per
cluster is a configurable cap, labelled a secondary estimate, not a search-engine fact.

## Methodology

For the seven archetypes, the BM25 parameters, the Cover@tau definition, the
in-document meaning of "gatekeeper", and the parameters, see
[references/fan-out-radar.md](../../references/fan-out-radar.md).
