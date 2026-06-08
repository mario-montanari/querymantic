---
name: output-forge
description: "Use when turning a Spektr run.json into client-ready deliverables, or when a user asks to export, package, or brand a Spektr analysis. Triggers: build the deck, generate the report, export the audit, branded output, white-label, slide deck, Word audit, Excel dashboard, HTML dashboard, .pptx, .docx, .xlsx from a run."
user-invokable: true
argument-hint: "[run.json] [--out DIR] [--brand brand.json]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Output Forge: deliverables from a run.json

## Overview

Output Forge renders a finished Spektr `run.json` into deliverables: a self-contained
HTML dashboard, a slide deck, a Word audit, and an Excel workbook. The HTML dashboard
needs no third-party package and is always produced; the three Office formats need
optional backends and are skipped, with a recorded reason, when those backends are
absent. A white-label `brand.json` sets the look and the authorship. Output is
byte-deterministic: the same `run.json` renders the same bytes.

## When to use

- A `run.json` exists and a client wants the analysis as a deck, a document, a
  spreadsheet, or a shareable web page.
- An agency wants the same audit under its own brand.
- A reproducible artifact is needed, where two renders of one run match byte for byte.

Do not use to compute new analysis; Output Forge only renders what the modules
already wrote. Run the analysis modules first (see the `spektr` skill).

## Render from an existing run.json

Render without re-running the engine:

```bash
python scripts/spektr_run.py forge run.json --out forge_output --brand forge/templates/brand.json
```

This writes the artifacts to the output directory and records a manifest in the
`output_forge` slot of `run.json`. Limit the formats with `--formats html docx`. Run
`python scripts/spektr_run.py forge --help` for the full option list.

## Render as part of a pipeline run

Add `output_forge` to the module list to render in the same pass that builds the run:

```bash
python scripts/spektr_run.py run --inputs exports/ --output run.json \
  --modules entity_web fan_out_radar citation_grid click_ceiling output_forge \
  --brand forge/templates/brand.json --forge-out forge_output
```

## White-label branding

Copy `forge/templates/brand.json` and edit the name, tagline, footer, contact, font
stack, colours (hex), and author. Every field is optional and falls back to a neutral
default. Pass the file with `--brand`. The author follows the brand name unless set
explicitly, so a custom brand never carries the default author into its documents.

## The artifacts

- `dashboard.html`: self-contained, inline SVG charts, no external resource. Always
  produced.
- `deck.pptx`: slide deck. Needs `python-pptx`.
- `audit.docx`: written audit. Needs `python-docx`.
- `dashboard.xlsx`: sortable workbook. Needs `openpyxl`.

The Office backends are optional. Without them, the HTML dashboard still renders and
the manifest lists the skipped formats with the reason. Install the backends to
produce the Office files.

## What lands in run.json

The `output_forge` slot records the render mode, the pinned timestamp, the brand name
and a short fingerprint, the backend availability, the formats requested, each
artifact with its byte size and SHA-256, and any format skipped with its reason. The
slot carries no absolute path, so it stays portable, and it is byte-stable across two
runs on the same input.

## Methodology

For how the shared report view is built, how determinism is achieved (pinned
timestamps and OOXML archive normalisation), and the expected-against-observed rule,
see [references/output-forge.md](../../references/output-forge.md).
