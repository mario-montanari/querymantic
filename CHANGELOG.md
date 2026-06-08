# Changelog

All notable changes to this project are recorded here. The format follows
Keep a Changelog, and the project aims to follow semantic versioning.

## [Unreleased]

### Added
- Sprint 0 scaffold: plugin manifest, shared `spektr_core` package (run-state
  contract, engine adapter, pipeline runner), the `run.json` schema, the CLI
  entry point, and stub skill, agent, and command files.
- Vendored `keyword-intelligence` engine under `engine/`, read-only and
  byte-identical to its source, with a sync script.
- Continuous integration and pre-commit configuration for secret scanning,
  linting, and dependency audit.

[Unreleased]: https://example.invalid/spektr/compare
