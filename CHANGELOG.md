# Changelog

All notable changes to this project are recorded here. The format follows
Keep a Changelog, and the project aims to follow semantic versioning.

## [Unreleased]

### Added (interactive dashboard)
- Optional interactive HTML dashboard for Output Forge, opt-in via
  `--forge-interactive` (on both `run` and `forge`). It renders the same dashboard
  with the charts mounted as interactive Plotly figures, inlining a pinned, vendored
  copy of the partial `plotly-basic` bundle (`vendor/plotly/plotly-basic-3.6.0.min.js`,
  MIT) with no content delivery network reference, so it stays offline. Each chart
  keeps the static SVG as a fallback when scripts do not run. The default HTML
  dashboard is unchanged and stays script-free inline SVG; the interactive format is
  skipped and recorded when the vendored bundle is absent. The variant is
  byte-deterministic. `NOTICE` lists the vendored bundle as a bundled component.

### Added (publish kit)
- Publish kit and license attributions. `NOTICE` now lists the optional
  third-party libraries the suite imports through degrading ports (python-pptx,
  python-docx, openpyxl under MIT; statsmodels under BSD-3-Clause), each with its
  role and source; none are bundled and the core stays standard-library only. A
  `PUBLISHING.md` checklist sets the ordered pre-publication gates (plugin
  validation, secrets and lint and Python security, dependency audit, tests, and
  the by-hand content checks). `requirements-optional.txt` names the optional
  libraries pinned to their current PyPI releases so pip-audit and Dependabot can
  resolve them (python-pptx 1.0.2, python-docx 1.2.0, openpyxl 3.1.5,
  statsmodels 0.14.6). A local `scripts/publish.ps1` runs every gate and pushes
  only when all pass; it stays inert until run.

### Changed (tooling)
- Tooling configuration so the publish gates are green and never touch the
  vendored engine: a `ruff.toml` that excludes `engine/` and `runs/`, and a
  top-level `exclude` in `.pre-commit-config.yaml` so no hook (ruff fixes,
  bandit, formatters) rewrites the read-only engine in CI. The Querymantic-authored
  Python (modules, core, scripts, evals) was run through `ruff format` and its
  lint findings cleared. Verified after: ruff check and ruff format clean,
  bandit clean at the configured level, 73 tests still green including the
  determinism proof.

### Added
- Sprint 8 (refinement), Italian as the fifth language: a new `language_layer`
  module that corrects Italian keywords the bundled four-language engine misreads.
  The engine votes Italian to English or French and flattens its intent to
  informational, because its function-word, diacritic, and intent tables hold no
  Italian. Language Layer runs first, before the analysis modules, so they read
  corrected values. It re-detects Italian with a conservative, strictly-greater
  vote over the engine's own (recovered from the engine's confidence), and
  overrides intent only on positive Italian lexical evidence (a marker or question
  pronoun), mirroring the engine's exact weights; when no Italian marker fires the
  engine intent is kept, since it may carry a signal from a provided intent column.
  It recomputes the corpus `by_language` and `by_intent` and each cluster's
  dominant intent in the produced state, and records every change with the cue that
  fired in its own `language_layer` audit slot. The vendored engine package is
  never edited. A corpus in one of the four supported languages is left untouched
  (verified zero changes on the English sample). The Italian lexicon lives as data
  in `data/gazetteer/it.json`; Italian entity-extraction stopwords were added to
  `querymantic/text/stopwords.py`. Ships an Italian sample at `assets/samples/it/`,
  the `references/language-layer.md` methodology, and the `language-layer` skill.

### Changed
- Run-state schema bumped from 0.1.0 to 0.2.0: a new `language_layer` module slot,
  listed first in `MODULE_KEYS` and the schema enums because it leads the run order.
  The committed determinism proof in `expected_outputs/` was regenerated with
  `language_layer` first; on the English sample it is a no-op, so only the new slot
  and the schema version change.

### Added (earlier this sprint)
- Sprint 8 (refinement), per-module skills: the six remaining per-module skills
  (`entity-web`, `fan-out-radar`, `demand-pulse`, `citation-grid`, `click-ceiling`,
  `live-wire`), each a lean SKILL.md with a trigger-only description, the CLI invocation,
  what it writes to `run.json`, and a one-level-deep link to its methodology reference.
  These join the `output-forge` skill and the `querymantic` orchestrator, so every module now
  has a discoverable skill.
- Sprint 8 (refinement), determinism proof: `expected_outputs/` now holds a committed,
  regenerable proof that the same input produces the same bytes. Because the vendored
  engine writes a temporary path and its own timestamp into `engine.run_metadata`, the
  full `run.json` is not byte-stable; the parts Querymantic owns are. The proof therefore
  stores a trimmed artifact (`sample_run.trimmed.json`: the `querymantic` metadata with a
  pinned timestamp plus every `modules` slot, with the `engine` block dropped) and the
  Output Forge HTML dashboard (`sample_dashboard.html`), byte for byte.
  `scripts/regenerate_expected_outputs.py` rewrites the files or, with `--check`,
  compares a fresh run against them and exits non-zero on drift. A pytest check makes
  the byte-equality a CI-enforced guarantee.
- Sprint 7, Output Forge: the `output_forge` module, an `ooxml` port, a white-label
  `brand.json`, and a `forge` CLI subcommand. It renders a finished `run.json` into
  deliverables from one shared, deterministic view: a self-contained HTML dashboard
  (standard library only, inline SVG charts, no external resource and no content
  delivery network, always produced), and a slide deck (`python-pptx`), a Word audit
  (`python-docx`), and an Excel workbook (`openpyxl`), each behind the `ooxml` port and
  skipped with a recorded reason when its backend is absent. The artifact files are
  written to an output directory; the run-state gains only the `output_forge` manifest,
  which lists each artifact with its byte size and SHA-256, the brand fingerprint, the
  backend availability, and any skipped format, and carries no absolute path. Output is
  byte-deterministic: every timestamp is pinned to the run timestamp (the OOXML
  core-properties dates) and the produced OOXML archive is normalized in the port
  (fixed ZIP-epoch member time, sorted member order), so two renders of the same input
  match byte for byte. The `forge` subcommand renders from an existing run.json without
  re-running the engine; adding `output_forge` to `--modules` renders inline in a
  pipeline run. The Office backends are optional, so a stdlib-only machine still
  produces the HTML dashboard and a complete manifest. Adds a methodology reference, a
  per-module skill, an eval scenario, and pytest coverage.
- Sprint 6, Live Wire (opt-in): the `live_wire` module, a capture file contract
  (`livewire_capture.json`), and paste templates with a guide. It is the only place
  observed data enters a run, and it never runs by default: it runs only when a
  capture file is passed with `--livewire`. It reads two optional blocks. The
  `search_console` block (query, clicks, impressions, ctr, position) overrides Click
  Ceiling's modeled current clicks with measured clicks and re-anchors the winnable
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
  features, and the Demand Pulse trend when present), renormalizing the weights when
  an upstream module is absent. An expected share is a within-portfolio,
  demand-weighted distribution, explicitly labeled expected and never a competitor
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
  sub-query count is a configurable cap, labeled a secondary estimate. Adds a
  starter reformulation gazetteer, a methodology reference, and pytest coverage.
- Sprint 1, Entity Web: an interchangeable entity extractor (default
  `tfidf_position`, an own stdlib scorer; clean-room YAKE left as a declared slot),
  stdlib text utilities (tokenizer, multilingual stop lists, candidate terms), and
  the `entity_web` module. It extracts entities from the keyword corpus, attaches
  demand and ownership, builds a co-occurrence graph, lists entity gaps, and scores
  topical authority per cluster, writing the `entity_web` slot in `run.json`. Adds a
  methodology reference and pytest coverage.
- Sprint 0 scaffold: plugin manifest, shared `querymantic` package (run-state
  contract, engine adapter, pipeline runner), the `run.json` schema, the CLI
  entry point, and stub skill, agent, and command files.
- Vendored `keyword-intelligence` engine under `engine/`, read-only and
  byte-identical to its source, with a sync script.
- Continuous integration and pre-commit configuration for secret scanning,
  linting, and dependency audit.

[Unreleased]: https://github.com/mario-montanari/querymantic/commits/main
