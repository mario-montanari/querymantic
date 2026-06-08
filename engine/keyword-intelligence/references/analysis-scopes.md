# Analysis scopes

## Contents

- The twelve scopes
- Scope output format
- 1. Intent classification
- 2. Cluster assignment
- 3. AIO eligibility
- 4. GEO opportunity
- 5. Quick wins
- 6. Cannibalization risk
- 7. Content gap
- 8. Striking distance
- 9. Branded versus non-branded
- 10. Questions and PAA
- 11. Seasonality
- 12. Long tail
- Default thresholds reference
- Scope dependencies and order

## The twelve scopes

The skill applies twelve analytical lenses to every keyword in the canonical corpus. Each scope is independent in its rule set but shares the same canonical input, the same provenance metadata, and the same confidence-scoring discipline. The full taxonomy, in execution order, is:

1. Intent classification
2. Cluster assignment
3. AIO eligibility
4. GEO opportunity
5. Quick wins
6. Cannibalization risk
7. Content gap
8. Striking distance
9. Branded versus non-branded
10. Questions and PAA
11. Seasonality
12. Long tail

Order matters because some scopes consume outputs of earlier scopes. Cluster assignment uses intent classification as a tie-breaker. Quick wins read the difficulty and the volume but also the AIO eligibility (an AIO-eligible keyword that rounds out a cluster is a different kind of quick win from a generic one).

## Scope output format

Every scope produces a record with a fixed shape, regardless of internal logic.

```
{
  "scope": "intent_classification",
  "label": "informational",
  "confidence": 0.86,
  "evidence": ["question shape", "no commercial markers", "PAA in SERP features"],
  "related_keywords": ["..."],
  "parameters_used": {"intent_question_threshold": 0.6}
}
```

The `label` is categorical or ordinal. The `confidence` is a float from 0 to 1, derived per scope according to documented rules. The `evidence` array names the signals that contributed to the label. The `related_keywords` array, when populated, lists keywords from the same corpus that the scope identifies as connected. The `parameters_used` block records the exact threshold values applied, so the analysis is reproducible even if defaults change in a later version.

## 1. Intent classification

### What it captures

The reason behind the query, expressed as a four-axis vector rather than a single label. The four axes are query type (informational, navigational, transactional, commercial investigation), funnel stage (awareness, consideration, decision, post-purchase), modality (typed, voice, conversational AI, ambient), and temporal layer (evergreen, seasonal, event-driven, breaking). The semantic background that makes intent classification feasible (contextual embeddings, RankBrain, BERT, MUM, query understanding) is documented in [semantics.md](semantics.md).

### Inputs

`keyword`, `serp_features` (when available), `intent_label_raw` (when supplied by the source tool, used as a corroborating signal but not as ground truth), `position` and `clicks` from GSC (when available, used to tighten confidence on commercial signals).

### Method

Query type is determined by a rule pipeline applied in order:

1. If the keyword starts with an interrogative pronoun (in any supported language: `what`, `how`, `why`, `where`, `when`, `who`, `which`, `comment`, `pourquoi`, `wie`, `was`, `warum`, `cómo`, `por qué`, and so on) → informational candidate, weight 0.7.
2. If the keyword contains transactional markers (`buy`, `price`, `cheap`, `discount`, `cost`, `acheter`, `prix`, `kaufen`, `precio`, `comprar`) → transactional candidate, weight 0.8.
3. If the keyword contains commercial-investigation markers (`best`, `top`, `vs`, `versus`, `review`, `comparison`, `meilleur`, `bester`, `mejor`) → commercial candidate, weight 0.7.
4. If the keyword is the brand name plus a navigational marker (`login`, `account`, `support`, `connexion`, `anmeldung`, `iniciar sesión`) → navigational candidate, weight 0.9.
5. If `serp_features` contains `featured_snippet`, `paa`, or `ai_overview` → informational lift, +0.1.
6. If `serp_features` contains `shopping`, `local_pack` → transactional lift, +0.1.
7. If `intent_label_raw` matches the candidate type → +0.1; if it disagrees → -0.05.

The candidate with the highest aggregated weight wins. Ties resolve by source priority (GSC + SERP features > tool-supplied label > regex markers).

Funnel stage maps from query type with adjustments: informational → awareness or consideration depending on token specificity; commercial → consideration; transactional → decision; navigational → consideration or post-purchase depending on whether the keyword contains «support» or similar markers.

Modality detection identifies typed (the default), voice (long natural-language phrasing, presence of fillers like `please`, `near me`), conversational AI (multi-clause queries, presence of «can you», «tell me about», imperative forms), and ambient (rare; queries with explicit device or context markers).

Temporal layer identifies evergreen (no temporal markers), seasonal (month names, season names, recurring event markers like «christmas», «black friday»), event-driven (year markers like `2026`, named events like `cop30`, `world cup 2026`), and breaking (rare in static CSV exports; flagged when the keyword contains markers like `live`, `today`, `latest`).

### Output

A four-element vector with confidence per axis. The composite intent label exposed in the report is the query type, but the underlying vector is preserved in JSON for the scopes that consume it (cluster assignment, AIO eligibility, GEO opportunity).

### Edge cases

Mixed-intent queries (e.g., «best running shoes 2026») receive multiple non-zero weights and a flag in `evidence` noting the ambiguity. The analyst sees the ambiguity and decides whether to treat the keyword as commercial-decision (most likely) or as a hybrid.

## 2. Cluster assignment

### What it captures

Groups of semantically related keywords that should be addressed by the same content asset (a hub page, a pillar, a satellite). The cluster is the unit on which content architecture decisions are made.

For the theoretical foundations of clustering (algorithmic families, SERP-based versus embedding-based versus hybrid approaches, distance metrics, quality evaluation, the roadmap toward an embedding-augmented v2), see [clustering.md](clustering.md). The algorithm below is the deterministic three-pass approach the skill implements; clustering.md explains why this choice was made and what its trade-offs are.

### Inputs

`keyword`, `parent_topic` (when supplied by source tool), token statistics from Stage 3 enrichment, intent vector from scope 1.

### Method

The skill uses a deterministic three-pass clustering algorithm:

Pass 1: Seed clusters from `parent_topic` values when present. Every distinct `parent_topic` becomes a candidate cluster with a head keyword (the highest-volume keyword sharing that parent).

Pass 2: For keywords without a `parent_topic`, attempt assignment to existing clusters by token overlap. A keyword joins a cluster if it shares at least 60% of significant tokens (excluding stop words for the keyword's language) with the cluster head, AND the intent vectors are compatible (same query type and same funnel stage, or one is a clear specialization of the other).

Pass 3: Keywords still unassigned form new clusters by mutual overlap. The algorithm picks the unassigned keyword with the highest volume as the head of a new cluster, then attempts to attach other unassigned keywords with shared significant tokens of at least 60%.

Token significance: a token is significant if it is not in the stop-word list for the keyword's language and has length ≥ 3 characters. Stemming uses a light-touch suffix stripping rule per language documented in [multi-language.md](multi-language.md).

### Output

`label` is the cluster head keyword. `confidence` reflects how clean the cluster is (high when most members share parent_topic; lower when the cluster was assembled through token overlap only). `related_keywords` lists the cluster members.

Each cluster is also tagged with a `cluster_size` count, a `cluster_volume_total` sum, and a `cluster_intent_dominant` label. These corpus-level cluster attributes feed the gap analysis in Stage 6.

### Edge cases

Singleton clusters (one keyword, no overlap with anything else) are preserved with a `singleton: true` flag. They often represent emerging or unique-intent queries worth a dedicated page.

Mega-clusters (more than 200 keywords) are split into sub-clusters by intent vector before being reported. A 500-keyword cluster on «running shoes» that contains awareness, consideration, and decision intents is more useful split into three sub-clusters.

## 3. AIO eligibility

### What it captures

Likelihood that the keyword triggers an AI Overview in Google Search and the related likelihood that it routes through generative engines (Perplexity, ChatGPT search, Claude search, Gemini).

### Inputs

`keyword`, `serp_features`, intent vector from scope 1, token statistics.

### Method

The skill computes an AIO eligibility score from 0 to 100 using four signals.

If `serp_features` already contains `ai_overview`, the keyword is confirmed eligible: score 100, confidence 1.0. No further computation needed.

When the SERP feature is absent, the skill evaluates four pattern signals:

- Informational intent type → +30
- Question shape (any interrogative pronoun, ends with `?`) → +25
- Multi-clause structure (≥2 commas, conjunctions like «and», «or», «but», «vs») → +15
- Long-tail (≥5 tokens) → +10
- Comparison or how-to markers (`how to`, `comment`, `wie`, `cómo`; `vs`, `versus`, `compared to`) → +20

The signals are summed and capped at 90 (to leave a confidence margin below confirmed eligibility). Scores above 60 mark the keyword as AIO-eligible with the documented signal set in `evidence`. Scores between 40 and 60 are flagged as «possibly eligible» and recommended for manual SERP inspection. Scores below 40 are not flagged.

### Output

`label` is one of `confirmed`, `eligible`, `possibly_eligible`, `not_eligible`. `confidence` is high for `confirmed` (1.0) and decreases as scores approach the threshold boundaries.

### Edge cases

Keywords with mixed signals (transactional intent but question shape, e.g., «how much does X cost») are scored on the dominant signal but flagged in `evidence`. The composite scoring in Stage 5 reads the flag and weights AIO eligibility lower for mixed cases.

## 4. GEO opportunity

### What it captures

Likelihood that the keyword represents a generative-engine optimization (GEO) opportunity, distinct from AIO eligibility. AIO eligibility is about whether Google shows an AI Overview; GEO opportunity is about whether the keyword is the kind of query users ask generative engines (Perplexity, ChatGPT, Claude, Gemini) where citation readiness, llms.txt presence, and brand mention signals determine visibility.

### Inputs

`keyword`, intent vector, AIO eligibility output, token statistics.

### Method

GEO opportunity score combines four factors:

- Conversational shape (full sentences, presence of «how», «what», «why», «can you», imperative forms): +25
- Long-tail length (≥6 tokens): +20
- Multi-step or comparative structure: +20
- Informational or commercial-investigation intent: +20
- Recent or evergreen temporal layer (excluding navigational and pure transactional): +15

Scores above 60 mark the keyword as a GEO opportunity. The skill cross-references with AIO eligibility: keywords scoring high on both are routed to a `dual` recommendation (optimize for both Google AI Overviews and generative engine citations); keywords high on GEO but low on AIO are routed to `geo_only` (likely missed by Google AI Overviews but appearing in third-party generative engines). Detailed treatment of each route is in [aio-geo-optimization.md](aio-geo-optimization.md).

### Output

`label` is one of `dual`, `geo_only`, `aio_only`, `neither`. `confidence` reflects signal strength.

## 5. Quick wins

### What it captures

Keywords reachable inside one quarter of focused effort, defined by an attainable difficulty paired with a volume worth pursuing.

### Inputs

`keyword`, `volume`, `difficulty`, `position` (when available), intent vector, AIO eligibility.

### Method

A keyword is a quick win if all of the following hold by default:

- `volume` ≥ 100 and ≤ 5,000 (configurable via `--quickwin-volume-range`)
- `difficulty` ≤ 35 (configurable via `--quickwin-difficulty-max`)
- If `position` is available: position is empty (no current ranking) or position is between 11 and 30
- Intent is informational, commercial-investigation, or transactional (navigational excluded)
- AIO eligibility is `confirmed`, `eligible`, or `not_eligible` (queries with `possibly_eligible` are excluded by default to avoid uncertainty)

### Output

`label` is `quick_win` or `not_quick_win`. `confidence` reflects how cleanly the keyword meets the criteria; a difficulty of 34 is a less confident quick win than a difficulty of 15.

### Edge cases

Quick wins inside a coherent cluster (assigned in scope 2) are flagged as `cluster_quick_win` and weighted higher in the scoring stage because they reinforce architecture rather than producing orphan pages. Isolated quick wins are still flagged but with a note that they require their own page with no internal authority feed.

## 6. Cannibalization risk

### What it captures

Cases where two or more pages on the same domain target the same query and compete with each other in SERPs, splitting authority and click-through.

### Inputs

`keyword`, `position`, `competitor_url` (when present and pointing to the client's domain via the `--client-domain` parameter), GSC data when available.

### Method

Cannibalization detection requires the analyst to mark which `competitor_url` values belong to the client's domain (typically by passing `--client-domain example.com`). The skill then runs three checks:

1. Same keyword appears with two distinct client URLs in the corpus.
2. Same keyword appears in GSC with multiple landing pages reporting impressions.
3. Same keyword has both an existing client URL ranking and another client URL appearing in the SERP features list.

Any of the three triggers a cannibalization flag.

### Output

`label` is `cannibalized` or `no_risk`. `evidence` lists the competing URLs. `confidence` is high when GSC data confirms the case (multiple landing pages with impressions) and lower when the signal comes from rank-tracking exports only.

### Edge cases

Branded queries are excluded from cannibalization detection by default because the brand site legitimately targets the brand name across multiple pages. Override with `--cannibalization-include-branded`.

## 7. Content gap

### What it captures

Keywords for which competitor domains rank but the client's domain does not.

### Inputs

`keyword`, `position`, `competitor_url`, `--client-domain` parameter.

### Method

A keyword is in the content gap if:

- At least one competitor URL ranks in the top 30 for the keyword
- No client URL ranks in the top 100 for the keyword (or `position` is empty)
- The keyword's intent is reachable for the client (excludes pure navigational queries to a competitor's brand)

The skill then prioritizes gap keywords by a composite of competitor strength (mean DR of ranking competitors when `domain_rank` is available), volume, and cluster membership (gap keywords inside an underserved cluster are prioritized higher).

### Output

`label` is `content_gap` or `not_in_gap`. `related_keywords` lists other content-gap keywords in the same cluster, helping the analyst plan the gap fill as a coordinated content commission rather than as scattered pages.

## 8. Striking distance

### What it captures

Keywords where the client's domain ranks just outside the top page (positions 4 to 20) and a focused intervention can move the page into top 3.

### Inputs

`keyword`, `position`, `volume`, `difficulty`.

### Method

A keyword is in striking distance if:

- `position` is between 4 and 20 (configurable via `--striking-distance-range`)
- `volume` ≥ 50
- The keyword has a non-empty `competitor_url` confirmed as the client's domain

Within striking distance, the skill sub-segments by effort tier:

- Position 4 to 7: `top_page_climb` (typically a content refresh and on-page tightening is enough)
- Position 8 to 13: `second_page_break` (often requires structural improvements: schema, internal links, content depth)
- Position 14 to 20: `third_page_lift` (typically requires more substantial work, sometimes consolidation or new pillar)

### Output

`label` is one of `top_page_climb`, `second_page_break`, `third_page_lift`, `not_striking`. `evidence` includes current position and an estimated effort tier.

## 9. Branded versus non-branded

### What it captures

Whether the keyword contains the client's brand name or a known variation. This is a coarse approximation of named-entity recognition limited to the brand-list parameter; for the full entity-recognition picture (NER tools, entity linking, salience scoring, knowledge graph integration), see [entity-and-topical-authority.md](entity-and-topical-authority.md).

### Inputs

`keyword`, brand list provided as `--brand-list` parameter (a JSON or text file with brand variations, including misspellings, internal product names, executive names if relevant).

### Method

A keyword is branded if a regex test against the brand list matches. Variations include exact brand name, common misspellings (handled via fuzzy match with a Levenshtein distance ≤ 2 on multi-word brands and ≤ 1 on single-word brands), and explicit brand modifiers (`brand login`, `brand support`, `brand careers`).

### Output

`label` is `branded` or `non_branded`. `evidence` names the matching brand variation.

### Edge cases

Generic words that overlap with brand names (e.g., a brand called «Apple» or «Amazon») cause false positives. The skill accepts an `--exclude-from-branded` regex parameter for these cases (e.g., `--exclude-from-branded "apple (pie|fruit|tree|seed)"`).

## 10. Questions and PAA

### What it captures

Question-shaped keywords and keywords whose SERPs include a People Also Ask box.

### Inputs

`keyword`, `serp_features`, language tag.

### Method

Question detection runs three tests in OR:

1. Keyword starts with an interrogative pronoun for its language.
2. Keyword ends with `?`.
3. Keyword contains a question pattern matched by the language-specific question regex.

PAA detection is straightforward: `serp_features` includes `paa`.

A keyword can be a question without triggering PAA (informational query with no PAA box) or trigger PAA without being a question (some PAA boxes attach to non-question keywords with rich SERPs).

### Output

`label` is one of `question`, `paa_only`, `question_and_paa`, `neither`. `related_keywords` lists other questions in the same cluster, useful for planning a complete Q&A section on a hub page.

## 11. Seasonality

### What it captures

Keywords with predictable temporal demand patterns (peaks during specific months, weeks, or events).

### Inputs

`keyword`, monthly trend data when available (Semrush and Ahrefs export 12-month trend sparklines in some report types), seasonal markers in the keyword string itself.

### Method

The skill detects seasonality through three signals.

Explicit seasonal markers in the keyword: month names (`january`, `gennaio`, `janvier`, `januar`, `enero`, and so on), season names (`summer`, `winter`), holiday markers (`christmas`, `black friday`, `easter`).

Trend pattern analysis when monthly data is present: standard deviation of monthly volumes divided by the mean. Coefficient of variation above 0.4 marks the keyword as seasonal; above 0.7 marks it as strongly seasonal.

Year markers in the keyword (`2025`, `2026`): flagged as event-driven temporal rather than seasonal proper, but reported in the same scope output for analyst convenience.

### Output

`label` is one of `evergreen`, `seasonal`, `strongly_seasonal`, `event_driven`. `evidence` includes the detected marker or the coefficient of variation. When monthly data is available, the peak month is reported in `evidence` for content-calendar planning.

## 12. Long tail

### What it captures

Keywords with low individual volume but high specificity, typically capturing late-funnel intent or conversational AI queries.

### Inputs

`keyword`, `volume`, token statistics.

### Method

A keyword is long tail if:

- Token count ≥ 5, OR
- `volume` ≤ 100 AND token count ≥ 4, OR
- The keyword passes the GEO opportunity test (scope 4) and is informational

Within long tail, two sub-segments matter:

- `long_tail_classical`: low-volume, multi-token, typed queries that signal late-funnel intent
- `long_tail_conversational`: long natural-language phrasings that route through generative engines

### Output

`label` is one of `long_tail_classical`, `long_tail_conversational`, `head`, `mid`. `evidence` includes the token count and the volume bucket.

## Default thresholds reference

Every threshold mentioned in this document has a default value and a CLI flag for override. The full reference appears in the `--help` output of the analyze script. The most-tuned thresholds during real engagements are:

| Threshold | Default | CLI flag |
|---|---|---|
| Quick win volume max | 5,000 | `--quickwin-volume-max` |
| Quick win volume min | 100 | `--quickwin-volume-min` |
| Quick win difficulty max | 35 | `--quickwin-difficulty-max` |
| Striking distance position min | 4 | `--striking-min` |
| Striking distance position max | 20 | `--striking-max` |
| Cluster overlap minimum | 0.60 | `--cluster-overlap-min` |
| AIO eligibility threshold | 60 | `--aio-eligibility-min` |
| GEO opportunity threshold | 60 | `--geo-opportunity-min` |
| Seasonality CV threshold | 0.40 | `--seasonality-cv-min` |
| Strong seasonality CV threshold | 0.70 | `--seasonality-cv-strong` |
| Long tail token threshold | 5 | `--long-tail-tokens-min` |

## Scope dependencies and order

The execution order in Stage 4 respects the dependency chain.

```
Intent classification (1)
    ├──> Cluster assignment (2)
    ├──> AIO eligibility (3)
    │       └──> GEO opportunity (4)
    ├──> Quick wins (5)
    └──> Long tail (12)

Branded vs non-branded (9)
    └──> Cannibalization risk (6, with branded exclusion logic)

Position-dependent scopes:
    Cannibalization risk (6)
    Content gap (7)
    Striking distance (8)

Independent of dependencies:
    Questions and PAA (10)
    Seasonality (11)
```

The skill enforces this order. An analyst-supplied custom rule set for any scope (via `--custom-rules`) is applied at the matching point in the chain, never out of order.
