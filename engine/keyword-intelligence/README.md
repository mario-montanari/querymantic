# keyword-intelligence

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Version: 1.0.0](https://img.shields.io/badge/version-1.0.0-blue)
![Tier: POWERFUL](https://img.shields.io/badge/tier-POWERFUL-purple)
![Language: English](https://img.shields.io/badge/language-english-blue)

> Curated by Mario Montanari, digital business, web and SEO consultant since 1997.

A Claude skill for professional keyword intelligence, made for analysts who work both sides of search at once: traditional engines (Google, Bing) and the new generative ones (AI Overviews, ChatGPT Search, Perplexity, Claude, Gemini).

## The problem

Keyword research as we knew it ten years ago is technically dead. Monthly volumes from third-party tools are estimates with error margins that often exceed 50%. SERPs are no longer ten blue links: today they are mixes of AI Overviews, featured snippets, video carousels, shopping packs, maps, Reddit threads, and generative summaries that grab clicks before the user reaches the organic section. The 2014 sequence, "pick the keyword, write the piece, rank for it," does not describe the job anymore.

What the practitioner builds in 2026 is a structured representation of demand: a graph with nodes (terms, entities, topics, intents), edges (co-occurrence, hierarchy, substitution, citation), and weights that change over time because algorithms, language models, and user behavior change.

Maintaining that graph by hand across tens of thousands of keywords is impractical. Keeping it inside a spreadsheet introduces invisible errors and decisions that no one can audit later. Relying on a single SaaS tool ties the quality of the decisions to the quality of that vendor's data.

This skill exists to make the process reproducible, vendor-neutral, and tied to actual decisions rather than analysis for its own sake.

## What this skill does

The skill takes a keyword list exported from any SEO tool (CSV) and turns it into a structured analytical dataset. It runs a deterministic seven-stage pipeline that starts with sourcing and ends with five coordinated output artifacts ready for client delivery. Everything happens locally, on the data you provide. No external API calls. No vendor lock-in.

Every run produces five coordinated artifacts that answer five different operational questions: what to write first, where you are at risk of cannibalizing yourself, which clusters competitors already own, where generative engines cite other people but could cite you, and exactly what to brief the writer for each cluster.

## The seven-stage pipeline

| # | Stage | What it produces |
|---|-------|------------------|
| 1 | Sourcing | A raw keyword corpus assembled from six source categories: seed keywords, algorithmic expansion (autocomplete, PAA, related searches), competitor extraction, internal data (GSC, GA4), linguistic expansion (synonyms, morphology, regional variants), and generative-AI sourcing (conversational queries, query fan-out) |
| 2 | Normalization | A canonical dataset: heterogeneous CSVs map to one canonical schema; Unicode normalization (NFC), case handling, encoding and separator detection, type coercion, multi-source reconciliation that preserves divergence as signal rather than averaging it away |
| 3 | Enrichment | A per-keyword feature set: language detection across English, French, German, Spanish; four-axis intent vector (query type, funnel stage, modality, temporal layer); branded versus non-branded segmentation; question detection; head/mid/long-tail token statistics |
| 4 | Scope analysis | Twelve analytical lenses applied per keyword: intent classification, cluster assignment, AIO eligibility, GEO opportunity, quick wins, cannibalization risk, content gap, striking distance, branded versus non-branded, questions and PAA, seasonality, long tail. Each scope outputs a label, a confidence score, and supporting evidence |
| 5 | Scoring | Four composite scores per keyword (main, quick-win, strategic, AEO/defensive), each accompanied by an independent confidence score from 0 to 1 derived from input completeness, source reliability, and enrichment certainty |
| 6 | Gap analysis | A gap inventory across seven dimensions: keyword (competitors rank, you do not), content (uncovered intents), intent (intent layers underserved), SERP feature (features unreachable in current shape), AEO/GEO (queries routing through AI engines without your visibility), entity (entities the corpus references that you do not own), freshness (queries with temporal sensitivity not addressed by recent content) |
| 7 | Output generation | Five coordinated artifacts written from the same canonical state: Markdown report, JSON, enriched CSV, TXT executive summary, per-cluster content briefs, plus an audit-trail metadata directory |

Two cross-cutting concerns sit alongside the seven stages.

### AEO and GEO integration

Generative-engine optimization runs as a parallel track across the whole pipeline: collecting conversational queries in stage 1, capturing AI-search signals in stage 3, classifying AIO eligibility and GEO opportunity in stage 4, contributing to the AEO/defensive composite in stage 5, surfacing the AEO/GEO gap in stage 6, and exposing the routing path per keyword in the artifacts. The skill explicitly addresses how AI Overviews, ChatGPT Search, Perplexity, Claude, and Gemini behave and what changes for each.

### Reading the post-2024 algorithmic environment

The skill's operational decisions account for what has happened since 2022: the Helpful Content Update sequence and the core updates that followed, the extension of E-A-T into E-E-A-T with Experience as a first-class component, the dominance of Reddit and UGC content in informational SERPs, the rise of information gain as a strategic principle (US patent US20200349181A1, granted June 2024), the recalibration of Core Web Vitals weight, and the role of structured data as a trust signal for generative engines.

## Supported input

The skill accepts exports from any keyword research tool. Internal normalization maps heterogeneous fields into a common schema, handling differences in headers, encoding, separator, date format, and unit of measure.

| Source | Format | Notes |
|--------|--------|-------|
| Semrush | CSV | Keyword Magic Tool, Organic Research, Position Tracking, Domain vs Domain |
| Ahrefs | CSV | Keywords Explorer, Site Explorer, Content Gap |
| Google Search Console | CSV (Performance export) | Top queries reports |
| Moz | CSV | Keyword Explorer |
| Ubersuggest | CSV | Keyword Ideas, SEO Analyzer |
| SE Ranking, Sistrix, KWFinder, Serpstat, Mangools, Surfer | CSV | Treated as generic; supply `--mapping` for explicit column maps when needed |
| Custom | CSV (any delimiter: comma, semicolon, tab, pipe) | Arbitrary schema; map via `--mapping` JSON |

XLSX, JSON, and other binary or hierarchical formats are not natively supported. Re-export to CSV from the source tool, which every supported vendor offers as a one-click option.

Supported keyword languages: English, French, German, Spanish. Stop words, intent markers, question detection patterns, and light suffix stripping are language-specific for each of the four.

## Operating mode

Everything runs offline. The skill makes no external API calls and sends no data to third-party servers. It asks for no credentials. The analysis is based entirely on the data you supply. The choice is functional: it makes the process reproducible, avoids lock-in, protects sensitive client data, and works in environments with network restrictions.

The practical consequence is that the quality of some signals depends on how rich the input CSV is. The more columns you provide (volume, difficulty, CPC, present SERP features, current position, ranking URLs, and so on), the more the skill can extract. Stages that would normally require live SERP capture or LLM citation capture rely on whatever is already present in your exports.

## Output

Five coordinated artifacts, generated by every full run.

### Markdown report

A narrative document that walks through the dataset the way a consultant would: state of demand, intent distribution, priority clusters, immediate quick wins, strategic plays, critical gaps, and executive recommendations. Designed to land in the hands of a decision maker (client, marketing director, founder) and end up inside a Notion page or a slide deck.

### Structured JSON

A machine-readable output containing the entire enriched dataset, the cluster maps, scores in all variants, and the gap inventory. Intended for anyone who wants to feed dashboards, sheets, or third-party systems, or come back to the analysis later without starting over.

### Enriched CSV

The original keyword list extended with every column the skill computes: language, intent vector (query type, funnel stage, modality, temporal), cluster head, AIO eligibility, GEO opportunity, scope flags (quick win, striking distance, cannibalization, branded, question, PAA, seasonality, long tail), the four composite scores with their confidence values, and the recommended action class (`create`, `update`, `restructure`, `monitor`, `ignore`). Sorted by main composite descending. The right format for people who live in Excel or Google Sheets and need to filter and share without intermediaries.

### Executive summary TXT

A 40 to 60 line summary for people who don't read the long reports. It opens with the Demand Opportunity Score, then names the actual clusters to start with and the actual quick-win keywords to commission, alongside the action split and the AEO and GEO openings competitors haven't claimed yet. Made for email, fast briefings, the first kickoff meeting. Hard cap at 80 lines.

### Content briefs

A Markdown file that turns the top clusters by volume into editorial brief skeletons: primary keyword, secondary keywords, questions to answer, dominant intent, suggested format, and recommended action. It is the bridge from analysis to production, so the work leaves with a roadmap instead of a spreadsheet to interpret. The skeleton is deterministic; ask Claude to expand any brief into a full writing brief when you need one.

The five files share the same timestamp, the same run identifier, and the same cluster IDs, so they cross-reference cleanly.

## Tracking progress between runs

Keyword work is not a one-off. You run the analysis at the start of an engagement, do a quarter of work, then run it again. `compare.py` reads two of those runs and tells you what actually moved: the Demand Opportunity Score delta, the quick wins you captured (a striking-distance keyword that broke into the top three) against the ones still open, per-keyword score and position movement, and the gaps that opened or closed. It writes its own `comparison.md` and `comparison.json`.

Because the pipeline is deterministic, the comparison is honest: when both runs use the same methodology version, every delta is a change in the data, not noise in the method. A version mismatch is flagged, because scores from different methods are not comparable. One caveat the tool states out loud: capturing an opportunity removes it from the opportunity-density signals, so a productive quarter can leave the headline score flat while the per-keyword tables show the real progress. Read the captured-win count and the position climbers, not the headline alone.

## Handing off to other skills

The structured JSON is a stable contract within a methodology version, which makes this skill a clean front end for the rest of an ecosystem. A content skill reads the clusters and the briefs. A GEO skill reads the AI-search routing and the AEO/GEO gap. A humanizing skill polishes the prose before it ships. Generic automation reads the enriched CSV. This skill produces the contract and stops there: it does not call those skills, and it does not pretend to orchestrate them. The field-level handoff recipes live in `references/ecosystem-contract.md`.

## Who this is for

The skill is written for senior practitioners. It assumes the user already understands intent classes, SERP features, clusters, canonicals, featured snippets, and AI Overviews. It does not explain the basics. It is not an introductory course.

It is built for:

- Independent SEO consultants and in-house teams who produce content roadmaps and have to defend the choices in front of whoever is paying.
- SEO and digital agencies working across multiple clients who need a reproducible, vendor-neutral method.
- Content strategists and content managers who decide what to write, where, in what order, in what format.
- SEO, AIO, and GEO copywriters and editors who get raw data and have to turn it into editorial plans (articles, pages, pillars, satellite pages, product pages, full website structures, writing briefs).
- Search engineers and product marketing teams mapping market demand into product roadmaps.

It is not for people looking for "the list of the first hundred keywords to write." That list does not exist in a neutral form. It depends on intent, SERP topology, domain authority, production capacity, and business goals. The skill helps build it for your specific case, not download it pre-packaged.

## Before and after

### Classic approach (how the work used to be done in 2018)

You exported a competitor's keyword list from your keyword research tool. You sorted by volume descending. You took the top 50. You eyeballed the list for items that looked off-topic and dropped them. You commissioned an article for each of the top twenty, with the requirement that "the title must contain the exact keyword." You published. You waited. Three months later: marginal traffic growth, half the articles ranking in positions 30 to 60, three articles ranking in positions 5 to 10 but not converting, two cannibalizing each other, none showing up in AI Overviews, and ChatGPT citing your competitors when answering the same queries.

### The skill's approach (how the work runs in 2026)

You load the full keyword export from your research tool of choice (5,000 keywords) into the skill, add an export of your domain's currently ranking keywords from GSC (1,200), and add a list of 200 conversational queries collected in an LLM simulation session. The skill normalizes encoding, separator, and column names; reconciles cross-tool divergences as preserved signal rather than averages; extracts a four-axis intent vector per keyword (query type, funnel stage, modality, temporal layer); types head, mid, and long-tail; flags AEO-eligible queries and GEO opportunities; builds clusters with a deterministic three-pass algorithm seeded by parent_topic and refined by token overlap; assesses gaps across seven dimensions; computes four composite scores per keyword (main, quick-win, strategic, AEO/defensive), each accompanied by an independent confidence score. The report identifies the priority clusters by total volume; flags cannibalization risks among existing pages; suggests pillar and cluster pages; for every cluster it provides primary keyword, secondary, supporting, dominant intent, structural recommendations, and the action class (`create`, `update`, `restructure`, `monitor`, `ignore`) the gap analysis assigns.

Same dataset. Different decisions across the board.

## Installation

### Claude Code (project-specific)

Copy the `keyword-intelligence/` folder into your project's `.claude/skills/`:

```
project/
└── .claude/
    └── skills/
        └── keyword-intelligence/
            ├── SKILL.md
            ├── scripts/
            ├── references/
            ├── assets/
            └── expected_outputs/
```

### Claude Code (global, all projects)

Copy the folder into `~/.claude/skills/` on Linux and macOS, or the equivalent path on Windows.

### claude.ai (desktop or web)

Load the skill from Settings, Capabilities, Skills, following Anthropic's official instructions.

### API

API loading is documented in the official Anthropic documentation.

## When it activates

The skill activates automatically when the user:

- Loads a keyword list (CSV with any delimiter) and asks for analysis, classification, clustering, prioritization, or gap analysis.
- Asks to map keywords to content (articles, pages, pillars, satellites, product pages, site structures).
- Asks to assess AEO or GEO opportunities on an existing dataset.
- Asks to clean, normalize, or deduplicate a keyword research export.
- Asks to compute opportunity, composite difficulty, click potential, or traffic value scores.
- Asks to detect cannibalization between URLs on a domain.
- Asks for multi-class intent analysis on a dataset.
- Asks to compare two analyses or track keyword progress between two points in time.

It does not activate for:

- Casual SEO conversations without an underlying dataset.
- Generic consulting requests without data.
- Purely technical contexts unrelated to search (code, server configuration, dev tooling).

## Skill structure

```
keyword-intelligence/
├── SKILL.md                       index file with YAML frontmatter
├── README.md                      this file
├── LICENSE                        MIT license
├── .gitignore
├── scripts/                       Python 3.7+, standard library only
│   ├── analyze.py                 main pipeline
│   ├── report.py                  artifact generation
│   ├── audit.py                   pre-flight validation
│   └── compare.py                 run-over-run comparison
├── references/                    knowledge base loaded on demand by Claude
│   ├── methodology-overview.md    seven principles, demand graph, terminology
│   ├── workflow.md                seven-stage pipeline, run comparison, run-time
│   ├── input-normalization.md     canonical schema, per-tool column maps
│   ├── analysis-scopes.md         the twelve scopes with rules and thresholds
│   ├── scoring-formulas.md        four composites, Demand Opportunity Score, seven gaps
│   ├── aio-geo-optimization.md    AI Overviews, GEO, llms.txt, citation readiness
│   ├── multi-language.md          per-language rules for English, French, German, Spanish
│   ├── output-artifacts.md        the five artifacts and the comparison artifacts
│   ├── ecosystem-contract.md      analysis.json as a handoff contract to other skills
│   ├── semantics.md               LSA to dense retrieval, embeddings, Google milestones
│   ├── clustering.md              algorithmic families, hybrid clustering, hybrid v2 roadmap
│   └── entity-and-topical-authority.md   entity SEO, named practitioners, AEO/GEO research
├── assets/
│   ├── samples/                   sample CSV exports for every supported tool
│   └── samples_followup/          a later re-export of the same corpus, for the comparison demo
└── expected_outputs/
    ├── sample_run/                reference outputs for the five delivery formats
    ├── sample_run_followup/       the follow-up run used by the comparison demo
    └── sample_comparison/         comparison.md and comparison.json from compare.py
```

## Credits and sources

The skill consolidates publicly available authoritative sources and field experience accumulated since 1997, with particular focus on the algorithmic shifts inside Google and the rise of generative engines.

### Official Google documentation

- Search Quality Rater Guidelines (latest version)
- Google Search Central, including webmaster guidelines and structured data documentation
- Relevant Google patents, in particular *Contextual estimation of link information gain* for the information gain concept and the patents on generative summaries for AI Overview

### Academic and technical research

- Manning, Raghavan, Schütze, *Introduction to Information Retrieval*, Cambridge University Press
- Robertson, Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond*
- Devlin et al., *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*, 2018
- Reimers, Gurevych, *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*, 2019
- Aggarwal et al., *GEO: Generative Engine Optimization*, Princeton and Georgia Tech, 2024

### Emerging specifications

- *llms.txt*, the specification proposed by Jeremy Howard in 2024 for site-level LLM-friendly summaries

### Industry publications

- Search Engine Journal, Search Engine Land, Moz Blog, Ahrefs Blog, Backlinko, iPullRank
- Public work by Aleyda Solis, Marie Haynes, Lily Ray, Glenn Gabe, and Mark Williams-Cook
- Bill Slawski's archived analysis of Google patents at *SEO by the Sea*

Recognition goes to all these authors, institutions, and projects for providing the public foundation on which the professional practice of the field has been built.

## Underlying philosophy

Four principles shape the skill. The first is vendor neutrality: every method described should be implementable with any reasonable substitute, including a custom-built one. The skill endorses no specific tool. Where tools are named, they are mentioned as examples.

The second is reproducibility: every score, every cluster, every recommendation traces back to its inputs. Running the same analysis twice on the same data produces the same result.

The third is transparency about uncertainty. Where data are estimates, the skill says so. Where consensus does not exist, it presents existing positions without forcing a false synthesis.

The fourth is operational grounding. Every analysis ends in a concrete decision: build, expand, prune, monitor, or ignore. Reports here exist to produce moves.

## Author

Mario Montanari has been designing digital strategies since 1997. Across his career he has worked through nine technological paradigms, starting with the machine-learning antispam filters of the late nineties and the manual SEO of the early 2000s, then static HTML, Flash, Web 2.0, responsive design, headless CMS, and the LLMs that became central in content and search after 2022. Over a hundred projects across luxury automotive, Formula 1, international FMCG, legal, premium tourism, and public administration.

Specialized in SEO, GEO, and AEO, he works on contemporary visibility: organic ranking on Google, citations inside AI Overviews, mentions in ChatGPT and Perplexity. He builds analytical systems that combine reproducible method with professional judgment, instead of relying solely on the output of a single tool.

Personal site: [mariomontanari.it](https://mariomontanari.it)

This skill is the formalization of a method he uses daily with his clients. It is released as open source because the discipline, at this moment, needs shared method more than it needs more tools.

## License

MIT License. See the `LICENSE` file for the full text. Use, modify, integrate this skill in any project, including commercial work, with attribution kept. The license is chosen to maximize reuse.

## Contributing

Contributions are welcome.

To report a problem or suggest a change, open a GitHub issue with a clear description. To submit code or reference changes, open a pull request with the rationale and, where possible, concrete examples or use cases. If you use a tool that isn't yet supported, a pull request adding a new import adapter is the most direct contribution. Methodological discussions are welcome, as long as they are grounded in public sources, observational data, or documentable cases.

The skill is alive. SEO changes fast and GEO changes faster, and the skill is updated to follow.
