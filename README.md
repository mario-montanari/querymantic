# Querymantic

Offline keyword and demand intelligence for Claude Code and Claude Cowork.

You drop in your keyword exports. Querymantic reads them, runs a deterministic analysis,
and writes one structured file you can build on. No external API, no account, no data
leaving your machine. The numbers come from your files and you can trace every one of
them back to a row.

Most keyword tools hand you a spreadsheet and call it research. A spreadsheet is not a
strategy. Querymantic is built around the questions that actually decide a project: what
demand exists, how it clusters, where the client is invisible, and which of those
queries now route through AI search instead of ten blue links.

## Status

Version 0.1.0. The base pipeline works: it ingests your exports, runs the vendored
keyword-intelligence engine, and produces a validated `run.json`. The analysis modules
(entity coverage, query fan-out, demand trend, AI-citation readiness, winnable clicks,
branded output) are being added one at a time. The roadmap is in
[ARCHITECTURE.md](ARCHITECTURE.md). What is documented as working, works. What is not
built yet is named as a module slot, not dressed up as a feature.

## What it does today

- Reads CSV or TSV exports from Semrush, Ahrefs, Google Search Console, Moz,
  Ubersuggest, or a generic CSV, and normalises them to one schema.
- Runs the offline engine to produce intent classification, topical clusters, AI
  Overview and generative-search scopes, quick wins, cannibalisation, content gap,
  and more.
- Writes `run.json`: the single source of truth for the run, with a hash of the
  inputs so a result is always reproducible and auditable.

## Install

Clone into your Claude Code plugins, or run the CLI directly. The suite needs only
Python 3.10 or newer from the standard library. There is nothing to `pip install` for
the core.

```bash
git clone <your-fork> querymantic
cd querymantic
```

## Use

From the plugin root:

```bash
# Analyse a folder of exports and write run.json
python scripts/querymantic_run.py run --inputs assets/samples/ --output run.json

# Add gap analysis and a branded split
python scripts/querymantic_run.py run --inputs my-exports/ --output run.json \
  --client-domain example.com --brand-list "example,example shop"

# Check an existing run against the contract
python scripts/querymantic_run.py validate run.json
```

Run any command with `--help` for the full option list. Inside Claude Code, the
`querymantic` skill and the `/querymantic-analyze` and `/querymantic-audit` commands wrap the same
pipeline.

## How it is built

Querymantic vendors a complete, read-only copy of the keyword-intelligence engine and adds
its own layer on top. The engine answers what demand exists and how it is structured.
The modules answer what to do with it. One canonical state, `run.json`, ties the two
together, and each module is a pure step that reads that state and writes its own part
of it. The full design is in [ARCHITECTURE.md](ARCHITECTURE.md).

The engine stays untouched: the vendored copy is byte-identical to its source and is
only ever refreshed with the sync script. That keeps the base analysis reproducible
and lets the suite evolve without forking the engine.

## On AI search

A growing share of queries now resolve inside AI Overviews, ChatGPT, and Perplexity,
where the user reads an answer and never clicks. Querymantic treats that as structure, not
magic. There is no secret markup and no special file that makes an AI cite you. What
works is answer-shaped passages, real statistics, clear citations, and clean
structured data, on a site a crawler can actually read. Querymantic scores your demand for
that readiness and shows you where AI search is routing users to someone else.

## Author

Built by Mario Montanari. Working in digital since 1997: SEO, then GEO and AEO, across
automotive, Formula 1, international FMCG, legal, premium travel, and public sector.
The methodology here is the same one used on client work, written down.

[mariomontanari.it](https://mariomontanari.it)

## License

MIT. See [LICENSE](LICENSE). Bundled-component attributions are in [NOTICE](NOTICE).
