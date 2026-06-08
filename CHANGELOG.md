# Changelog

All notable changes to this project are recorded here. The format follows
Keep a Changelog, and the project aims to follow semantic versioning.

## [Unreleased]

### Added
- Sprint 6, Live Wire (opt-in): the `live_wire` module, a capture file contract
  (`livewire_capture.json`), and paste templates with a guide. It is the only place
  observed data enters a run, and it never runs by default: it runs only when a
  capture file is passed with `--livewire`. It reads two optional blocks. The
  `search_console` block (query, clicks, impressions, ctr, position) overrides Click
  Ceiling's modelled current clicks with measured clicks and re-anchors the winnable
  band to the ceiling minus the measured current. The `ai_citations` block (which
  domains an AI surface cited per query) measures the client's demand-weighted
  citation share and the competitor split, which Citation Grid can only approximate
  offline as a within-portfolio expected share. The module is a non-destructive
  overlay: it writes its own slot, pairing each observed value with the expected one
  it corresponds to, and leaves the offline slots byte-identical, so expected and
  observed are never conflated. The CTR parser accepts both the export percent
  string and the API fraction; queries that do not match the corpus are listed under
  `unmatched_queries` so a capture's coverage stays visible. Adds a methodology
  reference, an eval scenario, and pytest coverage.
- Sprint 5, Click Ceiling: the `click_ceiling` module and a dated CTR-by-position
  table (`data/ctr_table_2026Q2.json`). It estimates the band of winnable monthly
  organic clicks per cluster from the table and the SERP features present, reporting
  a band and never a single number. The table carries per-cell provenance: confirmed
  anchor positions from a published CTR study, formula-filled interpolated and
  extrapolated cells, and derived SERP-feature factors; a rank on a non-confirmed
  cell widens the band. Per keyword the estimate is volume times CTR(rank, features),
  applying the single strongest SERP suppression rather than a product, and on
  AI-Overview queries the measured organic-CTR suppression, recovered on the
  optimistic endpoint by the Citation Grid readiness. Demand Pulse trend, Entity Web
  topical authority, and Fan-Out coverage sharpen the band when present, each
  recorded per cluster as an auditable adjuster; the module degrades to the engine
  metrics alone. A run-level summary totals the winnable band and splits it by
  intent. Adds a methodology reference, an eval scenario, and pytest coverage.
- Sprint 4, Citation Grid: the `citation_grid` module. It estimates per-cluster
  citation readiness by AI answer surfaces and turns it into editorial actions,
  fully offline with no content corpus. Six citability components (Extractability,
  EntityCoverage, StructuredSignals, InformationGain, FreshnessProxy, SourceCues)
  drive a structural-signal checklist per cluster; two of them need real passage
  text and are checklist-only offline. An expected readiness (0 to 100) blends only
  the signals with an offline value (engine AIO and GEO eligibility, Fan-Out
  coverage, Entity Web topical authority, answer-shape density, SERP structure
  features, and the Demand Pulse trend when present), renormalising the weights when
  an upstream module is absent. An expected share is a within-portfolio,
  demand-weighted distribution, explicitly labelled expected and never a competitor
  or observed share (which belong to the Live Wire path). Adds a methodology
  reference, an eval scenario, and pytest coverage.
- Sprint 3, Demand Pulse: a stdlib statistics port (Mann-Kendall, Theil-Sen) with
  an optional STL seasonal-strength path behind statsmodels that degrades when the
  package is absent, and the `demand_pulse` module. It classifies each cluster as
  rising, declining, seasonal, flat, or unknown from a monthly volume series, with
  the trend statistics, a momentum ratio, and a marker-derived seasonal flag kept
  separate from the series-based state. The canonical state carries volume only, so
  the series is an optional second input (a wide `keyword` plus `YYYY-MM` CSV, wired
  through a new `--series` option and a generic per-module argument channel in the
  pipeline); without it every cluster is unknown. Adds a sample series, a
  methodology reference, an eval scenario, and pytest coverage.
- Sprint 2, Fan-Out Radar: a stdlib BM25 index and the `fan_out_radar` module. It
  generates sub-queries across seven archetypes per cluster, scores expected
  coverage against the cluster keywords (offline), reports Cover@tau and missing
  archetypes, and flags gatekeeper queries (central sub-queries with no originating
  volume). It uses the Entity Web graph when present and degrades without it. The
  sub-query count is a configurable cap, labelled a secondary estimate. Adds a
  starter reformulation gazetteer, a methodology reference, and pytest coverage.
- Sprint 1, Entity Web: an interchangeable entity extractor (default
  `tfidf_position`, an own stdlib scorer; clean-room YAKE left as a declared slot),
  stdlib text utilities (tokenizer, multilingual stop lists, candidate terms), and
  the `entity_web` module. It extracts entities from the keyword corpus, attaches
  demand and ownership, builds a co-occurrence graph, lists entity gaps, and scores
  topical authority per cluster, writing the `entity_web` slot in `run.json`. Adds a
  methodology reference and pytest coverage.
- Sprint 0 scaffold: plugin manifest, shared `spektr_core` package (run-state
  contract, engine adapter, pipeline runner), the `run.json` schema, the CLI
  entry point, and stub skill, agent, and command files.
- Vendored `keyword-intelligence` engine under `engine/`, read-only and
  byte-identical to its source, with a sync script.
- Continuous integration and pre-commit configuration for secret scanning,
  linting, and dependency audit.

[Unreleased]: https://example.invalid/spektr/compare
