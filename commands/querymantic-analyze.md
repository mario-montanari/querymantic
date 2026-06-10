---
description: Run the Querymantic pipeline on keyword exports and write run.json.
argument-hint: "[inputs] [output]"
allowed-tools: Read, Bash, Glob, Grep
---

Run an offline keyword and demand analysis with Querymantic.

Inputs: `$1` is the input file or directory of CSV/TSV exports. `$2` is the output
path for `run.json` (default `run.json` if not given).

Steps:

1. If `$1` is a directory, list its CSV/TSV files with Glob.
2. Run: `python scripts/querymantic_run.py run --inputs $1 --output ${2:-run.json}`.
3. Read the resulting `run.json` and summarize corpus size, the strongest clusters,
   and the engine's AI-search and gap signals. Report figures exactly as written in
   the file; do not invent numbers.
