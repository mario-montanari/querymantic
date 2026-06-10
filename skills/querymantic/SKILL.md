---
name: querymantic
description: "Use when analyzing keyword exports (Semrush, Ahrefs, Google Search Console, Moz, Ubersuggest, or generic CSV) offline for SEO, GEO, and AI-search strategy, or when a user drops a keyword CSV and wants a structured demand analysis rather than a flat list. Triggers: keyword analysis, demand intelligence, search intent, topical authority, entity coverage, query fan-out, AI citation readiness, winnable clicks, content gap."
user-invokable: true
argument-hint: "[inputs] [output]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Querymantic: offline keyword and demand intelligence

## Overview

Querymantic turns raw keyword exports into one structured, machine-readable state and a
set of analyses, without any external API call. It vendors the keyword-intelligence
engine for the base analysis (intent, clusters, scopes, gaps) and adds modules on
top for entity coverage, query fan-out, demand trend, AI-citation readiness, and
winnable-click bands.

The canonical output is `run.json`: the single source of truth for a run. The
engine analysis sits under its `engine` key; each module fills its own slot under
`modules`. Every figure traces back to the input files through `querymantic.input_hash`.

## Running an analysis

Run the pipeline on one or more CSV/TSV files, or a directory of them:

```bash
python scripts/querymantic_run.py run --inputs path/to/exports/ --output run.json
```

Useful options:

- `--client-domain example.com` enables gap analysis against the client.
- `--brand-list "brand,brand name"` splits branded from non-branded demand.
- `--label "Q2 audit"` labels the run.
- `--modules entity_web fan_out_radar` runs named modules in order.

The command prints a short summary and writes `run.json`. Run
`python scripts/querymantic_run.py run --help` for the full option list.

## Validating a run

```bash
python scripts/querymantic_run.py validate run.json
```

This checks the run against the run-state contract and reports any structural
problem. The contract is documented at `schemas/run.schema.json`.

## What run.json contains

- `querymantic`: schema and plugin versions, the input hash, the input paths, and the
  list of modules that have run.
- `engine`: the vendored engine analysis. Stable fields include `corpus_summary`,
  per-keyword `metrics` and `scores`, `clusters`, and `gaps`.
- `modules`: one slot per module, filled as each module runs.

## Modules

Modules are added in this order, each a pure step that reads `run.json` and writes
its own slot: Entity Web, Fan-Out Radar, Demand Pulse, Citation Grid, Click Ceiling,
Live Wire, Output Forge. The registry is in `modules/`; the methodology for each is
in `references/` as it lands.

## Reference

- Run-state contract: `schemas/run.schema.json` and `querymantic/run_state.py`.
- Engine methodology and the analysis.json fields: `engine/keyword-intelligence/`.
