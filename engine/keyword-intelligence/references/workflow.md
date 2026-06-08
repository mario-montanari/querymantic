# Workflow

## Contents

- The seven-stage pipeline
- Stage 1. Sourcing
- Stage 2. Normalization
- Stage 3. Enrichment
- Stage 4. Scope analysis
- Stage 5. Scoring
- Stage 6. Gap analysis
- Stage 7. Output generation
- The iteration loop
- Comparing runs across time
- Run-time considerations
- A complete pass: what an analyst does

## The seven-stage pipeline

The skill processes a keyword corpus through seven sequential stages. Each stage produces a verifiable intermediate state that the next stage consumes.

```
[CSV exports]
      ↓
[Stage 1] Sourcing       → keyword corpus with provenance
      ↓
[Stage 2] Normalization  → canonical schema, sources reconciled
      ↓
[Stage 3] Enrichment     → derived metrics, intent vector, language tag
      ↓
[Stage 4] Scope analysis → twelve analytical lenses applied per keyword
      ↓
[Stage 5] Scoring        → composite scores + confidence per keyword
      ↓
[Stage 6] Gap analysis   → seven gap dimensions evaluated against the corpus
      ↓
[Stage 7] Output         → five artifacts written to disk
```

The pipeline is strictly sequential. A failure in Stage N blocks Stages N+1 through 7. This is intentional: forcing failures to surface early prevents downstream artifacts that look complete but rest on a broken foundation.

## Stage 1. Sourcing

Sourcing assembles the raw keyword corpus from one or more inputs. Six source categories are recognized.

### Seed keywords

A small set of starter terms (typically 5 to 30) provided by the analyst or extracted from the client's existing taxonomy. Seeds anchor the corpus to the client's domain and prevent drift toward generic high-volume queries that have nothing to do with the client's business.

### Algorithmic expansion

Tool-generated suggestions derived from search-engine autocomplete, related searches, and «people also search for» boxes. Algorithmic expansion captures the lateral semantic space around the seeds. Quality varies by tool and language; treat the output as raw material requiring filtering, not as a finished list.

### Competitor extraction

Keywords for which one or more competitor domains rank in the top 100. Competitor extraction reveals the demand the client is missing and identifies coverage that other actors already staff. The CSV provenance must include the competitor domain so the analyst can interpret strength: a keyword owned by a domain ranking position 3 with a DR of 80 has different operational weight than one owned by a brand ranking position 90 with a DR of 25.

### Internal data (GSC, GA4)

Keywords for which the client's own domain already receives impressions and clicks. Internal data has the highest reliability of any source because it reports actual user behavior on the actual domain. Sampling and low-volume thresholds apply but do not substitute for the absence of bias toward English markets common in commercial tools.

### Linguistic expansion

Morphological and lexical variations of seeds and discovered keywords: plurals, gender variants where the language has them, synonyms, regional spellings, abbreviations, and natural-language reformulations of the same intent. Linguistic expansion is documented per language in [multi-language.md](multi-language.md) for English, French, German, and Spanish.

### Generative AI sourcing

Conversational queries, query fan-out variations, and long-tail formulations characteristic of how users phrase requests to ChatGPT, Perplexity, Claude, Gemini, and AI Overviews. These queries rarely surface in classical keyword tools because they have low individual volume and high specificity. Their cumulative weight in AI search routing is large enough to matter for any portfolio that targets visibility in generative engines. Treatment is documented in [aio-geo-optimization.md](aio-geo-optimization.md); the academic background on query fan-out and on AI search citation behavior is in [entity-and-topical-authority.md](entity-and-topical-authority.md).

### Provenance metadata

Every keyword retains the source category and (where applicable) the originating CSV file and row number. Without provenance, downstream conflicts cannot be resolved. With provenance, a divergence in volume between two sources becomes an interpretable signal rather than noise.

## Stage 2. Normalization

Normalization converts heterogeneous input formats into the canonical schema defined in [input-normalization.md](input-normalization.md). Three operations occur.

Each tool's column set maps to canonical column names: `keyword`, `volume`, `difficulty`, `cpc`, `position`, `serp_features`, `traffic_potential`, `intent_label_raw`, `language`, `country`, `source`. Missing columns are tolerated; impossible mappings are flagged and reported.

Identical keywords from multiple sources are reconciled but never collapsed into one row. They are preserved with source attribution and surfaced as a `multi_source` flag. The reasoning lives in [methodology-overview.md](methodology-overview.md): divergence is signal, not noise.

Validation runs encoding consistency (UTF-8 enforced), separator detection (comma, semicolon, tab), header presence checks, and sanity checks on numeric ranges (negative volumes flagged, difficulty values above 100 flagged, position values above 100 flagged). Any failure stops the pipeline with a remediation message naming the file and the offending row.

## Stage 3. Enrichment

Enrichment derives secondary attributes that scope analysis and scoring depend on. Five derivations apply.

Language detection runs when the language column is absent or empty. The skill infers the language from character set, common stop words, and morphological markers; rules per language are in [multi-language.md](multi-language.md).

Intent vector classification produces a four-axis vector (query type, funnel stage, modality, temporal layer) computed from the keyword string and, when available, the SERP features. Classification rules are in [analysis-scopes.md](analysis-scopes.md).

Branded versus non-branded segmentation runs a regex test against the client's brand list and known variations. Branded keywords are flagged but never excluded because they inform several scopes (cannibalization risk, defensive scoring, intent stratification).

Question detection tests for question-shaped keywords using interrogative pronouns in each supported language, sentence-final question marks where present, and common question patterns in conversational AI input.

Token statistics compute word count, character count, and head-versus-tail classification (1 to 2 words = head, 3 to 4 = mid, 5+ = long tail).

Enrichment is fast and deterministic. Every derived attribute carries a confidence score from 0 to 1, so downstream stages can weight uncertain enrichments appropriately rather than treating low-confidence inferences as ground truth.

## Stage 4. Scope analysis

Twelve analytical scopes apply to every keyword. The full taxonomy and the rules for each scope live in [analysis-scopes.md](analysis-scopes.md). The conceptual ground supporting the scopes is documented in [semantics.md](semantics.md) for intent and language-related scopes and in [entity-and-topical-authority.md](entity-and-topical-authority.md) for branded, content-gap, and entity-related scopes. The scopes are:

1. Intent classification
2. Cluster assignment
3. AIO eligibility
4. GEO opportunity
5. Quick wins
6. Cannibalization risk
7. Content gap
8. Striking distance
9. Branded versus non-branded segmentation
10. Questions and PAA
11. Seasonality
12. Long tail

Each scope produces a categorical or ordinal label, a confidence score, and (when applicable) a list of related keywords from the same corpus. The output of Stage 4 is a per-keyword record with twelve scope evaluations attached, ready for scoring in Stage 5.

## Stage 5. Scoring

Scoring computes four composite scores per keyword: main, quick-win, strategic, and AEO/defensive. Each composite is a weighted aggregate of normalized signals; the formulas, the weights, and the rationale for each weight are in [scoring-formulas.md](scoring-formulas.md).

Scoring also produces a confidence score per keyword based on input completeness (how many canonical columns were populated), source reliability (internal data ranks higher than algorithmic expansion), and enrichment certainty (how confident were the inferences in Stage 3). A high composite with low confidence is preserved with a flag rather than promoted to the top of the priority list. The analyst sees the high composite, sees the flag, and decides.

## Stage 6. Gap analysis

Gap analysis evaluates the corpus along seven dimensions:

1. Keyword gap (queries the client's domain does not target at all)
2. Content gap (intents the existing content does not address)
3. Intent gap (intent layers underserved across the portfolio)
4. SERP feature gap (features the client's pages cannot win in current shape)
5. AEO/GEO gap (queries routing through AI engines without client visibility)
6. Entity gap (entities the corpus references that the client does not own)
7. Freshness gap (queries with temporal sensitivity not addressed by recent content)

Gap analysis runs at the corpus level, not the keyword level. Its output is a list of gap findings, each with a priority rating and a recommended action class (create, update, restructure, ignore). Detailed dimension definitions and the formulas that produce priority ratings are in [scoring-formulas.md](scoring-formulas.md).

## Stage 7. Output generation

Stage 7 writes five artifacts to disk:

- A Markdown report (human-readable, structured for client delivery)
- A JSON file (machine-readable, full intermediate state plus final scores)
- An enriched CSV (the original keyword corpus plus all derived columns)
- A TXT executive summary (one page, decision-focused)
- Per-cluster content briefs (editorial brief skeletons for the top clusters)

The structure of each artifact, including section order and required fields, is documented in [output-artifacts.md](output-artifacts.md). The five artifacts are produced from the same intermediate JSON state, ensuring consistency: the executive summary cannot disagree with the Markdown report, and the CSV cannot misalign with the JSON.

## The iteration loop

A first pass through the seven stages rarely produces the final analysis. Three iteration triggers are common.

Sourcing gaps surface when the first pass reveals that an intent layer is underrepresented in the corpus. The analyst extracts additional seeds, runs Stage 1 again, and re-runs Stages 2 to 7 on the expanded corpus.

Threshold tuning becomes necessary because the first pass uses default thresholds for difficulty, branded detection, and intent classification. The analyst inspects the output, identifies cases where defaults misclassify, adjusts thresholds, and re-runs Stages 4 to 7 on the same normalized corpus.

Scope refinement applies when the first pass surfaces that one scope (typically cluster assignment or content gap) needs domain knowledge that the rule-based default does not capture. The analyst supplies a custom mapping or rule set, then re-runs Stages 4 to 7.

The pipeline supports stage-level resumption: re-running from Stage 4 reuses the normalized corpus from Stage 2 and the enriched corpus from Stage 3 without re-reading the source CSVs. This makes iteration cheap.

## Comparing runs across time

The iteration loop above improves a single analysis. A separate concern is tracking what changed between two analyses run weeks or months apart, typically a baseline at the start of an engagement and a follow-up after a quarter of work. This is what `compare.py` does. It is not a pipeline stage; it is a standalone tool that reads two canonical JSON states and reports the movement between them.

```bash
python scripts/compare.py \
  --baseline output/q1/analysis.json \
  --current output/q2/analysis.json \
  --output-dir output/q1_vs_q2/
```

The comparison reports six things: the corpus-level headline (Demand Opportunity Score delta, AIO and GEO share deltas, corpus size), quick-win movement (captured, still climbing, still open, newly surfaced, regressed), composite score movement (mean delta per composite and per-keyword risers and fallers on the main composite), position movement (top climbers and decliners for keywords with a position in both runs), gaps opened and closed, and corpus membership (keywords added and dropped).

Two design points matter for interpretation. First, keywords are matched across runs by their normalized string (use `--match-key keyword-lang` for multilingual corpora). When the same keyword appears from several sources, the comparison keeps one representative per key, chosen deterministically by highest volume, so the representative does not flip between runs unless the data changed. Second, the comparison is only valid within a methodology version. A run produced under a different version is flagged, because a score delta across versions conflates a data change with a method change. Re-run the baseline under the current version before trusting cross-version deltas.

The capture paradox is worth naming: realizing an opportunity removes it from the opportunity-density signals that feed the Demand Opportunity Score. A quarter that captures several striking-distance keywords can leave the headline score flat while the per-keyword tables show real progress. Read the captured-quick-win count and the position climbers, not just the headline, when judging whether a quarter moved the needle.

The artifact structure (`comparison.md` and `comparison.json`) is documented in [output-artifacts.md](output-artifacts.md).

## Run-time considerations

The skill runs offline on a local machine. Four runtime characteristics shape practical use.

Memory holds the full keyword corpus and all derived state. The practical limit on a 16 GB machine is around 250,000 keywords; above that, batch the corpus by language or by source.

Disk usage scales with corpus size. The skill writes intermediate state to a workspace directory between stages; budget roughly 500 MB per 100,000 keywords for full intermediate state plus the five output artifacts.

CPU is single-threaded by default for reproducibility. Multi-process options exist for sourcing and enrichment but stay off by default; turning them on requires confirming that the deterministic ordering of records is preserved.

Time on a modern laptop: a 50,000-keyword corpus completes the full pipeline in 2 to 5 minutes. Stage 4 (scope analysis) dominates the budget because it applies twelve evaluations per keyword.

## A complete pass: what an analyst does

The methodology compresses to seven actions in a typical client engagement.

1. Collect CSV exports from the tools the client subscribes to. Three to five sources is typical: a keyword-research tool, a backlink-and-SERP tool, GSC, and one or two complementary sources for breadth.
2. Run Stage 1 to assemble the corpus. Inspect the source-category distribution. If one category dominates (say, 90% from algorithmic expansion), plan an expansion before continuing.
3. Run Stages 2 and 3. Read the normalization report. Resolve encoding mismatches, schema gaps, and obvious anomalies before proceeding. A clean Stage 3 output is the foundation for everything else.
4. Run Stages 4 and 5. Read the score distribution by source and by intent layer. If the top decile is dominated by one source or one intent layer, suspect a sourcing bias and return to Stage 1.
5. Run Stage 6. Read the gap findings. Validate against the client's stated priorities and against the analyst's own qualitative knowledge of the market.
6. Run Stage 7. Read the executive summary first; if it does not feel defensible to the analyst, the corpus or the thresholds need work, not the writing of the summary.
7. Iterate one or two more passes until the executive summary reads as something the analyst can present without internal qualification.

The seventh action is the test of finished work: a methodology that does not produce defensible recommendations is a methodology with a hidden assumption to find.
