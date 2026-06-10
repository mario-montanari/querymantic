# Querymantic

Offline keyword and demand intelligence for Claude Code and Claude Cowork.

You drop in your keyword exports. Querymantic reads them, runs a deterministic
analysis, and writes one structured file you can build on. It makes no external
calls and loads nothing at runtime: no API, no account, no telemetry. The numbers
come from your files, and every one of them traces back to a row.

Most keyword tools hand you a spreadsheet and call it research. Querymantic is
built around the questions that decide a project: what demand exists, how it
clusters, where the client is invisible, and which of those queries now resolve
inside AI search instead of ten blue links.

## Status

Version 0.1.0. Early, and honest about it. The pipeline works end to end:
ingestion, the vendored keyword-intelligence engine, seven analysis modules, an
Italian language layer, and branded deliverables. The full test suite is green
on Python 3.10 and 3.12 in CI. What is documented here works. Anything
still planned lives in [ARCHITECTURE.md](ARCHITECTURE.md) as a roadmap item, not
dressed up as a feature.

## What it does

- Reads CSV or TSV exports from Semrush, Ahrefs, Google Search Console, Moz,
  Ubersuggest, or any generic CSV, and normalizes them to one schema.
- Runs the offline engine: intent classification, topical clusters, AI Overview
  and generative-search scoping, quick wins, cannibalization, content gap.
- Layers seven modules on top:
  - Fan-Out Radar simulates the sub-queries an AI engine expands a topic into,
    then measures how much of that fan your content covers. Most of those
    sub-queries report zero search volume, which is why keyword tools never
    show them.
  - Citation Grid scores, cluster by cluster, how ready your content is to be
    cited in AI answers.
  - Entity Web maps the entities in your corpus and shows which ones you do not
    own yet.
  - Demand Pulse compares runs over time: rising intents, fading ones,
    seasonality.
  - Click Ceiling estimates the clicks you can actually win per cluster, so
    priority follows winnable clicks instead of raw volume.
  - Live Wire (opt-in) merges observed Search Console and AI-citation captures
    into the offline picture. The default stays fully offline.
  - Output Forge turns one run into client-ready deliverables: a script-free
    HTML dashboard, a .pptx deck, a .docx audit, an .xlsx workbook, and an
    optional interactive dashboard, all brandable.
- Adds Italian as a fifth language on top of the engine's English, French,
  German, and Spanish.
- Writes `run.json`: the single state of the run, with a hash of the inputs, so
  every result is reproducible and auditable.

## Install

Clone it where Claude Code looks for plugins, or anywhere you want to run the
CLI:

```bash
git clone https://github.com/mario-montanari/querymantic
cd querymantic
```

The core needs Python 3.10 or newer and nothing else. It runs on the standard
library alone. The optional formats (.pptx, .docx, .xlsx, STL seasonality) each
need one library, pinned in `requirements-optional.txt`. Skip them and the suite
still runs: a missing format is skipped and recorded, never silently faked.

## Use

From the plugin root:

```bash
# Analyze a folder of exports and write run.json
python scripts/querymantic_run.py run --inputs assets/samples/ --output run.json

# Add gap analysis and a branded split
python scripts/querymantic_run.py run --inputs my-exports/ --output run.json \
  --client-domain example.com --brand-list "example,example shop"

# Render deliverables from an existing run
python scripts/querymantic_run.py forge run.json --formats html pptx

# Check an existing run against the contract
python scripts/querymantic_run.py validate run.json
```

Run any command with `--help` for the full option list. Inside Claude Code and
Claude Cowork, the `querymantic` skill and the `/querymantic-analyze` and
`/querymantic-audit` commands wrap the same pipeline.

## How it is built

Querymantic vendors a complete, read-only copy of the keyword-intelligence
engine and adds its own layer on top. The engine answers what demand exists and
how it is structured. The modules answer what to do with it. One canonical
state, `run.json`, ties the two together, and each module is a pure step: it
reads the state, writes its own slot, and touches nothing else.

Determinism is enforced in CI. Same input, same output, byte for byte, checked
on every push against committed expected outputs on Python 3.10 and 3.12. Every
score that rests on an assumption (fan-out width, zero-click share, scoring
weights) is exposed as a parameter with its provenance recorded in the run, so
you can challenge it, override it, and see exactly what changes.

The vendored engine stays byte-identical to its source and is only refreshed
with the sync script. The suite evolves without forking the engine.

## On AI search

A growing share of queries now resolves inside AI Overviews, ChatGPT, and
Perplexity, where the user reads an answer and never clicks. Querymantic treats
that as structure, not magic. There is no secret markup and no special file that
makes an AI cite you. What works is answer-shaped passages, real statistics,
clear citations, and clean structured data on a site a crawler can actually
read. Querymantic scores your demand for that readiness and shows you where AI
search is routing users to someone else.

## Author

Built by Mario Montanari. Working in digital since 1995: SEO, then GEO and AEO,
across automotive, Formula 1, international FMCG, legal, premium travel, and the
public sector. The methodology here is the same one used on client work, written
down.

[mariomontanari.it](https://mariomontanari.it)

## License

MIT. See [LICENSE](LICENSE). Bundled-component attributions are in
[NOTICE](NOTICE).
