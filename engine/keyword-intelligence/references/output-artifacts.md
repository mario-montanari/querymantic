# Output artifacts

## Contents

- The five artifacts and their purposes
- File naming and directory structure
- The Markdown report
- The JSON output
- The enriched CSV
- The TXT executive summary
- The content briefs
- The run-comparison artifacts
- Encoding and locale conventions
- Cross-artifact consistency guarantees
- Versioning and audit metadata

## The five artifacts and their purposes

A single run of the skill produces five files, each addressing a different consumer of the analysis.

The Markdown report is for human reading. It is the artifact the analyst presents to clients and reviewers. It contains structure, narrative, and tables in proportions calibrated for a 30 to 60 minute reading session.

The JSON output is the machine-readable canonical state. It is the artifact downstream tools consume: dashboards, content management systems, custom reports, follow-up scripts. It contains the full intermediate state of the run, not just the final scores.

The enriched CSV is the analyst-portable artifact. It is the original keyword corpus plus every derived column, sorted by the main composite by default but resortable in any spreadsheet. It is the artifact the client team imports into their existing keyword-tracking systems.

The TXT executive summary is for decision-makers who will not read the full report. It compresses the engagement's findings into one page focused on three or four decisions the leadership team needs to make. It opens with the Demand Opportunity Score and names the actual clusters and quick-win keywords to start with.

The content briefs file (`content_briefs.md`) is the bridge from analysis to production. It turns the top clusters by volume into editorial brief skeletons: primary keyword, secondary keywords, questions to answer, dominant intent, suggested format, and recommended action. The skeleton is deterministic; Claude can expand any brief into a full writing brief on request.

The five artifacts are produced from the same intermediate JSON state. The executive summary cannot disagree with the Markdown report; the CSV cannot misalign with the JSON. This consistency is an architectural guarantee, not a discipline applied at write time.

## File naming and directory structure

Every run creates a new output directory named with the run's timestamp and an optional engagement label.

```
output/
└── 2026-05-05_153022_clientname/
    ├── report.md
    ├── analysis.json
    ├── keywords_enriched.csv
    ├── executive_summary.txt
    ├── content_briefs.md
    └── _metadata/
        ├── run_config.json        # the parameters and thresholds used
        ├── input_manifest.json    # the source CSVs ingested
        └── methodology_version.txt # the methodology version this run executed under
```

The timestamp uses the local system time of the run, in `YYYY-MM-DD_HHMMSS` form. The engagement label, when supplied via `--label`, follows the timestamp separated by `_`. The label is sanitized to lowercase letters, digits, and hyphens.

The `_metadata` directory carries the audit trail. Every parameter the run consumed (every threshold, every override, every input file path) is captured. A run is reproducible if and only if the metadata is present.

## The Markdown report

The Markdown report follows a fixed section order. Section content adapts to the corpus, but the order does not change so that readers (and reviewers across multiple engagements) develop predictable reading habits.

### Section order

```
# Keyword intelligence report
## Engagement context
## Corpus summary
## Composite scoring distribution
## Top opportunities
### Quick wins
### Strategic priorities
### Defensive priorities
## Cluster analysis
## Gap analysis
### Keyword gaps
### Content gaps
### Intent and SERP feature gaps
### AEO/GEO gaps
### Entity gaps
### Freshness gaps
## AIO and GEO routing
## Cannibalization findings
## Recommended actions
## Methodology and parameters
```

### Section content rules

Engagement context. Three to five sentences naming the client, the markets covered, the language scope, and the engagement window. Free-text passed via `--engagement-context` parameter or omitted.

Corpus summary. Opens with the Demand Opportunity Score, a single 0 to 100 headline reading of how much actionable demand the corpus holds. Then total keywords, distribution by source, distribution by language, distribution by intent layer. One bar-style ASCII chart per dimension, plus a numeric table. The intent and AI-routing blocks each close with a one-line interpretation at analyst altitude.

Composite scoring distribution. Histograms (ASCII bar charts) of the four composites with key percentiles annotated (50th, 75th, 90th, 99th). Median and mean of each composite. Confidence-band breakdown.

Top opportunities. Three sub-sections, one per relevant composite. Each sub-section contains a table of the top 20 keywords sorted on that composite, with columns for keyword, volume, difficulty, position, intent, cluster, and confidence. The cap is 20 by default; configurable via `--top-n`.

Cluster analysis. Table of the top 30 clusters by cluster_volume_total, with cluster size, dominant intent, and a cluster-level recommendation column. Each cluster row links to a cluster detail block listed below the table for clusters with size ≥ 5.

Gap analysis. Six sub-sections, one per gap dimension that has findings (sub-sections with no findings are omitted from the report rather than shown as empty). Each sub-section opens with a one-paragraph definition of the gap dimension, then a table of findings sorted by priority, then a one-paragraph synthesis.

AIO and GEO routing. Table summarizing the corpus by routing path (`dual`, `aio_only`, `geo_only`, `classical`). Counts and share of total. Sample keywords for each path.

Cannibalization findings. Table of cannibalization-flagged keywords, with the competing URLs and the suggested resolution. Empty section is omitted.

Recommended actions. Synthesis of the gap action classes (`create`, `update`, `restructure`) into a prioritized list. The list is the report's deliverable: it tells the client team what to do next, in what order.

Methodology and parameters. The methodology version, the parameters used, the source files ingested. This section is short (~10 lines) but important: it makes the report auditable.

### Writing conventions

The report uses sentence case in headings, em dash never, straight quotes for inline strings, code blocks for keyword examples and parameter values. Tables use Markdown table syntax. Long keyword strings inside tables are truncated to 80 characters with an ellipsis if needed.

The narrative paragraphs (corpus summary synthesis, gap synthesis, action priorities) follow the same style discipline as the references: dense, opinionated, no filler, no AI-isms.

## The JSON output

The JSON output is the canonical machine-readable state. It is structured for downstream tools and for re-ingestion by future skill runs (a JSON from one run can be passed back into the skill via `--resume-from-json` to skip the parsing stages).

### Top-level structure

```json
{
  "run_metadata": {
    "timestamp": "2026-05-05T15:30:22Z",
    "label": "clientname",
    "methodology_version": "1.0.0",
    "skill_version": "1.0.0",
    "elapsed_seconds": 187
  },
  "input_manifest": {
    "files": [
      {"path": "input/semrush_export.csv", "rows": 12500, "source": "semrush"},
      {"path": "input/gsc_queries.csv", "rows": 8200, "source": "gsc"}
    ],
    "client_domain": "example.com",
    "brand_list": ["example", "ex"]
  },
  "parameters": { ... },
  "corpus_summary": { ... },
  "keywords": [ ... ],
  "clusters": [ ... ],
  "gaps": { ... },
  "recommendations": [ ... ]
}
```

### Per-keyword record schema

Every keyword entry in the `keywords` array follows the same schema.

```json
{
  "keyword": "running shoes review",
  "keyword_original": "Running Shoes Review",
  "language": "en",
  "language_confidence": 0.95,
  "country": "US",
  "source": "semrush",
  "source_file": "input/semrush_export.csv",
  "source_row": 1542,
  "metrics": {
    "volume": 12000,
    "difficulty": 42,
    "cpc": 1.25,
    "position": null,
    "serp_features": ["paa", "ai_overview"],
    "traffic_potential": 4500
  },
  "enrichment": {
    "intent_vector": {
      "query_type": "commercial_investigation",
      "funnel_stage": "consideration",
      "modality": "typed",
      "temporal": "evergreen"
    },
    "branded": false,
    "question_shape": false,
    "token_count": 3,
    "tail_class": "head"
  },
  "scopes": {
    "intent_classification": { ... },
    "cluster_assignment": { ... },
    ...
  },
  "scores": {
    "main": {"score": 68.1, "confidence": 0.87},
    "quick_win": {"score": 52.3, "confidence": 0.85},
    "strategic": {"score": 71.4, "confidence": 0.86},
    "aeo_defensive": {"score": 24.0, "confidence": 0.82}
  }
}
```

The schema is stable within a methodology version. Schema changes require a methodology version bump (see «Versioning and audit metadata» below).

### Cluster records

Each cluster in the `clusters` array contains the head keyword, the member keyword IDs (positions in the `keywords` array), the dominant intent, the volume aggregate, and the action class assigned.

### Gap records

The `gaps` object contains seven keys, one per gap dimension. Each key holds an array of gap findings with priority, evidence, action class, and references to relevant keyword IDs.

## The enriched CSV

The enriched CSV is the original keyword corpus extended with derived columns. Default columns appear in this order:

1. `keyword`
2. `keyword_original` (original casing)
3. `source`
4. `language`
5. `country`
6. `volume`, `difficulty`, `cpc`, `position`, `serp_features`, `traffic_potential` (canonical metrics)
7. `intent_query_type`, `intent_funnel_stage`, `intent_modality`, `intent_temporal` (intent vector)
8. `cluster_head`, `cluster_size` (cluster assignment)
9. `aio_eligibility`, `geo_opportunity` (scopes 3 and 4)
10. `quick_win_flag`, `striking_distance_flag`, `cannibalization_flag`, `content_gap_flag`, `branded_flag`, `question_flag`, `paa_flag`, `seasonality_class`, `long_tail_flag` (other scope flags)
11. `score_main`, `score_quick_win`, `score_strategic`, `score_aeo_defensive`
12. `confidence_main`, `confidence_quick_win`, `confidence_strategic`, `confidence_aeo_defensive`
13. `recommended_action_class` (`create`, `update`, `restructure`, `monitor`, `ignore`)
14. `source_file`, `source_row` (provenance)

Columns can be filtered via `--csv-columns` if the analyst wants a slimmer file for a specific consumer. The `--csv-columns minimal` preset emits the keyword, the four scores, and the action class only.

CSV format conventions: UTF-8 with BOM (the BOM aids Excel's auto-detection); comma separator; double-quote field delimiter for fields containing commas, newlines, or double quotes; CRLF line endings (Windows-friendly default, override with `--csv-line-endings lf`).

## The TXT executive summary

The executive summary is one page of plain text designed for decision-makers who will not read the full report.

### Length and structure

Target length: 40 to 60 lines, hard cap at 80 lines. The cap is enforced; if the synthesis exceeds the cap, the script trims the lowest-priority sentences from the «recommended next steps» section first.

Structure:

```
KEYWORD INTELLIGENCE: EXECUTIVE SUMMARY
[engagement label and date]

Scope of analysis
[2-3 sentences: corpus size, languages, source mix]

What we found
[3-5 bullet points: the top corpus-level findings, ordered by impact]

What we recommend
[3-5 bullet points: the action priorities, ordered by impact]

What we did not analyze
[1-2 sentences naming explicit limits: queries that need separate work, scope that was descoped]

Methodology version: [version]
Confidence note: [overall confidence band: high, mixed, or low, with one-sentence rationale]
```

### Writing rules

The summary uses imperative sentences. It avoids adjectives that do not specify magnitude. It names numbers when numbers exist. It does not repeat the report; it compresses the report.

Example sentence pattern, found versus recommended:

- Found: «The corpus contains 47% AIO-eligible queries against an 18% industry baseline; the client's domain currently appears in 3% of them.»
- Recommended: «Restructure the top 12 cluster hubs for passage extraction over the next quarter; this addresses 73% of the AIO gap.»

The contrast pattern (numeric finding plus numeric impact of recommendation) makes the summary verifiable and actionable. A summary without numbers fails the test.

## The content briefs

The content briefs file (`content_briefs.md`) turns the analysis into the start of an editorial plan, so the analyst leaves with a production roadmap rather than a spreadsheet to interpret.

### Structure

The file lists the top clusters by total search volume (15 by default). Each cluster becomes one brief:

```text
## [cluster head]

- Cluster size: [N] keywords, [total volume] total monthly volume
- Dominant intent: [intent]
- Suggested format: [format mapped from intent]
- Recommended action: [most common action class across the cluster]
- Primary keyword: [highest-volume member]
- Secondary keywords: [next members by volume, deduplicated]
- Questions to answer: [question-shaped members, deduplicated]
```

The suggested format maps from the dominant intent: informational to a guide or explainer, commercial investigation to a comparison or review page, transactional to a product or category page, navigational to a brand page. The recommended action is the action class held by most keywords in the cluster.

### Deterministic skeleton, optional enrichment

The brief skeleton is computed from the canonical state and is fully reproducible. When the user wants finished briefs, Claude reads the cluster and its keywords from the canonical JSON and expands a skeleton into a full writing brief (angle, outline, internal links, entity coverage). The enrichment is a judgment layer on top of a reproducible base, never a replacement for it.

## The run-comparison artifacts

The five artifacts above describe one run. The `compare.py` script describes the movement between two runs and writes its own pair of coordinated artifacts to a separate output directory: `comparison.md` for human reading and `comparison.json` for machine consumption. The `--format` flag selects which to write (`text`, `json`, or `both`); both are produced by default.

### comparison.json structure

```json
{
  "compare_metadata": {
    "generated": "2026-05-05T15:30:22Z",
    "match_key": "keyword",
    "top_n": 15,
    "version_warning": null,
    "baseline": {"path": "...", "label": "q1", "timestamp": "...",
                 "methodology_version": "1.0.0", "total_keywords": 170,
                 "duplicate_records_collapsed": 42},
    "current": {"path": "...", "label": "q2", "timestamp": "...",
                "methodology_version": "1.0.0", "total_keywords": 174,
                "duplicate_records_collapsed": 44}
  },
  "corpus": {
    "demand_opportunity_score": {"baseline": 35.8, "current": 35.9, "delta": 0.1},
    "total_keywords": {"baseline": 170, "current": 174, "delta": 4},
    "aio_eligibility_share": { ... },
    "geo_opportunity_share": { ... },
    "intent_shift": { "commercial_investigation": {"baseline": 80, "current": 84, "delta": 4}, ... }
  },
  "quick_wins": {
    "newly_quick_win": {"count": 5, "keywords": [ ... ]},
    "still_quick_win": {"count": 55, "keywords": [ ... ]},
    "resolved": {
      "captured": {"count": 2, "keywords": [ ... ]},
      "still_climbing": {"count": 0, "keywords": []},
      "regressed": {"count": 0, "keywords": []},
      "reclassified": {"count": 0, "keywords": []},
      "left_corpus": {"count": 0, "keywords": []}
    }
  },
  "scores": {
    "keywords_in_both": 128,
    "mean_delta_by_composite": {"main": {"mean_delta": 0.18, "keywords_compared": 128}, ... },
    "mean_main_confidence_delta": 0.0,
    "top_risers": [ {"keyword": "...", "baseline": 66.1, "current": 71.0, "delta": 4.9}, ... ],
    "top_fallers": [ ... ]
  },
  "positions": {
    "keywords_with_position_in_both": 56,
    "top_climbers": [ {"keyword": "...", "baseline_position": 14.0, "current_position": 2.0, "improvement": 12.0}, ... ],
    "top_decliners": [ ... ]
  },
  "gaps": {
    "keyword_gap": {"baseline_count": 0, "current_count": 0, "count_delta": 0,
                    "closed_samples": [], "opened_samples": [], "samples_partial": false},
    "aeo_geo_gap": { ... },
    "content_gap_intents": {"added": [], "removed": [], "present_now": [ ... ]}
  },
  "membership": {
    "added": {"count": 5, "samples": [ ... ]},
    "dropped": {"count": 1, "samples": [ ... ]}
  }
}
```

### comparison.md sections

The Markdown comparison follows a fixed section order: a header naming both runs and the match key, then Headline (the Demand Opportunity Score and share deltas), Quick wins (captured, still climbing, still open, newly surfaced, regressed), Score movement (mean delta per composite plus risers and fallers tables), Position movement (climbers and decliners tables), Gaps opened and closed, and Corpus membership.

### Matching, capture, and version rules

Keywords are matched across runs by the `--match-key` choice: `keyword` (the normalized string, default) or `keyword-lang` (string plus detected language, for multilingual corpora). When the same keyword appears from several sources, the comparison keeps one representative per key, chosen by highest volume, with ties broken on source name then source row. Volume is stable within an export, so the representative does not flip between runs unless the underlying data changed. The number of duplicate records collapsed per run is reported in `compare_metadata`.

A captured quick win is a keyword that was a quick win in the baseline and now ranks in the top three. A quick win that improved but has not reached the top three is `still_climbing`; one that got worse is `regressed`; one whose label changed for a reason other than position (volume, difficulty, threshold) is `reclassified`; one absent from the current run is `left_corpus`.

Gap sample lists are capped by `analyze.py`, so a set difference on the capped samples can invent spurious opened or closed entries. When a gap exceeds the sample cap, the comparison sets `samples_partial` to true, the Markdown suppresses the per-item lists, and only the count delta (computed from the full tally) is reported.

If the two runs carry different methodology versions, `version_warning` is populated and shown prominently. Scores computed under different methods are not directly comparable; re-run the baseline under the current version before trusting the score deltas.

## Encoding and locale conventions

All five artifacts use UTF-8 encoding by default. The CSV uses UTF-8 with BOM for Excel compatibility, while the Markdown, JSON, and TXT use UTF-8 without BOM.

Number formatting in the Markdown report and the executive summary uses the Anglo-Saxon convention: comma for thousands, period for decimals (`12,000`, `0.87`). The CSV uses period for decimals and no thousands separator (raw numeric values to keep the CSV machine-parseable).

Date formatting uses ISO 8601: `2026-05-05` for dates, `2026-05-05T15:30:22Z` for timestamps. Local timezones are converted to UTC for storage in metadata.

## Cross-artifact consistency guarantees

The five artifacts share an invariant: they are all derived from the same canonical state object after Stage 7's serialization. Three guarantees follow.

A keyword's main composite in the Markdown report equals the same keyword's `score_main` in the JSON and `score_main` in the enriched CSV. No artifact-specific recomputation occurs.

A finding in the gap section of the Markdown report appears in the `gaps` block of the JSON with the same priority value and the same action class. No interpretive paraphrase changes the values.

The executive summary's numeric claims are pulled from the JSON state, not regenerated. If the executive summary states «47% AIO-eligible», the JSON's `corpus_summary.aio_eligibility_share` field equals 0.47.

These guarantees are enforced by the script architecture: the output writers consume the canonical state and emit, never recompute.

## Versioning and audit metadata

Every run produces three audit files in the `_metadata` subdirectory.

`run_config.json` captures every parameter the run consumed. The file is a flat dictionary mapping parameter names (as they appear in `--help`) to the values used in this run. Defaults are included explicitly (a value not overridden is recorded with its default).

`input_manifest.json` captures the input files: their absolute paths at run time, their SHA-256 hashes, their row counts, and the canonical source category each was assigned. The hashes let a future re-run detect whether the inputs have changed.

`methodology_version.txt` contains the methodology version string, e.g. `1.0.0`. Bump rules:

- Patch (1.0.0 → 1.0.1): bug fix that does not change scores for any keyword.
- Minor (1.0.0 → 1.1.0): rule additions, threshold default changes, new scopes; existing scores may shift.
- Major (1.0.0 → 2.0.0): formula reweightings, schema changes, removed features; scores from previous versions are not directly comparable.

A re-run with `--resume-from-json` requires the methodology version in the JSON to match the running skill's version. Mismatches abort with a remediation message asking the analyst to choose: re-run from CSVs to apply the new methodology, or pin the skill to the older methodology version.

This versioning discipline keeps the skill auditable across time. A report from six months ago is reproducible because its metadata is complete and its methodology version is accessible.
