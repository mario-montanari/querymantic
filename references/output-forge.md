# Output Forge

## Contents

- What it produces
- The shared view
- The four formats
- White-label branding
- Determinism: pinned timestamps and archive normalisation
- Degradation and the dependency budget
- The manifest in run.json
- Expected against observed in the deliverables
- Limitations

## What it produces

Output Forge is the last module. It reads the finished run-state and renders it into
deliverables: a self-contained HTML dashboard, and a slide deck, a Word audit, and
an Excel workbook when their optional backends are installed. The files are written
to an output directory; the run-state itself only gains the `output_forge` slot,
which carries a manifest of what was produced. It is a pure step and changes nothing
else in the run-state.

## The shared view

The four renderers do not each walk the run-state on their own. A single function
builds one normalised view (`modules/output_forge/model.py`): the corpus headline
figures, the clusters ordered by demand with every per-module metric folded in, the
winnable-clicks summary, the citation-readiness summary, the entity gaps, and the
observed block when Live Wire ran. Every renderer consumes that view, so a deck and
a workbook can never report different numbers for the same cluster. The view is
plain data and deterministic: derived floats are rounded and clusters are ordered,
so two runs on the same input build the same view.

## The four formats

- **HTML dashboard** (`dashboard_html.py`): standard library only, no third-party
  package, no external resource. Charts are inline SVG, styles are inlined, and
  there is no script tag and no content delivery network reference, so the file
  opens identically on a machine with no network. This is the format the suite
  always produces and the floor it degrades to.
- **Slide deck** (`deck.py`, `.pptx`): a short, presentable deck behind
  `python-pptx`.
- **Word audit** (`audit_docx.py`, `.docx`): a written audit behind `python-docx`.
- **Excel dashboard** (`dashboard_xlsx.py`, `.xlsx`): a sortable, filterable
  workbook behind `openpyxl`.

The three Office formats are Office Open XML documents, the packaging format
standardised as ECMA-376 and ISO/IEC 29500. An OOXML file is a ZIP archive of XML
parts, which matters for determinism below.

Primary references for the formats and backends:

- ECMA-376, Office Open XML File Formats:
  https://ecma-international.org/publications-and-standards/standards/ecma-376/
- python-pptx: https://pypi.org/project/python-pptx/
- python-docx: https://pypi.org/project/python-docx/
- openpyxl: https://pypi.org/project/openpyxl/
- Plotly (planned interactive enhancement): https://pypi.org/project/plotly/

## White-label branding

A single `brand.json` (template under `forge/templates/`) drives the look and the
authorship of every artifact: the name, tagline, footer, contact, font stack, and a
small colour palette, plus the document author written into the Office core
properties. Every field is optional and falls back to a neutral default, so a run
with no brand file still produces complete, unbranded output. The brand is validated
on load (colours must be hex), and the manifest records a short fingerprint of the
resolved brand rather than a file path, so the run-state carries no absolute path.

## Determinism: pinned timestamps and archive normalisation

The suite's promise is that the same input gives the same output. For text that is
easy: the HTML dashboard is byte-identical across runs because every value comes
from the deterministic view and the only timestamp shown is the run timestamp, which
is itself pinnable (`--deterministic-timestamp`).

The Office formats need two extra steps, because a naive save is not reproducible:

1. **Pinned document dates.** Each renderer sets the core-properties created and
   modified dates to the run timestamp, instead of letting the backend stamp the
   wall clock.
2. **Archive normalisation.** An OOXML file is a ZIP, and the ZIP format records a
   modification time per member, defaulting to the current local time, so two saves
   of identical content differ byte for byte. `spektr_core/ports/ooxml.py`
   rewrites the produced archive with a fixed member time (the 1980 ZIP epoch) and a
   stable member order. This is the conventional reproducible-archive technique; see
   the reproducible-builds guidance on archive metadata at
   https://reproducible-builds.org/docs/archives/.

Together these make the Office output byte-identical across two runs on the same
input in the same environment. Byte-equality across different backend versions is
not guaranteed: a different `python-pptx` or `openpyxl` release can serialise the
same content differently. That is the backend's behaviour, not the module's, and it
is the reason the determinism proof in the test suite runs twice in one environment.

## Degradation and the dependency budget

The Office backends are optional by the tiered dependency budget. The module asks
`ooxml_capabilities()` once; a format whose backend is absent is skipped and recorded
in the manifest under `skipped`, with the reason, never raised as an error. A run on
a stdlib-only machine therefore still produces the HTML dashboard and a complete
manifest. A backend that is present but fails mid-render is caught the same way, so
one bad format never loses the others.

## The manifest in run.json

The `output_forge` slot records, deterministically: the render mode, the pinned
`generated_at`, the brand name and fingerprint, the backend availability map, the
formats requested, the artifacts produced (each with its filename, byte size, and
SHA-256), and the formats skipped with reasons. The SHA-256 of each artifact is the
determinism proof: the same input yields the same bytes yields the same digest. The
manifest holds no absolute path, so it stays portable.

## Expected against observed in the deliverables

The deliverables inherit the suite's discipline that expected and observed figures
are never conflated. The shared view marks an observed value as the headline only
where Live Wire actually measured one, and keeps the expected value beside it. When
Live Wire did not run, the deliverables show expected figures alone, labelled as
such. The "how to read these figures" section in every format states the provenance
rules in plain language.

## Limitations

- The Office renderers are exercised in continuous integration, where the backends
  install. On a stdlib-only machine they are not run; the suite degrades to the HTML
  dashboard, and the manifest records the skip.
- Office byte-equality is environment-bound, as noted above: it holds across runs
  with the same backend versions, not across versions.
- The interactive Plotly charts are a planned enhancement. The HTML dashboard's
  inline-SVG charts are the current, self-contained implementation; a pinned,
  vendored copy of plotly.js is not bundled yet.
- The dashboard surfaces the top clusters and gaps by demand, not every row; the
  Excel workbook carries the full per-cluster table for analysts who need it.
