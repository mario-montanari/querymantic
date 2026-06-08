# Architecture

Spektr is a Claude Code and Claude Cowork plugin that turns keyword exports into a
single structured state and a set of offline analyses. It vendors the
keyword-intelligence engine for the base analysis and adds modules on top. Nothing
calls an external API: every figure is computed from the files you provide.

## Two layers

The published plugin lives in this directory and has its own git history. The
vendored engine sits inside it, read-only.

```
spektr/
├── .claude-plugin/plugin.json   # plugin manifest
├── README.md
├── LICENSE                      # MIT
├── NOTICE                       # bundled-component attributions
├── CHANGELOG.md
├── ARCHITECTURE.md              # this document
├── engine/
│   ├── keyword-intelligence/    # vendored, read-only, byte-identical to source
│   └── sync_engine.py           # refresh and verify the vendored copy
├── spektr_core/                 # shared package, stdlib-first
│   ├── run_state.py             # run.json contract: hash, build, load, save, validate
│   ├── engine_adapter.py        # runs the vendored engine, reads analysis.json
│   ├── pipeline.py              # ingest -> engine -> modules -> save
│   ├── text/                    # tokenizer, BM25, stopwords (stdlib)
│   └── ports/                   # thin adapters to optional libraries, degrade if absent
├── modules/                     # the modules: pure functions run_state -> run_state'
├── skills/spektr/               # orchestrator skill (drop a CSV, get the analysis)
├── agents/spektr-orchestrator.md
├── commands/                    # spektr-analyze, spektr-audit
├── references/                  # methodology; cites primary sources only
├── schemas/run.schema.json      # the run.json contract
├── data/                        # dated lookup tables and gazetteers
├── forge/templates/             # output templates and white-label config
├── evals/                       # YAML scenarios plus pytest on calculations
├── assets/samples/              # sample CSVs, multi-tool, multi-language
└── expected_outputs/            # regenerable sample runs (determinism proof)
```

## Design principles

- **Engine untouched.** The vendored engine is read-only and byte-identical to its
  source, refreshed only by the sync script on version bumps. It stays stdlib-only.
- **Single canonical state.** `run.json` is the one shared state, in continuity with
  the engine's `analysis.json` contract. Each module is a pure function
  `run_state -> run_state'` that fills its own slot.
- **Tiered dependency budget.** The core and the vendored engine run on the standard
  library. Optional libraries sit behind ports that degrade rather than break, so a
  missing optional package never hard-fails a run.
- **Expected versus observed.** Any score that depends on signals unavailable offline
  has an `expected` (offline) variant and an `observed` variant from live capture.
  They are never mixed.
- **Deterministic output.** The same input yields the same analytical content. The
  input hash records which files produced a run, and output timestamps can be pinned
  for byte-reproducible artifacts.
- **Honest positioning.** AI-citation work is structural rigor (answer-shaped passages,
  statistics, citations, structured data), not a hidden channel. Every load-bearing
  figure carries its provenance; fragile estimates are parameters, not facts.

## The run-state contract

`run.json` has three parts:

- `spektr`: the schema and plugin versions, a deterministic SHA-256 over the input
  files, the input paths, and the list of modules that have run.
- `engine`: the vendored engine analysis. Stable fields include `corpus_summary`,
  per-keyword `metrics` and `scores`, `clusters`, and `gaps`.
- `modules`: one slot per module, `null` until that module fills it.

The schema is documented in `schemas/run.schema.json`. The executable check the
pipeline relies on is the structural validator in `spektr_core/run_state.py`, which
uses the standard library only, so the suite needs no schema-validation dependency.

## Modules

Each module reads `run.json`, computes its analysis from the engine output and the
input metrics, and writes its own slot.

1. **Entity Web** extracts entities and a co-occurrence graph, separates owned from
   demand entities, and reports coverage gaps and topical authority per cluster.
2. **Fan-Out Radar** models how a query expands into sub-queries and measures how
   well a cluster covers that expansion.
3. **Demand Pulse** classifies each cluster's demand trend (rising, declining,
   seasonal, flat) with a trend test and optional seasonality decomposition.
4. **Citation Grid** scores per-passage AI-citation readiness from deterministic
   components and reports an expected versus observed share.
5. **Click Ceiling** estimates a winnable-clicks band per cluster from a dated
   click-through table and SERP-feature adjustments. It reports a band, never a
   single number.
6. **Live Wire** is opt-in: it reads a manual capture file and replaces `expected`
   values with `observed` ones.
7. **Output Forge** renders one `run.json` into a branded deck, a written audit, a
   spreadsheet dashboard, and a self-contained HTML dashboard.
