# Changelog

All notable changes to this project are recorded here. The format follows
Keep a Changelog, and the project aims to follow semantic versioning.

## [Unreleased]

### Added
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
