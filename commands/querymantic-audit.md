---
description: Run a full Querymantic audit (pipeline plus all available modules) and summarize findings.
argument-hint: "[inputs] [client-domain]"
allowed-tools: Read, Bash, Glob, Grep
---

Run a full offline audit with Querymantic.

Inputs: `$1` is the input file or directory of CSV/TSV exports. `$2` is the optional
client domain for gap analysis.

Steps:

1. If `$1` is a directory, list its CSV/TSV files with Glob.
2. Run the pipeline with every available module, in order. `language_layer` leads so
   any Italian keyword is corrected before the analysis modules read it (it is a no-op
   on a corpus in another language):
   `python scripts/querymantic_run.py run --inputs $1 --output run.json --client-domain $2 --modules language_layer entity_web fan_out_radar demand_pulse citation_grid click_ceiling`.
   Drop `--client-domain` if `$2` is empty. Drop any module name the build does not
   yet register; the CLI rejects unknown modules, so request only modules that exist.
3. Read `run.json` and produce an audit summary: corpus size, demand opportunity,
   AI-search routing and gaps from the engine, plus each module's findings.
4. Report figures exactly as written in `run.json`. State plainly when a module has
   not run rather than estimating its result.
