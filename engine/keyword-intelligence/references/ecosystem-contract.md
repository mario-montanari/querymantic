# Ecosystem contract

## Contents

- Why analysis.json is a contract
- Field stability tiers
- The four consumer categories
- Handoff recipes
  - Brief a cluster for content
  - Route a keyword set for GEO and AI search
  - Hand prose to a humanizing skill
  - Export to a spreadsheet or database
- Detecting a breaking change
- Boundaries

## Why analysis.json is a contract

The canonical `analysis.json` is the single source of truth for a run. The four human-facing artifacts (the Markdown report, the enriched CSV, the executive summary, the content briefs) are projections of it. Because the skill is deterministic and the schema is stable within a methodology version, `analysis.json` can be treated as a contract: another skill, or a downstream script, can read documented fields and rely on their shape and meaning across runs.

This is what makes the skill a clean front end for a larger pipeline. Keyword intelligence answers "what demand exists, how is it structured, and where is the client missing". Other skills answer "what to write", "how to earn AI citations", and "how to make the prose read like a person wrote it". The contract is the seam between them.

The methodology version is the contract number. It lives in `run_metadata.methodology_version` and in `_metadata/methodology_version.txt`. A consumer that pins to a methodology version knows the schema will not shift under it. The bump rules are in [output-artifacts.md](output-artifacts.md): patch never changes scores, minor may shift scores, major may change the schema.

## Field stability tiers

Not every field carries the same guarantee. Consumers should know which tier a field sits in before depending on it.

Stable. Present in every run, same shape, same meaning within a methodology version. Safe to depend on: `run_metadata`, `corpus_summary` (including `demand_opportunity_score`, `aio_eligibility_share`, `geo_opportunity_share`), the per-keyword `keyword`, `language`, `metrics`, `scores` (the four composites with `score` and `confidence`), and the `scopes` object keys. The `clusters` array shape (`head`, `head_index`, `members`, `size`, `volume_total`, `dominant_intent`) is stable.

Advisory. Present but content-dependent. The `evidence` arrays inside each scope are human-readable explanations, useful for display but not meant to be parsed. Scope `score` values are stable in range (0 to 100 or 0 to 1 depending on the scope) but their exact value can shift with a minor version.

Derived elsewhere. Some fields a consumer might expect are not in the JSON because they are computed at artifact-write time. The per-keyword recommended action class (`create`, `update`, `restructure`, `monitor`, `ignore`) is emitted in the enriched CSV by the report stage, not stored in `analysis.json`. A JSON consumer that needs the action class reads it from `keywords_enriched.csv`, or recomputes it from the scopes and scores.

## The four consumer categories

The contract is written for categories of consumer, not for specific skills, so it stays useful whether or not a given skill is installed. The skill names below are examples of each category in the Claude ecosystem.

Content and topical-authority skills. A skill that drafts content or assesses content quality and E-E-A-T (for example, a content skill such as seo-content) consumes the cluster structure and the content briefs. It needs the cluster head and members, the dominant intent, the question-shaped keywords, and the per-keyword intent vector to decide page format and outline.

GEO and AI-search skills. A skill that optimizes for AI Overviews and generative-engine citations (for example, a GEO skill such as seo-geo) consumes the AIO eligibility and GEO opportunity scopes, the corpus-level AIO and GEO shares, and the AEO/GEO gap. It needs to know which keywords route through AI search experiences and where the client has no visibility.

Humanizing skills. A skill that strips AI-writing patterns from prose (for example, a humanizing skill such as humanizer or avoid-ai-writing) consumes the text artifacts, not the JSON: it runs on `report.md` and on expanded content briefs before client delivery. The contract here is the prose, produced under the skill's own no-AI-pattern discipline, ready for a second pass.

Generic automation. A dashboard, a CMS importer, or a sync to Notion, Airtable, or Google Sheets consumes the enriched CSV for tabular work and `analysis.json` for the full structured state. The CSV is the low-friction path; the JSON is the complete one.

## Handoff recipes

Each recipe names the exact fields to read. Field paths use dot notation into `analysis.json`.

### Brief a cluster for content

1. Pick a cluster from `clusters[]`, typically sorted by `clusters[i].volume_total`.
2. Read `clusters[i].head` (the pillar keyword), `clusters[i].dominant_intent`, and `clusters[i].members` (an array of integer indices into `keywords[]`).
3. For each member index `m`, read `keywords[m].keyword`, `keywords[m].metrics.volume`, `keywords[m].enrichment.intent_vector.query_type`, and `keywords[m].scopes.question_paa.label` (values include `question`, `question_and_paa`, `paa_only`, `neither`) to collect the questions the page must answer.
4. Hand the head, the members, the dominant intent, and the questions to the content skill. The bundled `content_briefs.md` already assembles this skeleton for the top clusters; a content skill can start from that file and expand it.

### Route a keyword set for GEO and AI search

1. For each keyword, read `keywords[k].scopes.aio_eligibility.label` (values: `confirmed`, `eligible`, `possibly_eligible`, `not_eligible`) and `keywords[k].scopes.geo_opportunity.label` (values: `dual`, `geo_only`, `aio_only`, `neither`).
2. Treat the `geo_opportunity.label` as the routing path: `dual` keywords need both AI Overview structure and generative-citation work, `geo_only` need crawl accessibility and citation readiness, `aio_only` need passage extraction on classical rank, `neither` are classical SEO.
3. Read `corpus_summary.aio_eligibility_share` and `corpus_summary.geo_opportunity_share` for the corpus-level allocation.
4. Read `gaps.aeo_geo_gap` (the count and a sample list of AI-eligible keywords with no client visibility) to target the keywords where AI search routes users to other sources. Hand this set to the GEO skill.

### Hand prose to a humanizing skill

1. Run the analysis to produce `report.md` and, on request, expanded content briefs.
2. Pass those Markdown files to the humanizing skill. The contract is the text, not the JSON.
3. The skill's output replaces the prose in the delivery package. The scores and tables, which are numeric and not prose, pass through unchanged.

### Export to a spreadsheet or database

1. For tabular consumers, use `keywords_enriched.csv`. It carries the canonical metrics, the intent vector, the cluster assignment, the scope flags, the four composite scores and confidences, and the `recommended_action_class`, one row per keyword.
2. For consumers that need the full structure (cluster membership, gap findings, run metadata), use `analysis.json`. Map `keywords[]` to rows and `clusters[]` to a related table joined on the member indices.

## Detecting a breaking change

A consumer should fail loudly, not silently, when the contract shifts.

1. Read `run_metadata.methodology_version` on every ingest.
2. Compare it to the version the consumer was built against. Equal major and minor: safe. Different minor: scores may have shifted, re-validate score-dependent logic. Different major: the schema may have changed, do not ingest without review.
3. For run-over-run work, the `compare.py` tool already enforces this: it flags a methodology mismatch between the baseline and the current run rather than reporting score deltas that conflate a data change with a method change.

A consumer that pins a methodology version and checks it on ingest will never be surprised by a schema change.

## Boundaries

The skill produces the contract. It does not call the content, GEO, or humanizing skills, and it does not orchestrate a pipeline. The handoff is a file on disk that another skill, or the analyst, or Claude reads. Keeping the seam explicit is deliberate: it preserves the skill's vendor-neutrality and reproducibility, and it lets each downstream skill evolve on its own schedule. The contract is stable; the orchestration is the analyst's to compose.
