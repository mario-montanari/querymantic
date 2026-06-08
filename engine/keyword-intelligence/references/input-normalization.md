# Input normalization

## Contents

- The canonical schema
- Required versus optional columns
- Per-tool mapping
  - Semrush
  - Ahrefs
  - Google Search Console
  - Moz
  - Ubersuggest
  - Generic CSV
- Encoding and separator handling
- Type coercion rules
- Validation rules
- Reconciliation across sources
- What stays unmapped

## The canonical schema

Every CSV input is converted to a single canonical schema before any analysis runs. The schema has a required core, an optional extension, and a provenance block.

### Required core

| Canonical column | Type | Description |
|---|---|---|
| `keyword` | string | The query string itself, lowercased and trimmed |
| `source` | enum | One of: `semrush`, `ahrefs`, `gsc`, `moz`, `ubersuggest`, `generic`, `seed` |

A row missing either of these two columns is rejected at parse time.

### Optional extension

| Canonical column | Type | Description |
|---|---|---|
| `volume` | int | Monthly search volume estimate |
| `difficulty` | int (0-100) | Keyword difficulty score |
| `cpc` | float | Cost per click in USD |
| `position` | int (1-100) | Current ranking position of the analysed domain or competitor |
| `serp_features` | list[str] | SERP feature labels: `featured_snippet`, `paa`, `images`, `video`, `local_pack`, `knowledge_panel`, `ai_overview`, `shopping`, `news`, `sitelinks` |
| `traffic_potential` | int | Estimated organic traffic potential per month |
| `intent_label_raw` | string | The intent label assigned by the source tool (preserved verbatim) |
| `language` | string (ISO 639-1) | Language code of the keyword |
| `country` | string (ISO 3166-1 alpha-2) | Country code for the volume estimate |
| `clicks` | int | Reported clicks (GSC and similar) |
| `impressions` | int | Reported impressions (GSC and similar) |
| `ctr` | float (0-1) | Click-through rate (GSC and similar) |
| `parent_topic` | string | Parent topic or cluster label assigned by the tool |
| `competitor_url` | string | Competitor URL ranking for the keyword |
| `domain_rank` | int | Domain authority or rank of the ranking entity |

### Provenance block

| Canonical column | Type | Description |
|---|---|---|
| `source_file` | string | Filename of the CSV the row came from |
| `source_row` | int | Original row number in the source CSV (1-indexed, header counted) |
| `import_timestamp` | ISO 8601 | When the row entered the canonical schema |

The provenance block is populated automatically and never accepted from input. Its presence makes every downstream finding auditable back to a specific row in a specific file.

## Required versus optional columns

The skill operates with as little as `keyword` and `source`. Every additional canonical column unlocks more scope analyses and tightens the confidence score on the composite. The relationship between canonical columns and the analyses they enable is explicit.

| Analysis | Required canonical columns |
|---|---|
| Intent classification | `keyword`; `serp_features` improves accuracy; `intent_label_raw` informs the rule when present |
| Cluster assignment | `keyword`; `parent_topic` improves seeding |
| AIO eligibility | `keyword`, `serp_features` (for `ai_overview` flag) |
| GEO opportunity | `keyword`; `serp_features` and `position` improve targeting |
| Quick wins | `keyword`, `volume`, `difficulty` |
| Cannibalization risk | `keyword`, `position`; same `keyword` repeated across the corpus signals the case |
| Content gap | `keyword`, `position`; `competitor_url` improves the analysis |
| Striking distance | `keyword`, `position` |
| Branded vs non-branded | `keyword`; client brand list provided as parameter |
| Questions and PAA | `keyword`; `serp_features` improves detection |
| Seasonality | `keyword`, `volume`; trend column when available |
| Long tail | `keyword` (token statistics computed in Stage 3) |

A keyword without `volume` or `difficulty` cannot be ranked for quick wins, but it still receives intent classification, cluster assignment, and gap analysis. The skill never refuses to process rows with partial data; it returns partial scores with explicit confidence.

## Per-tool mapping

The mapping tables below cover the default export formats of each supported tool as of the cutoff date for the methodology version. Tool vendors change column names without notice; the skill accepts user-supplied mapping overrides for any column that has been renamed.

### Semrush

Default export: «Keyword Magic Tool», «Position Tracking», «Organic Research».

| Semrush column | Canonical column | Notes |
|---|---|---|
| `Keyword` | `keyword` | Lowercased and trimmed |
| `Volume` | `volume` | |
| `Keyword Difficulty` or `KD%` | `difficulty` | Strip `%` if present |
| `CPC` or `CPC (USD)` | `cpc` | |
| `Position` or `Pos.` | `position` | |
| `SERP Features by Keyword` | `serp_features` | Comma-separated list, normalized to canonical labels |
| `Traffic` | `traffic_potential` | When export is from Organic Research; otherwise leave empty |
| `Intent` | `intent_label_raw` | Preserved verbatim |
| `Country` | `country` | |
| `Parent Topic` | `parent_topic` | |
| `URL` | `competitor_url` | When the export is from Domain vs Domain or Organic Research |

SERP feature normalization: Semrush labels like `Featured Snippet`, `People Also Ask`, `AI Overview`, `Knowledge Panel`, `Local Pack` map to canonical lowercase snake_case (`featured_snippet`, `paa`, `ai_overview`, `knowledge_panel`, `local_pack`).

### Ahrefs

Default export: «Keywords Explorer», «Site Explorer», «Content Gap».

| Ahrefs column | Canonical column | Notes |
|---|---|---|
| `Keyword` | `keyword` | |
| `Volume` | `volume` | |
| `KD` | `difficulty` | |
| `CPC` | `cpc` | |
| `Current position` or `Position` | `position` | |
| `SERP features` | `serp_features` | |
| `Traffic potential (TP)` | `traffic_potential` | |
| `Intents` | `intent_label_raw` | Ahrefs assigns multiple intents; preserved as comma-separated string |
| `Country` | `country` | |
| `Parent topic` | `parent_topic` | |
| `Top URL` or `URL` | `competitor_url` | |
| `DR` | `domain_rank` | |
| `Clicks` | `clicks` | When present in keyword research export |

### Google Search Console

GSC exports come from «Performance» reports, segmented by query.

| GSC column | Canonical column | Notes |
|---|---|---|
| `Top queries` or `Query` | `keyword` | |
| `Clicks` | `clicks` | |
| `Impressions` | `impressions` | |
| `CTR` | `ctr` | Strip `%` and convert to 0-1 float |
| `Position` | `position` | GSC reports decimal positions; round half-up |
| `Country` | `country` | When segmented by country |

GSC does not provide volume, difficulty, or CPC. The analysis still benefits from GSC because internal data has the highest reliability of any source: a query the client's domain already ranks for and receives impressions on is a confirmed query in the client's intent space, regardless of how external tools rate it.

### Moz

Default export: «Keyword Explorer».

| Moz column | Canonical column | Notes |
|---|---|---|
| `Keyword` | `keyword` | |
| `Monthly Volume` or `Volume` | `volume` | |
| `Difficulty` | `difficulty` | |
| `Organic CTR` | `ctr` | |
| `Priority` | (skill-internal field) | Moz combines volume, difficulty, and CTR; preserved as `moz_priority` if present |
| `SERP Features` | `serp_features` | |
| `Country` | `country` | |

### Ubersuggest

Default export: «Keyword Ideas», «SEO Analyzer».

| Ubersuggest column | Canonical column | Notes |
|---|---|---|
| `Keyword` | `keyword` | |
| `Volume` or `Search Volume` | `volume` | |
| `SEO Difficulty` or `SD` | `difficulty` | |
| `CPC` | `cpc` | |
| `Paid Difficulty` | (skill-internal field) | Preserved as `ubersuggest_pd` when present |

### Generic CSV

When a CSV does not match any recognized tool signature, the skill applies generic mapping rules.

A CSV qualifies as «generic» if its header includes at least `keyword` (case-insensitive). The skill then attempts column inference for known canonical names: any header matching `volume`, `vol`, `search volume`, `monthly volume`, `monthly searches` maps to `volume`. Any header matching `difficulty`, `kd`, `seo difficulty`, `keyword difficulty`, `kd%` maps to `difficulty`. Inference rules are documented in the `--show-mapping` output of the analyze script for transparency.

If inference fails for a column the analyst expects to use, the skill accepts a `--mapping` JSON file that supplies explicit mappings: `{"My Column Name": "volume"}`.

## Encoding and separator handling

CSV files arrive with inconsistent encoding and inconsistent separators. The skill handles four cases.

UTF-8 with BOM: the BOM is stripped and the file is read as UTF-8. UTF-8 without BOM is read directly. Latin-1 (ISO 8859-1) is detected by sniffing the first 4 KB for byte sequences invalid in UTF-8 and decoded accordingly. UTF-16 (with BOM) is detected and decoded; UTF-16 without BOM is rejected with a remediation message asking for a re-export in UTF-8.

Separator detection sniffs the first 4 KB of the file. The candidate separators are comma, semicolon, tab, and pipe (in that order of preference). The detector picks the separator whose count is most consistent across the first ten lines. If no candidate is consistent, the file is rejected with a remediation message.

## Type coercion rules

Numeric columns from CSV inputs arrive as strings with locale-specific formatting. Coercion rules are explicit.

For `volume`, `clicks`, `impressions`, `position`, and `domain_rank`: strip thousands separators (`,` or `.`), parse as integer. Negative values are rejected. Empty strings convert to null.

For `difficulty`: strip `%` suffix, parse as integer. Values above 100 are rejected. Values below 0 are rejected.

For `cpc`: strip currency symbols (`$`, `€`, `£`), strip thousands separators, parse as float. Negative values are rejected.

For `ctr`: if the value contains `%`, strip and divide by 100. If the value is a float between 0 and 1 (no `%`), accept directly. Values above 1 (without `%`) are rejected as malformed.

For `serp_features`: split on comma, strip each item, normalize to canonical labels via the lookup table built into the skill. Unknown labels are preserved with a `_unknown_` prefix and surfaced in the validation report.

For `keyword`: lowercase, trim leading and trailing whitespace, collapse internal multiple spaces to single space, normalize Unicode to NFC form. The original casing is preserved in `keyword_original` for display purposes.

## Validation rules

Validation runs after parsing and before any keyword enters the canonical corpus.

Row-level validation rejects rows missing `keyword`, rows where `keyword` is empty after trimming, rows where the keyword is longer than 200 characters (likely a paragraph, not a query), and rows with type-coercion failures that the analyst has not opted to ignore.

File-level validation rejects files with no readable header, files with fewer than two rows of data, files with a detected separator that produces inconsistent column counts across rows, and files that exceed 500 MB in size (the skill is offline and processes locally; very large files should be split or pre-filtered).

Corpus-level validation runs after all source files are parsed. It flags duplicate `(keyword, source, country, language)` tuples (these may be legitimate multi-source reports or accidental re-imports; the analyst inspects the report and decides). It flags corpora dominated by a single source (>90% from one source category) as potentially biased.

Every validation failure produces a structured message naming the file, the row, the rule that fired, and a suggested remediation. The skill never silently drops rows.

## Reconciliation across sources

When the same `keyword` appears in multiple sources, the skill keeps every occurrence as a separate row in the canonical corpus and adds a `multi_source` flag to each occurrence. This is deliberate. The analysis reports per-source values where they differ, computes per-keyword aggregates explicitly (mean, median, min, max), and lets the analyst pick which signal to trust.

For composite scoring purposes, the skill uses the following default reconciliation when computing a single value per keyword:

- `volume`: median of available sources, with a confidence score reflecting the spread
- `difficulty`: median of available sources
- `cpc`: median of available sources
- `position`: from GSC if available, otherwise minimum across sources (best ranking observed)
- `serp_features`: union across sources
- `intent_label_raw`: concatenated comma-separated, preserved as is

These defaults are configurable via the `--reconciliation` parameter on the analyze script.

## What stays unmapped

Some columns from source tools have no canonical equivalent and are preserved as enrichment columns in the canonical record without informing scoring. Examples include Ahrefs `Keyword status`, Semrush `Trends` (12-month sparkline data), Moz `Last Updated`, and any tool-specific scoring columns whose calculation is opaque. These columns appear in the JSON intermediate state under `tool_specific.<source>.<column_name>` and are surfaced in the enriched CSV output as columns prefixed with the source name. They never enter the composite score because their methodology is outside the skill's vendor-neutral commitment.
