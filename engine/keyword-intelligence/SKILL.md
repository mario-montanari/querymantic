---
name: keyword-intelligence
description: Use when analyzing keyword data for SEO, AEO, or GEO strategy from CSV exports of Semrush, Ahrefs, Google Search Console, Moz, Ubersuggest, or any keyword research tool. Provides offline keyword intelligence covering intent classification, cluster mapping, AI Overview eligibility, generative engine opportunity (ChatGPT, Perplexity, Claude, Gemini), quick-win identification, cannibalization detection, content gap analysis, striking-distance scoping, branded-versus-non-branded segmentation, question and PAA mapping, seasonality detection, and long-tail handling for English, French, German, and Spanish. Triggers on tasks involving keyword research, search demand analysis, content strategy planning, AI search visibility, or keyword CSV files.
Name: keyword-intelligence
Tier: POWERFUL
Category: SEO Intelligence
Dependencies: None (Python Standard Library Only)
Author: Mario Montanari, mariomontanari.it
Version: 1.0.0
Last Updated: 2026-06-03
---

# Keyword intelligence

## Name

keyword-intelligence

## Description

A vendor-neutral, offline keyword intelligence methodology for SEO, Answer Engine Optimization (AEO), and Generative Engine Optimization (GEO) work. The skill ingests CSV exports from any major keyword research tool, runs a deterministic seven-stage pipeline, and produces five coordinated output artifacts that drive content architecture, triage, AI search visibility, and editorial production decisions.

The skill rests on one principle: keywords are observations of demand, not the demand itself. The deliverable is a structured map of intents, clusters, and gaps, not a sorted list. A list ranks strings by attractiveness. A map shows the analyst what is missing, what overlaps, what competitors own, and what generative engines route through. The two outputs lead to different decisions.

The skill is designed for reproducibility. Two analysts running the same inputs through the same parameters produce the same scoring and the same recommendations. This separates intelligence from extraction: extraction is a one-off act, intelligence is a process.

## Features

The skill provides ten core capabilities organized as a coherent pipeline plus a dedicated theoretical foundation across three reference documents.

1. Multi-tool input normalization. Accepts CSV exports from Semrush (Keyword Magic, Position Tracking, Organic Research), Ahrefs (Keywords Explorer, Site Explorer, Content Gap), Google Search Console (Performance reports), Moz (Keyword Explorer), Ubersuggest (Keyword Ideas), plus generic CSVs and custom mappings. All input maps to one canonical schema documented in [references/input-normalization.md](references/input-normalization.md).

2. Twelve analytical scopes per keyword. Intent classification (four-axis vector), cluster assignment, AIO eligibility, GEO opportunity, quick wins, cannibalization risk, content gap, striking distance, branded versus non-branded, questions and PAA, seasonality, long tail. Each scope produces a label, a confidence score, and supporting evidence. Full rules in [references/analysis-scopes.md](references/analysis-scopes.md).

3. Four composite scores per keyword. Main composite for general SEO performance, quick-win composite for quarterly horizon prioritization, strategic composite for architectural decisions, AEO/defensive composite for brand-protective and AI-search-protective targets. Every composite carries a confidence score from 0 to 1. Full formulas in [references/scoring-formulas.md](references/scoring-formulas.md).

4. Seven gap dimensions at corpus level. Keyword gap, content gap, intent gap, SERP feature gap, AEO/GEO gap, entity gap, freshness gap. Each gap finding receives a priority and an action class (`create`, `update`, `restructure`, `monitor`, `ignore`).

5. AI search routing analysis. Every keyword routes to one of four optimization paths (`dual`, `aio_only`, `geo_only`, `classical`) based on the combination of AIO eligibility and GEO opportunity. Patterns and citation-readiness practices in [references/aio-geo-optimization.md](references/aio-geo-optimization.md).

6. Multi-language support. Full per-language rule sets for English, French, German, and Spanish: stop words, intent markers across four intent layers, question detection patterns, light morphological normalization for cluster matching. Reference tables in [references/multi-language.md](references/multi-language.md).

7. Five coordinated output artifacts. Markdown report for human delivery, JSON for machine consumption, enriched CSV for analyst portability, TXT executive summary for decision-makers, and per-cluster content briefs to seed editorial production. All five artifacts derive from the same canonical state, ensuring cross-artifact consistency. Structure in [references/output-artifacts.md](references/output-artifacts.md).

8. Pre-flight validation and audit. The `audit.py` script runs structural and content validation on inputs before the pipeline executes, flagging issues that would cause failures or produce misleading output.

9. Run-over-run comparison. The `compare.py` script reads two canonical JSON states and reports what changed between them: the Demand Opportunity Score and corpus shares, quick wins captured or newly surfaced, composite score movement, position movement, and gaps opened or closed. Because the methodology is deterministic, every reported delta reflects a change in the data, not noise in the method.

10. Theoretical foundation. Three dedicated reference documents cover the conceptual ground that the operational pipeline rests on: [references/semantics.md](references/semantics.md) covers semantic search from LSA to dense retrieval, embedding models, and the Google milestones (RankBrain, BERT, MUM, AI Overviews); [references/clustering.md](references/clustering.md) covers SERP-based clustering, embedding-based clustering, algorithmic families, hybrid approaches, and the roadmap toward an embedding-augmented v2; [references/entity-and-topical-authority.md](references/entity-and-topical-authority.md) covers entity SEO, named practitioners, knowledge graph integration, topical authority mechanisms, AEO/GEO empirical research, and brand SERP optimization. These documents make the skill auditable not just at the implementation level but at the level of methodological choices.

## Usage

The skill exposes four CLI entry points.

```bash
# Pre-flight audit on input files
python scripts/audit.py --inputs assets/samples/

# Full analysis pipeline (normalization, enrichment, scoring, output)
python scripts/analyze.py \
  --inputs assets/samples/ \
  --client-domain example-shoes.com \
  --brand-list "example,example shoes" \
  --output output/run_2026-05-05/

# Standalone artifact regeneration from existing canonical JSON
python scripts/report.py --input output/run_2026-05-05/analysis.json

# Run-over-run comparison of two canonical JSON states
python scripts/compare.py \
  --baseline output/run_2026-02-05/analysis.json \
  --current output/run_2026-05-05/analysis.json \
  --output-dir output/q1_vs_q2/
```

The expected workflow is audit → analyze → report. Audit verifies inputs and surfaces issues. Analyze runs the pipeline and writes the canonical JSON plus the five artifacts (it invokes report.py internally unless `--json-only` is passed). Report can be invoked standalone to regenerate artifacts from a previously produced canonical JSON, useful for reformatting without re-running the pipeline. Compare is optional and runs on demand: point it at two canonical JSON files from different points in time to track progress between engagements.

For a smoke test on the bundled sample data:

```bash
python scripts/analyze.py --inputs assets/samples/ \
  --client-domain example-shoes.com \
  --brand-list example \
  --output expected_outputs/sample_run/
```

The sample run reproduces the artifacts in `expected_outputs/sample_run/`, providing a baseline that any environment can verify.

## When to use this skill

Activate this skill when:

- The analyst has CSV exports from Semrush, Ahrefs, Google Search Console, Moz, Ubersuggest, or another keyword research tool, and needs structured analysis beyond what the tools provide natively.
- The task involves planning content architecture (hubs, pillars, satellites), not just listing target keywords.
- The engagement requires AI search visibility analysis (Google AI Overviews, Perplexity, ChatGPT search, Claude search, Gemini) alongside classical SEO.
- The analyst needs to identify content gaps, cannibalization risks, quick wins, or striking-distance opportunities across a keyword corpus.
- The corpus spans multiple languages (English, French, German, Spanish are supported with full per-language rules).
- The work demands reproducibility: two analysts running the same inputs through the same parameters must produce the same scoring and recommendations.

The skill is not the right tool for: live SERP tracking (it processes static CSV exports), keyword extraction from search engines (it consumes existing exports), or real-time rank monitoring (it is offline).

## Inputs

The skill accepts CSV exports from the following tools natively, mapping each tool's columns to a canonical schema:

| Tool | Recognized exports |
|---|---|
| Semrush | Keyword Magic Tool, Position Tracking, Organic Research, Domain vs Domain |
| Ahrefs | Keywords Explorer, Site Explorer, Content Gap |
| Google Search Console | Performance reports (queries) |
| Moz | Keyword Explorer |
| Ubersuggest | Keyword Ideas, SEO Analyzer |
| Generic CSV | Any CSV with at least a `keyword` column |

For unrecognized exports, supply a mapping JSON via `--mapping`. Detailed schema and per-tool column maps are in [references/input-normalization.md](references/input-normalization.md).

Beyond CSV exports, the skill accepts:

- A client domain (`--client-domain`) for cannibalization, striking-distance, and content-gap analysis.
- A brand list (`--brand-list`) for branded segmentation, with fuzzy matching for misspellings.
- A custom rule file (`--custom-rules`) for analyst-supplied scope refinements.
- An optional content recency manifest (`--content-recency`) for freshness-gap analysis.

The skill operates with as little as a single CSV containing only the `keyword` column. Every additional column unlocks more analyses and tightens the confidence on the composite scores.

## Outputs

A run produces a timestamped output directory containing:

```
output/2026-05-05_153022_clientname/
├── report.md                  # Markdown report for human delivery
├── analysis.json              # Full canonical state, machine-readable
├── keywords_enriched.csv      # Original corpus plus all derived columns
├── executive_summary.txt      # One-page summary for decision-makers
├── content_briefs.md          # Per-cluster brief skeletons for editorial production
└── _metadata/
    ├── run_config.json        # Parameters and thresholds applied
    ├── input_manifest.json    # Source files with hashes and row counts
    └── methodology_version.txt
```

The five artifacts are derived from the same canonical state, ensuring cross-artifact consistency: the executive summary cannot disagree with the report, the CSV cannot misalign with the JSON. Detailed structure of each artifact is in [references/output-artifacts.md](references/output-artifacts.md).

The content briefs are deterministic skeletons (primary keyword, secondaries, questions, intent, format, action) for the top clusters by volume. When the user asks for finished briefs, read the cluster and its keywords from the canonical JSON and expand a skeleton into a full writing brief (angle, outline, internal links, entity coverage). This enrichment is a judgment layer on top of the reproducible base, never a replacement for it. The Markdown report and the executive summary both lead with the Demand Opportunity Score, a single 0 to 100 reading of how much actionable demand the corpus holds.

## The methodology

Keyword research has been treated for two decades as the production of a list. This skill reframes it as the production of a graph: nodes are intents, topics, and entities; edges are semantic, navigational, and intentional relationships. The list remains as a projection of the graph, not as the deliverable itself.

Seven principles guide every analysis decision:

1. Keywords are observations, not the demand itself.
2. Structure beats volume.
3. Vendor-neutrality is a methodological commitment, not a software convenience.
4. Reproducibility separates intelligence from extraction.
5. Decision-grade outputs require traceable inputs.
6. Intent stratification beats intent labeling.
7. Priority and confidence are two scores, not one.

Each principle is operational, not philosophical. The full reasoning, with the failure modes each principle prevents, is in [references/methodology-overview.md](references/methodology-overview.md).

## The seven-stage workflow

Every run executes the same seven stages in sequence:

1. Sourcing. Six categories of keyword input (seed, algorithmic expansion, competitor extraction, internal data, linguistic expansion, generative AI sourcing).
2. Normalization. Heterogeneous CSVs map to one canonical schema; divergences across sources are preserved as signal, not averaged.
3. Enrichment. Language detection, intent vector, branded segmentation, question detection, token statistics.
4. Scope analysis. Twelve analytical lenses applied per keyword.
5. Scoring. Four composite scores per keyword (main, quick-win, strategic, AEO/defensive) plus a confidence score.
6. Gap analysis. Seven gap dimensions evaluated at the corpus level.
7. Output generation. Five artifacts written from the canonical state.

The pipeline supports stage-level resumption: re-running from Stage 4 reuses the normalized corpus from Stage 2 without re-reading the source CSVs. This makes iteration cheap. Detailed stage rules and intermediate state shapes are in [references/workflow.md](references/workflow.md).

## The twelve analysis scopes

Every keyword passes through twelve analytical lenses, executed in dependency order:

| # | Scope | What it captures |
|---|---|---|
| 1 | Intent classification | Four-axis vector: query type, funnel stage, modality, temporal layer |
| 2 | Cluster assignment | Semantic groups for content-architecture decisions |
| 3 | AIO eligibility | Likelihood of triggering Google AI Overviews |
| 4 | GEO opportunity | Likelihood of routing through generative engines |
| 5 | Quick wins | Reachable inside one quarter of focused effort |
| 6 | Cannibalization risk | Multiple client URLs competing for the same query |
| 7 | Content gap | Queries staffed by competitors but not by the client |
| 8 | Striking distance | Client positions 4-20 with realistic top-3 potential |
| 9 | Branded versus non-branded | Brand list match, with fuzzy variations |
| 10 | Questions and PAA | Question shape and People Also Ask presence |
| 11 | Seasonality | Predictable temporal demand patterns |
| 12 | Long tail | Low-volume high-specificity queries |

Each scope produces a label, a confidence score, and supporting evidence. Full rules, thresholds, and edge cases for every scope are in [references/analysis-scopes.md](references/analysis-scopes.md).

## Scoring

Every keyword receives four composite scores:

- Main composite: default ranking score for general SEO performance.
- Quick-win composite: prioritizes keywords reachable in one quarter.
- Strategic composite: prioritizes architectural decisions over single-keyword wins.
- AEO/defensive composite: surfaces brand-protective and AI-search-protective targets.

Each composite carries a confidence score from 0 to 1, computed as the geometric mean of input completeness, source reliability, and enrichment certainty. A keyword scoring 92 with confidence 0.4 is a research target. The same composite with confidence 0.95 is an action target. The skill never collapses the two layers into a single number.

Gap analysis additionally evaluates seven gap dimensions at the corpus level (keyword, content, intent, SERP feature, AEO/GEO, entity, freshness) and assigns each gap finding a priority and an action class (`create`, `update`, `restructure`, `monitor`, `ignore`). Full formulas, weights, and worked examples are in [references/scoring-formulas.md](references/scoring-formulas.md).

## Multi-language support

The skill supports four languages with full per-language rule sets: English, French, German, and Spanish. Per-language rules cover stop words, intent markers (transactional, commercial, informational, navigational), question detection patterns, and morphological normalization for cluster matching.

For other languages (Italian, Portuguese, Dutch, Polish, and so on), the skill runs in degraded mode: it accepts the keywords, performs token statistics and basic intent detection, but does not apply morphological normalization or language-tuned intent markers. Output rows in unsupported languages are flagged with `language_support: degraded`.

Right-to-left languages (Arabic, Hebrew) and CJK languages (Chinese, Japanese, Korean) are out of scope. The skill detects them, marks them out_of_scope, and processes only token statistics. Full per-language reference tables are in [references/multi-language.md](references/multi-language.md).

## AI search optimization

A keyword in 2026 can route to three distinct search experiences: classical SERP, Google AI Overviews, and generative engines (Perplexity, ChatGPT, Claude, Gemini). The skill treats these as separate optimization problems and identifies which keywords route to which.

The combination of AIO eligibility (scope 3) and GEO opportunity (scope 4) produces four routing paths:

- `dual`: optimize for both AI Overviews and generative engines.
- `aio_only`: classical retrieval rank plus passage extraction.
- `geo_only`: crawl accessibility, citation readiness, brand mention signals.
- `classical`: standard SEO applies.

The Markdown report and the JSON expose the routing per keyword. The executive summary names the share of corpus in each path so strategic discussion can allocate effort proportionally. Full optimization patterns, including llms.txt, AI crawler accessibility, brand mention signals, and passage-level citability, are in [references/aio-geo-optimization.md](references/aio-geo-optimization.md).

## Reading the output

Three reading paths fit different consumers.

For decision-makers: open the executive summary first. One page, three to five findings, three to five recommended actions, methodology version. If the summary is unconvincing, reading the report will not save it; the corpus or the thresholds need work.

For analysts and SEO leads: open the Markdown report. The section order is fixed across runs, so reading habits transfer. Start with the corpus summary and the composite distribution, then read the gap analysis, then the recommended actions section. The cluster analysis and the per-scope details support the recommendations.

For downstream automation: consume the JSON. The schema is documented and stable within a methodology version. The full intermediate state is present, including per-keyword scope outputs, cluster membership, and gap findings.

The enriched CSV serves both client teams and analysts who prefer spreadsheets. Default columns are sorted to put score-and-action columns near the right edge for resorting; full column inventory is in [references/output-artifacts.md](references/output-artifacts.md).

## Comparing runs over time

Run `compare.py` on two canonical JSON states to see what moved between two points in time. It surfaces the Demand Opportunity Score delta, quick wins captured (a striking-distance keyword that broke into the top three) versus newly surfaced, per-keyword composite and position movement, and gaps opened or closed. It writes two coordinated artifacts, `comparison.md` and `comparison.json`, selectable with `--format`. The comparison is meaningful precisely because the pipeline is deterministic: when both runs share a methodology version, every delta is a data change, not method noise. A version mismatch is flagged prominently, since scores from different methodology versions are not directly comparable. Comparison structure is documented in [references/output-artifacts.md](references/output-artifacts.md).

## Handing off to other skills

The canonical `analysis.json` is a stable, documented contract within a methodology version, which makes it a clean handoff to other skills in the Claude ecosystem: a content-quality skill consumes the clusters and content briefs, a GEO skill consumes the AIO and GEO routing and the AEO/GEO gap, a humanizing skill polishes the prose artifacts before delivery, and generic automation consumes the enriched CSV. The skill produces the contract; it does not call those skills, and the orchestration stays with the analyst. Field-level handoff recipes are in [references/ecosystem-contract.md](references/ecosystem-contract.md).

## Examples

### Example 1: a single Semrush export

```bash
python scripts/analyze.py \
  --inputs input/semrush_export.csv \
  --client-domain example.com \
  --brand-list "example" \
  --output output/example1/
```

A single-tool corpus runs through all seven stages with full functionality except cross-tool divergence preservation (with one source there is no divergence to preserve).

### Example 2: multi-tool corpus with GSC

```bash
python scripts/analyze.py \
  --inputs input/semrush.csv input/ahrefs.csv input/gsc.csv \
  --client-domain example.com \
  --brand-list "example,ex,exco" \
  --output output/multi_source/ \
  --label q2_planning
```

GSC data raises the confidence on every keyword the client's domain already serves, and the cross-tool divergence in volume and difficulty estimates is reported in the JSON for analyst review.

### Example 3: focused on AI search

```bash
python scripts/analyze.py \
  --inputs input/all_sources/ \
  --client-domain example.com \
  --brand-list "example" \
  --aio-eligibility-min 50 \
  --geo-opportunity-min 50 \
  --output output/ai_search_focus/
```

Lowered thresholds for AIO and GEO scopes pull more candidates into the AI search routing tables. Useful for engagements where the AI search visibility is the primary objective.

### Example 4: cluster-architecture engagement

```bash
python scripts/analyze.py \
  --inputs input/all_sources/ \
  --client-domain example.com \
  --cluster-overlap-min 0.50 \
  --output output/architecture_planning/
```

A lower cluster overlap threshold (50% instead of 60%) produces broader clusters, which suits architecture work where the analyst wants to see the maximal coverage map before splitting into sub-clusters.

### Example 5: defensive sweep on a brand

```bash
python scripts/analyze.py \
  --inputs input/branded_corpus.csv input/gsc_branded.csv \
  --client-domain example.com \
  --brand-list "example,exco,exsupport" \
  --cannibalization-include-branded \
  --output output/defensive/
```

Branded corpora with explicit cannibalization detection identify cases where two client URLs compete for branded queries, a frequent issue when multiple subdomains or product lines target overlapping intents.

## Configuration

Every threshold and weight has a CLI flag with a documented default. Run `python scripts/analyze.py --help` for the full list. The most-tuned parameters in real engagements are:

| Parameter | Default | Purpose |
|---|---|---|
| `--quickwin-volume-min` | 100 | Lower bound for quick-win volume |
| `--quickwin-volume-max` | 5000 | Upper bound for quick-win volume |
| `--quickwin-difficulty-max` | 35 | Upper bound for quick-win difficulty |
| `--striking-min` | 4 | Lower bound for striking distance position |
| `--striking-max` | 20 | Upper bound for striking distance position |
| `--cluster-overlap-min` | 0.60 | Token-overlap threshold for cluster matching |
| `--aio-eligibility-min` | 60 | Score threshold for AIO eligibility flag |
| `--geo-opportunity-min` | 60 | Score threshold for GEO opportunity flag |
| `--volume-reference` | 100000 | Volume value mapped to score 100 |

Every parameter applied in a run is captured in `_metadata/run_config.json` for reproducibility.

## Validation and troubleshooting

The skill performs three validation passes during a run:

- Row-level: rejects rows missing `keyword`, rows with empty keywords, rows with type-coercion failures.
- File-level: rejects files with no header, files with inconsistent column counts, files larger than 500 MB.
- Corpus-level: flags duplicate `(keyword, source, country, language)` tuples and corpora dominated by one source (>90% from one source category).

Common issues and resolutions:

- «Source not recognized»: the CSV did not match any built-in tool signature. Supply `--mapping` with explicit column maps, or add the missing tool's signature.
- «Encoding detection failed»: the CSV is not UTF-8, UTF-8 with BOM, or Latin-1. Re-export from the source tool with UTF-8 selected.
- «Inconsistent separator»: the file uses different separators in different rows. Re-export or pre-process.
- «Methodology version mismatch on resume»: the JSON was produced by a different methodology version. Re-run from CSVs to apply the new methodology, or pin the skill to the older version.

Every validation failure produces a structured message naming the file, the row, the rule that fired, and a suggested fix. The skill never silently drops rows.

## Limitations

The skill is honest about its boundaries.

It does not query SERPs. Position data, when present in the CSV, informs analysis. The skill does not poll Google or any other engine.

It does not run machine learning models. The methodology is rule-based, transparent, and reproducible by hand for any single keyword. An analyst who disagrees with a score can recompute it on paper.

It does not crawl websites. AI crawler accessibility checks for `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, and `CCBot` are recommended actions, not automated checks.

It does not generate content. The recommendations identify what to create, update, or restructure; the writing remains with the content team.

It does not support full functionality outside English, French, German, and Spanish. CJK and RTL languages are detected and flagged but not analyzed at full quality.

It does not refresh itself. AI search algorithms shift faster than classical search; thresholds and routing recommendations age. Re-run quarterly when the engagement targets AI search visibility.

## A note on scope

The skill is precise about what it does and what it does not do. Reading the «Limitations» section above is the recommended starting point for any analyst evaluating whether the skill fits a particular engagement. A tool that is honest about its boundaries produces better outcomes than a tool that promises everything and delivers an opaque average.

## Why this skill exists

Keyword research has been treated for two decades as a list-production exercise. The list approach worked when search was monolithic, transactional, and dominated by a single index. It is now insufficient for three reasons.

First, the demand graph is now multilingual, multi-modal, and multi-temporal. A single sorted list collapses these dimensions into one ranking and loses information that determines whether a keyword should drive a new page, an update to an existing page, or a structural change.

Second, AI search experiences route a non-trivial share of queries through generative engines that operate on different signals from classical SERPs. A list optimized for classical retrieval rank misses the queries that flow through AI Overviews and through Perplexity, ChatGPT, Claude, and Gemini.

Third, vendor-neutrality is no longer a luxury. Most engagements pull data from at least three sources, and tying analysis to one vendor's metric definitions produces conclusions that change when the vendor changes. The skill's canonical schema is the contract that lets analysis survive vendor changes.

This skill is the working tool that turns these three observations into a deterministic, reproducible, defensible analysis. It is not the only way to do keyword intelligence well, but it is one way that has been put through the discipline of full documentation, full traceability, and full reproducibility. That discipline is the value, not any individual rule it encodes.

## Common workflows by engagement type

Different engagements lead to different reading orders for the same output artifacts.

A quarterly content sprint planning engagement sorts the enriched CSV by the quick-win composite, takes the top 30 to 50 rows, groups them by cluster, and produces a content commission list for the next quarter. The Markdown report supports this work in the «Quick wins» sub-section under «Top opportunities». The executive summary names the share of corpus reachable in one quarter so the leadership conversation has a concrete number.

A site architecture engagement sorts on the strategic composite, but starts the actual reading from the cluster analysis section in the Markdown report. The unit of decision is the cluster, not the individual keyword. A pillar-and-spoke plan reads the top 20 clusters by total volume, identifies the missing hubs (cluster heads with no client URL ranking), and proposes the page architecture that closes the gap.

A defensive engagement sorts on the AEO/defensive composite. The keywords with the highest scores are branded queries with cannibalization risk and high-AIO-eligibility brand-adjacent informational queries. The remediation often involves URL consolidation (collapsing two competing client pages into one) and citation-readiness work (passage extraction structure, schema markup, llms.txt visibility).

An AI search visibility engagement reads the «AIO and GEO routing» section first. The share of corpus in each routing path informs the strategic allocation: how much effort goes into classical SEO, how much into AIO-specific structure, how much into GEO-specific brand mention work and llms.txt. The routing path per keyword is exposed in the JSON for downstream automation.

A multi-language engagement runs the pipeline once per language to avoid language-specific thresholds being averaged across markets. Each language run produces its own output directory, and the gap analysis at the corpus level reflects the language-specific demand graph rather than a misleading mixed-language aggregate.

A migration or replatform engagement uses the cannibalization findings to identify URLs that should be merged before migration, and the freshness gap to identify pages that should be rewritten rather than redirected. The audit report and the methodology version metadata make the pre-migration baseline auditable for post-migration comparison.

## Operational notes for analysts

A few practices recur across engagements and are worth naming explicitly.

Run the audit before the analysis on any unfamiliar corpus. The five-second audit catches encoding mismatches, malformed CSVs, and source-distribution biases that would otherwise surface as confused output two minutes into a five-minute pipeline run.

Inspect the score distribution before reading individual rows. A skewed distribution where the top decile clusters around one source or one intent layer is a sourcing-bias signal, not a real opportunity profile. Return to Stage 1 and broaden the corpus.

Read the executive summary first when reviewing your own work. If the summary does not feel defensible, the corpus or the thresholds need work, not the writing of the summary. The summary is the test of finished work.

Read the gap analysis before the top-opportunities tables. Top-opportunity rankings reflect what is in the corpus. Gap analysis reflects what is missing. Strategy is more often shaped by what is missing than by what is already on the table.

Re-run quarterly when AI search visibility is part of the engagement objective. AI search algorithms shift faster than classical search, and routing recommendations age faster too. The freshness gap dimension is precisely the warning system for this drift.

Keep the methodology version visible. A report from six months ago was produced under a possibly different methodology version. The metadata directory and the version line in every report make this explicit. Comparing scores across versions without acknowledging the version difference produces false trends.

When a client team disagrees with a score, the disagreement should be specific: which signal, which weight, which threshold. The skill's transparency makes the disagreement productive: change the parameter, re-run, see the new result. A black-box scorer turns disagreement into argument.

## Where the documentation lives

The skill ships with twelve reference documents. Knowing which file answers which question saves time during analysis.

The nine operational references describe how the pipeline runs and what it produces:

- [references/methodology-overview.md](references/methodology-overview.md). Read this first if the analyst is new to the skill. Seven principles, the demand-graph reframe, the five forces shaping a query, the «what this skill is not» section.
- [references/workflow.md](references/workflow.md). Read this when planning a run. The seven-stage pipeline end to end, run-time considerations (memory, disk, CPU, time), the iteration loop.
- [references/input-normalization.md](references/input-normalization.md). Read this when ingesting an unfamiliar CSV. Canonical schema, per-tool column maps for Semrush, Ahrefs, GSC, Moz, Ubersuggest, generic CSVs, encoding and separator handling.
- [references/analysis-scopes.md](references/analysis-scopes.md). Read this to understand what each scope detects. Twelve scopes with rules, thresholds, edge cases, and dependency order.
- [references/scoring-formulas.md](references/scoring-formulas.md). Read this when interpreting or disputing scores. Four composite formulas with weights, confidence calculation, seven gap dimensions with priority formulas, three worked examples with full numeric breakdown.
- [references/aio-geo-optimization.md](references/aio-geo-optimization.md). Read this when the engagement targets AI search visibility. AI Overviews, generative engines, query fan-out, citation readiness, llms.txt, AI crawler accessibility.
- [references/multi-language.md](references/multi-language.md). Read this for multilingual engagements. Per-language stop words, intent markers, question detection, stemming for English, French, German, Spanish.
- [references/output-artifacts.md](references/output-artifacts.md). Read this when consuming the artifacts. Section order in the Markdown report, JSON schema, CSV column inventory, executive summary template, the run-comparison artifacts.
- [references/ecosystem-contract.md](references/ecosystem-contract.md). Read this when handing the canonical JSON to another skill or to downstream automation. The contract guarantees, the field-level handoff recipes for content, GEO, humanizing, and generic consumers, and how to detect a breaking change.

The three theoretical references defend the methodology against alternatives:

- [references/semantics.md](references/semantics.md). The semantic-search literature from LSA to dense retrieval, embedding models, the Google milestones. Read this when challenged on why the skill stays rule-based instead of using BERT-family embeddings.
- [references/clustering.md](references/clustering.md). The clustering literature (algorithmic families, SERP-based, embedding-based, hybrid, LLM-assisted), quality evaluation metrics, the roadmap toward an embedding-augmented v2.
- [references/entity-and-topical-authority.md](references/entity-and-topical-authority.md). Entity SEO, ten named practitioners, knowledge graph integration, AEO and GEO academic research with paper citations, brand SERP optimization.

The three theoretical references are not required for operational use. They become essential when the analyst has to defend the methodology in a senior review, when planning the hybrid v2 documented in clustering.md, or when citing the relevant academic and patent literature inside client deliverables.

Together they bring the skill to the level of a defensible reference rather than a black-box tool. An analyst who reads all twelve files end to end has both the operating knowledge to run the pipeline and the conceptual depth to argue for the design choices in front of a senior reviewer.

## Methodology principles, in summary

The skill rests on seven principles applied as a set, not selectively. Detailed reasoning for each is in [references/methodology-overview.md](references/methodology-overview.md).

1. Keywords are observations, not the demand itself. Volume figures are delayed and partial measurements with sampling bias toward English markets and transactional verticals. Treating a number as the demand itself produces strategy that mistakes what is measurable for what actually matters.

2. Structure beats volume. A high-volume keyword inside a fragmented topic graph is worth less than a medium-volume keyword inside a coherent cluster. Pages designed around clusters reinforce each other through internal links and topical authority signals.

3. Vendor-neutrality is a methodological commitment. The graph of demand exists independently of any vendor's index. Tying analysis to one vendor's metric definitions produces conclusions that change when the vendor changes its methodology.

4. Reproducibility separates intelligence from extraction. Two analysts running the same inputs through the same parameters must produce the same scoring and recommendations. Every formula, threshold, and rule is documented for that reason.

5. Decision-grade outputs require traceable inputs. Every keyword in a final report carries its provenance. Without traceability, output cannot be audited, and audit is what separates a recommendation from a guess.

6. Intent stratification beats intent labeling. The skill keeps intent as a four-axis vector (query type, funnel stage, modality, temporal) instead of compressing the signal into one label.

7. Priority and confidence are two scores, not one. A high composite with low confidence is a research target. The same composite with high confidence is an action target. Conflating them produces over-confident roadmaps.

## Project metadata

- Tier: POWERFUL
- Version: 1.0.0
- License: MIT
- Author: Mario Montanari, mariomontanari.it
- Methodology version: 1.0.0
- Cutoff: April 2026
- Dependencies: Python 3.7+ standard library only
- Compatibility: Claude Code, OpenCode, Codex (any environment supporting Anthropic skill format)

For the full README intended for distribution, see [README.md](README.md). For the LICENSE, see [LICENSE](LICENSE).
