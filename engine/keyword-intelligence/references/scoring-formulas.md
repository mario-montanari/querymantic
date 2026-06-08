# Scoring formulas

## Contents

- The two-layer scoring philosophy
- Signal normalization
- The four composite scores
  - Main composite
  - Quick-win composite
  - Strategic composite
  - AEO/defensive composite
- Confidence scoring
- The Demand Opportunity Score
- The seven gap dimensions
- Gap priority formula
- Worked examples

## The two-layer scoring philosophy

Every keyword carries two scores, not one. The composite score answers «how attractive is this keyword on its merits». The confidence score answers «how reliable is this composite given the inputs that fed it». The skill never collapses the two into a single number. A keyword scoring 92 with confidence 0.4 is a research target. The same composite with confidence 0.95 is an action target. Conflating these two cases produces over-confident roadmaps that fall apart on contact with reality.

Both layers travel together through every artifact. The Markdown report shows them side by side. The JSON output stores them as distinct fields. The enriched CSV emits two columns per composite: `<composite>_score` and `<composite>_confidence`.

## Signal normalization

Composite scores combine signals expressed on different scales (volume in absolute counts, difficulty 0-100, position 1-100, intent as categorical). Every signal is normalized to a 0-100 score before entering a composite. Five normalization functions cover the common cases.

Volume normalization uses logarithmic scaling because the raw distribution is heavy-tailed:

```
volume_score = clamp(0, 100, 100 * log10(max(1, volume)) / log10(volume_reference))
```

`volume_reference` defaults to 100,000 (configurable via `--volume-reference`). A volume of 100,000 maps to score 100; a volume of 1,000 maps to about 60; a volume of 10 maps to about 20.

Difficulty normalization inverts the raw value because lower difficulty is better:

```
difficulty_score = 100 - difficulty
```

Position normalization rewards high rankings on a non-linear curve:

```
if position is null:    position_score = null (signal absent)
if position == 1:       position_score = 100
if position <= 3:       position_score = 90
if position <= 10:      position_score = 80 - (position - 4) * 5
if position <= 20:      position_score = 50 - (position - 11) * 3
if position <= 50:      position_score = 25 - (position - 21) * 0.5
else:                   position_score = 5
```

Intent score depends on the composite that consumes it. The main composite assigns 100 to commercial-investigation and transactional, 80 to informational, 60 to navigational. The quick-win composite assigns 100 to commercial-investigation, 80 to transactional, 70 to informational, 0 to navigational (navigational queries are not quick wins). The AEO/defensive composite assigns 100 to navigational and brand-adjacent informational, lower for everything else.

CTR potential normalization uses position and SERP feature presence:

```
ctr_potential = base_ctr_for_position * (1 - aio_dampening) * (1 - paa_dampening)
```

Where `base_ctr_for_position` is a lookup table (position 1 = 0.30, position 2 = 0.15, position 3 = 0.10, decreasing), `aio_dampening` is 0.4 if the SERP shows an AI Overview (clicks suppressed), and `paa_dampening` is 0.1 if the SERP shows PAA. The skill exposes the dampening factors as flags for sensitivity analysis.

## The four composite scores

Every keyword receives all four composites. The analyst sorts on whichever composite matches the engagement objective.

### Main composite

The default ranking score. Used when the engagement objective is general SEO performance.

```
main = 0.35 * volume_score
     + 0.25 * (100 - difficulty)
     + 0.15 * intent_score
     + 0.10 * ctr_potential_score
     + 0.10 * cluster_strength_score
     + 0.05 * serp_feature_winnability_score
```

Weights total 1.00. `cluster_strength_score` rewards keywords inside coherent, high-volume clusters (full formula below). `serp_feature_winnability_score` rewards keywords whose SERP features are reachable for the client's domain class (a small site is unlikely to win Knowledge Panel but can win Featured Snippet).

The main composite weights volume the highest because, all else equal, an analyst who sorts by main composite expects the top of the list to contain the keywords with the largest reachable demand. Volume's weight does not crush the other signals because volume_score itself is logarithmic.

### Quick-win composite

Used when the engagement is operating on a quarterly horizon and the analyst needs prioritization for content sprints.

```
quick_win = 0.30 * (100 - difficulty)
          + 0.25 * volume_score
          + 0.15 * proximity_score
          + 0.15 * intent_score (quick-win variant)
          + 0.10 * cluster_quick_win_bonus
          + 0.05 * serp_feature_winnability_score
```

`proximity_score` rewards keywords within striking distance (positions 4-20) and keywords without a current ranking (position null) when their difficulty is below 25. The bonus rewards quick wins that fall inside coherent clusters because they reinforce architecture rather than producing orphan pages.

A keyword scores quick_win > 75 only when difficulty is below 35 AND (position is in striking distance OR difficulty is below 25). The structure prevents the score from being inflated by volume alone.

### Strategic composite

Used when the engagement is operating on an annual horizon and the analyst is making architecture decisions, not just content commission decisions.

```
strategic = 0.30 * cluster_strength_score
          + 0.20 * volume_score
          + 0.15 * intent_score
          + 0.15 * gap_severity_score
          + 0.10 * geo_opportunity_score
          + 0.10 * (100 - difficulty)
```

Cluster strength dominates because architecture work pays off through cluster coverage, not single-keyword wins. `gap_severity_score` is high when the keyword sits in a content gap and the cluster is partially staffed by competitors only. `geo_opportunity_score` is the AIO/GEO output (scope 4) reweighted to 0-100. Difficulty is weighted lower than in the main composite because strategic work justifies harder targets when the architecture payoff is large.

### AEO/defensive composite

Used when the engagement is brand-protective: defending branded queries, identifying queries where AI engines route users to non-client sources, watching for cannibalization risks.

```
aeo_defensive = 0.30 * brand_proximity_score
              + 0.25 * cannibalization_severity_score
              + 0.20 * geo_opportunity_score
              + 0.15 * aio_eligibility_score
              + 0.10 * volume_score
```

`brand_proximity_score` is 100 for branded keywords, 60 for category-adjacent (the brand's product category in non-branded form), 0 for unrelated keywords. `cannibalization_severity_score` is 100 for confirmed cannibalization, 60 for suspected, 0 for no risk.

This composite identifies the keywords that, if neglected, will cause the largest brand or competitive damage. Volume is weighted lowest because defensive work targets even low-volume queries when they are brand-critical.

## Confidence scoring

Every composite carries a confidence score from 0 to 1. The score is the geometric mean of three sub-confidences.

Input completeness sub-confidence reflects how many of the composite's input signals are available. The main composite consumes six signals; if all six are populated, input_completeness = 1.0. If volume is missing, input_completeness = 5/6 = 0.83. The penalty is geometric, not arithmetic, so missing one critical signal weighs heavier than missing one minor signal: signals are weighted by the same coefficients used in the composite formula.

Source reliability sub-confidence reflects the trust placed in the data source. Internal data (GSC, GA4) = 1.0. Established commercial tools (Semrush, Ahrefs, Moz) = 0.9. Other tools (Ubersuggest, generic) = 0.75. Algorithmic expansion = 0.7. Generative AI sourcing = 0.6 (the queries are real, but the volume estimates rarely come from these sources). Seed-only entries = 0.5 (the keyword is real but external metrics are absent).

Enrichment certainty sub-confidence reflects the average confidence of the Stage 3 enrichment outputs (language detection confidence, intent vector confidence, branded detection confidence). When all enrichments are confident, this term is near 1.0. When the language could not be detected and the intent classification fell back to default heuristics, this term drops to 0.4-0.5.

The geometric mean is computed as:

```
confidence = (input_completeness * source_reliability * enrichment_certainty) ^ (1/3)
```

A keyword with input_completeness 0.8, source_reliability 0.9, enrichment_certainty 0.7 has confidence (0.8 * 0.9 * 0.7) ^ (1/3) = (0.504) ^ (1/3) = 0.795.

The geometric mean is chosen over the arithmetic mean because it punishes the weakest link harder. A keyword with one bad input cannot compensate by having two strong inputs.

## The Demand Opportunity Score

The four composites and their confidence scores live at the keyword level. The Demand Opportunity Score (DOS) lives at the corpus level: a single 0 to 100 reading of how much actionable demand the corpus holds, so a run has one number a decision-maker can remember. The Markdown report and the executive summary both lead with it. It is stored in `corpus_summary.demand_opportunity_score`.

The DOS is a weighted blend of five corpus-level signals. The weights sum to 1.00, so the score lands on a 0 to 100 scale.

```
DOS = 100 * (0.30 * mean_main_quality
           + 0.25 * quick_win_density
           + 0.20 * striking_density
           + 0.15 * aio_share
           + 0.10 * geo_share)
```

Each term is normalized to the 0 to 1 range:

- `mean_main_quality` is the mean of the per-keyword main composite across the corpus, divided by 100 and clamped to [0, 1]. It carries the most weight because it summarizes the overall quality of the opportunity set.
- `quick_win_density` is the share of keywords whose quick-win scope label is `quick_win`. It rewards immediate, reachable work.
- `striking_density` is the share of keywords whose striking-distance scope label is one of `top_page_climb`, `second_page_break`, `third_page_lift`. It rewards near-term lift on positions the client already holds.
- `aio_share` is `corpus_summary.aio_eligibility_share`: the share of keywords whose AIO eligibility label is `confirmed` or `eligible`. It rewards AI Overview surface.
- `geo_share` is `corpus_summary.geo_opportunity_share`: the share of keywords whose GEO opportunity label is `dual` or `geo_only`. It rewards generative-citation upside.

The blend is deliberate. It rewards a corpus that combines a high-quality opportunity set with reachable near-term work and AI-search surface, rather than raw volume alone. Volume enters only indirectly, through the main composite, where it is already logarithmic. A corpus stuffed with high-volume but unreachable head terms does not score well; a corpus with a healthy density of reachable quick wins and striking-distance positions does.

The bundled sample run scores 35.8. The score is most useful as a relative reading across runs of the same corpus rather than as an absolute benchmark across different corpora, since the densities depend on corpus composition and on the thresholds in force.

One property is worth naming, because it surprises analysts who expect the score to rise whenever work is done. Realizing an opportunity removes it from the density signals: a striking-distance keyword that climbs into the top three leaves `striking_density`, and a captured quick win leaves `quick_win_density`. A quarter that captures several opportunities can leave the DOS flat while real progress shows in the per-keyword tables. When judging a quarter with `compare.py`, read the captured-quick-win count and the position climbers alongside the DOS delta, not the DOS delta alone. The run-comparison tool is documented in [output-artifacts.md](output-artifacts.md).

## The seven gap dimensions

Gap analysis (Stage 6) operates at the corpus level. It identifies seven distinct categories along which the client's portfolio can be missing relative to the observed demand.

### 1. Keyword gap

The set of keywords for which competitor domains rank in the top 30 and no client URL appears in the top 100. Severity per keyword combines the competitor strength (mean DR of the ranking competitors) and the volume of the keyword. Cluster-level keyword gaps (a cluster where >70% of members are in the keyword gap) receive a multiplier because they reveal an unstaffed hub.

### 2. Content gap

The set of intents present in the corpus that no existing client content addresses. Distinct from keyword gap: a keyword gap is a single missing string; a content gap is a missing intent that may correspond to many strings. Content gaps are computed by taking the intent vectors of cluster heads and comparing against the intent vectors of existing client URLs (when GSC data is supplied). Severity per content gap combines cluster volume, cluster size, and competitor staffing in the cluster.

### 3. Intent gap

A coarser-grained gap than content gap. Intent gap reports whether the entire portfolio is missing one intent layer (informational, navigational, transactional, commercial-investigation). Severity is binary per intent layer: present or missing. The output is a list of missing intent layers with the volume of demand at each layer.

### 4. SERP feature gap

The set of SERP features present in the corpus that the client's pages cannot win in their current shape. Computed by taking the union of `serp_features` across the corpus and comparing against the features the client's URLs currently win (when GSC and SERP data is supplied). Severity per feature is the count of keywords showing the feature multiplied by the average volume.

### 5. AEO/GEO gap

The set of keywords routing through AI search experiences (AIO-eligible or GEO opportunity, by scopes 3 and 4) without client visibility. Computed by intersecting AIO-eligible/GEO-opportunity keywords with keywords where no client URL ranks in the top 10. Severity combines volume and the AEO/GEO opportunity score.

### 6. Entity gap

The set of named entities (brands, products, people, places) referenced across the corpus that the client does not own and does not authoritatively cover. Entity extraction is rule-based: capitalized multi-word phrases, presence in the brand-list parameter, recognized geographic markers. Severity is the count of keywords mentioning the entity multiplied by the average volume. For the broader entity-SEO context (NER tools, entity linking, salience scoring, knowledge-graph integration, Wikipedia and Wikidata pathways), see [entity-and-topical-authority.md](entity-and-topical-authority.md).

### 7. Freshness gap

The set of queries with temporal sensitivity (event-driven or breaking by scope 11) for which the client has no recent content (when content recency data is supplied as a separate `--content-recency` parameter). Severity combines volume and time-decay (a 6-month-old freshness gap weighs less than a 2-month-old one).

## Gap priority formula

Each gap finding receives a priority score from 0 to 100 computed by the same logic across dimensions, with weights tuned per dimension.

```
priority = w_volume * volume_aggregate_score
         + w_competitor * competitor_severity_score
         + w_intent * intent_alignment_score
         + w_cluster * cluster_coverage_score
         + w_recency * recency_score
```

Weights vary by gap dimension. For keyword gap and content gap: 0.30, 0.25, 0.20, 0.20, 0.05. For intent gap and SERP feature gap: 0.40, 0.10, 0.30, 0.15, 0.05. For AEO/GEO gap: 0.30, 0.10, 0.20, 0.15, 0.25 (recency matters more because AI search algorithms shift faster than classical search). For entity gap: 0.35, 0.15, 0.15, 0.30, 0.05. For freshness gap: 0.25, 0.05, 0.15, 0.10, 0.45.

Each gap finding is also assigned a recommended action class:

- `create`: priority ≥ 70 and the gap can be addressed by a single new asset
- `update`: priority ≥ 60 and the gap can be addressed by refreshing an existing asset
- `restructure`: priority ≥ 70 and the gap requires multi-asset coordination (cluster or architecture work)
- `ignore`: priority < 40 OR the gap addresses queries outside the client's commercial scope

Action class assignment is rule-based and exposed in `evidence` for audit.

## Worked examples

The following examples illustrate composite computation for three keyword profiles. All values use the default thresholds.

### Example 1: high-volume informational query, partial data

Inputs: `keyword = "running shoes review"`, `volume = 12000`, `difficulty = 42`, `cpc = null`, `position = null`, `serp_features = [paa, ai_overview]`, intent = commercial-investigation, intent_confidence = 0.9.

Volume_score = clamp(0, 100, 100 * log10(12000) / log10(100000)) = 100 * 4.079 / 5.0 = 81.6.

Difficulty_score = 100 - 42 = 58.

Intent_score (main variant) = 100 (commercial-investigation).

CTR_potential_score = base_ctr_for_position(null) is undefined, so falls back to 0 with a confidence penalty.

Cluster_strength_score = 70 (assuming the keyword sits in a coherent commercial cluster).

SERP_feature_winnability_score = 60 (PAA is reachable, AI Overview is uncertain).

Main composite = 0.35 * 81.6 + 0.25 * 58 + 0.15 * 100 + 0.10 * 0 + 0.10 * 70 + 0.05 * 60 = 28.6 + 14.5 + 15 + 0 + 7 + 3 = 68.1.

Confidence: input_completeness = 0.85 (CPC and position missing, but they have lower weight); source_reliability = 0.9 (Semrush); enrichment_certainty = 0.85. Confidence = (0.85 * 0.9 * 0.85) ^ (1/3) = 0.866.

Result: main composite 68.1, confidence 0.87. Solid candidate, well-supported.

### Example 2: low-volume long-tail conversational query

Inputs: `keyword = "what is the best running shoe for flat feet women under 100 dollars"`, `volume = 30`, `difficulty = 12`, intent = commercial-investigation, AIO eligibility = eligible (score 75), GEO opportunity = high (score 80).

Volume_score = 100 * log10(30) / log10(100000) = 100 * 1.477 / 5.0 = 29.5.

Difficulty_score = 88.

Strategic composite = 0.30 * 65 (cluster_strength, sits in a small cluster) + 0.20 * 29.5 + 0.15 * 100 + 0.15 * 70 (gap_severity) + 0.10 * 80 + 0.10 * 88 = 19.5 + 5.9 + 15 + 10.5 + 8 + 8.8 = 67.7.

Quick-win composite = 0.30 * 88 + 0.25 * 29.5 + 0.15 * 60 (proximity, no current ranking but low difficulty) + 0.15 * 100 + 0.10 * 50 + 0.05 * 60 = 26.4 + 7.4 + 9 + 15 + 5 + 3 = 65.8.

Confidence: input_completeness = 0.8 (cpc and position missing); source_reliability = 0.9; enrichment_certainty = 0.9. Confidence = 0.866.

Result: strategic 67.7, quick-win 65.8, AEO/defensive lower. Notable as a long-tail GEO opportunity that fits inside a cluster.

### Example 3: cannibalization candidate

Inputs: `keyword = "running shoes"`, `volume = 90000`, `difficulty = 78`, two client URLs ranking at position 14 and position 27, intent = commercial-investigation.

Main composite = 0.35 * 99 (very high volume) + 0.25 * 22 + 0.15 * 100 + 0.10 * 30 (low CTR potential at positions 14 and 27) + 0.10 * 60 + 0.05 * 50 = 34.7 + 5.5 + 15 + 3 + 6 + 2.5 = 66.7.

AEO/defensive composite = 0.30 * 0 (non-branded) + 0.25 * 100 (confirmed cannibalization) + 0.20 * 30 + 0.15 * 30 + 0.10 * 99 = 0 + 25 + 6 + 4.5 + 9.9 = 45.4.

The main composite suggests «high attractiveness», but the AEO/defensive composite flags the cannibalization. The Markdown report shows both, and the recommendation reads: consolidate the two client URLs before pursuing the keyword as a primary target. This is the kind of finding that the two-layer scoring philosophy is designed to surface.
