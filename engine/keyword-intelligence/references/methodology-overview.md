# Methodology overview

## Contents

- The reframe: from list to graph
- Seven principles
- The five forces that shape a query
- Vendor-neutrality as a methodological commitment
- Reproducibility as the lower bound
- What this skill is not
- How insights become decisions
- A note on terminology
- Theoretical foundations

## The reframe: from list to graph

Keyword research has been treated for two decades as the production of a list. An analyst opens a tool, types a seed term, exports a CSV with thousands of rows, and considers the work done. The list contains volume, difficulty, CPC, and a label called intent. Strategy then gets constructed by sorting and filtering this list.

This works for transactional pages. It collapses for everything else.

A query is not an isolated string. A query is an observation of demand at a single point in a much larger structure: a graph where nodes are intents, topics, and entities, and edges are semantic, navigational, and intentional relationships. When that graph is invisible, three failures recur.

1. Two pages target the same intent under different surface phrasing. Cannibalization follows.
2. A topic cluster is missing the bridge query that ties together its peripheral intents. Internal linking decays.
3. An emerging long tail of conversational queries is invisible to the team because it lacks volume. AI search engines route the user there anyway.

The reframe is operational, not philosophical. The output of keyword intelligence is a graph of demand. The list remains, but as a projection of the graph, not the other way around.

## Seven principles

The methodology rests on seven principles applied as a set, not selectively.

### 1. Keywords are observations, not the demand itself

A keyword volume number is a delayed and partial measurement of intent traffic, with sampling bias toward English markets, transactional verticals, and queries with commercial value. Treating that number as the demand itself produces a strategy that mistakes what is measurable for what actually matters.

### 2. Structure beats volume

A high-volume keyword inside a fragmented topic graph is worth less than a medium-volume keyword inside a coherent cluster. The reason is page design: a coherent cluster lets a team publish a hub and three spokes that mutually reinforce each other through internal links and topical authority signals. The orphan keyword forces a one-off page with no internal authority feed and no semantic neighbors.

### 3. Vendor-neutrality is a methodological commitment

The skill normalizes inputs from multiple tools because the underlying graph of demand exists independently of any vendor's index. A query is the same query whether Semrush, Ahrefs, GSC, Moz, or Ubersuggest reports it. Tying analysis to a single vendor's metric definitions produces conclusions that change when the vendor changes its methodology, repricing every historical comparison.

### 4. Reproducibility separates intelligence from extraction

A keyword extraction is a one-off act: pull the data, hand it over. Keyword intelligence is a process: given the same inputs, two analysts running this skill should produce the same scoring, the same priority order, the same gap analysis. Every formula, every threshold, every classification rule is documented in the references for that reason.

### 5. Decision-grade outputs require traceable inputs

Every keyword in a final report should carry its provenance: which CSV file it came from, which row, which raw fields fed which derived metrics. Without traceability, output cannot be audited, and audit is what separates a recommendation from a guess. A skill that loses provenance produces beautiful reports that nobody can defend in front of a client.

### 6. Intent stratification beats intent labeling

Tools that assign a single intent label to each keyword (informational, navigational, transactional, commercial) compress a multidimensional signal into one tag. The skill keeps intent as a vector across at least four axes: query type, funnel stage, modality, and temporal layer. The composite is more informative than any single axis, and it survives the cases where a single query operates in two layers at once.

### 7. Priority and confidence are two scores, not one

A composite score answers «how attractive is this keyword». A confidence score answers «how reliable is this composite given the inputs available». A high-priority keyword with low confidence is a research target, not an action target. Conflating the two produces over-confident roadmaps and content calendars that fall apart on contact with reality.

## The five forces that shape a query

At least five forces shape a query. Any analysis ignoring one of them is operating on a flat projection of a multidimensional signal.

| Force | What it captures | Example |
|---|---|---|
| Language | Surface morphology, idiomatic phrasing, regional variation | «running shoes» vs «scarpe da corsa» vs «Laufschuhe» |
| Intent layer | Why the query was issued | Informational, navigational, transactional, commercial investigation |
| Modality | How the query was issued | Typed, voice, conversational AI, ambient |
| Funnel stage | Where the user is in their decision process | Awareness, consideration, decision, post-purchase |
| Temporal layer | When the query is asked relative to events | Evergreen, seasonal, event-driven, breaking |

The skill computes a position on each axis where the data allows it. Where the data does not allow it, the field stays empty rather than guessed. Empty is honest; guessed is noise that propagates through every downstream score.

## Vendor-neutrality as a methodological commitment

The skill accepts CSV exports from any major keyword research tool. This is not an engineering convenience. It is a methodological commitment with three operational consequences.

Each tool exports its own column set with its own metric definitions. The skill maps these to a canonical schema documented in [input-normalization.md](input-normalization.md). The canonical schema is the contract. Everything downstream operates on the canonical schema, never on the raw vendor schema.

When two tools report different values for the same keyword (volume, difficulty, CPC), the divergence stays preserved, not averaged. Averaging destroys signal. Preservation lets the analyst weight the source according to known characteristics: Semrush tends to report higher US volumes, Ahrefs tends toward more conservative difficulty estimates, GSC reports actual impressions for the analyst's own domain.

Scoring formulas operate on the canonical schema. A formula depending on a metric only one tool exports is a formula that breaks for users of every other tool. Such formulas are flagged and never used as primary signals; they may appear as enrichment when the tool is present, but the analysis runs without them.

## Reproducibility as the lower bound

Reproducibility is the lower bound of professional analysis. Two analysts running the skill on the same input must produce the same output. Three properties make this possible.

No probabilistic models, no random seeds, no machine learning inference. Every score is a function of the input and the documented formula. The skill is offline pure: no API calls, no external models, no network access during analysis.

Every classification (high difficulty vs low difficulty, branded vs non-branded, question vs statement, navigational vs informational) uses thresholds documented in the references and exposed as configurable parameters with clear defaults. The defaults are conservative; the analyst overrides them when the dataset characteristics warrant.

Changes to formulas or thresholds bump the methodology version. A report carries the version it was produced under. A reanalysis under a newer version is a different analysis, not the same one rerun. This convention prevents the silent drift that erodes trust in scoring systems over time.

## What this skill is not

The skill is precise about its scope.

It is not a keyword extractor. Tools like Semrush, Ahrefs, GSC, Moz, and Ubersuggest produce the raw exports. The skill consumes them.

It is not a rank tracker. Position data, when present in the CSV, informs analysis. The skill does not query SERPs, does not poll Google, and does not maintain a tracking history.

It is not a machine learning pipeline. The methodology is rule-based, transparent, and reproducible by hand for any single keyword. An analyst who disagrees with a score can recompute it on paper.

It is not a real-time system. Analysis runs on a static snapshot of CSV exports. The freshness of conclusions matches the freshness of the input.

It is not a black-box scorer. Every formula appears in [scoring-formulas.md](scoring-formulas.md). Every classification rule appears in [analysis-scopes.md](analysis-scopes.md). Every threshold has a default and a rationale.

## How insights become decisions

The output artifacts (Markdown report, JSON, enriched CSV, executive summary) exist to drive decisions. Three patterns occur consistently across client work.

The cluster and gap analysis drive architecture decisions. The output answers: which hubs exist in the demand graph, which hubs are unstaffed by current content, which hubs are staffed by competitors only. From those answers come pillar-and-spoke plans, site restructures, and content commission lists.

The quick-win and striking-distance scopes drive triage decisions. The output answers: which keywords are reachable inside one quarter with focused effort, which require structural changes that take longer, which are out of reach without authority growth. From those answers come content sprints and editorial calendars.

The AIO/GEO and intent scopes drive positioning decisions. The output answers: which queries route through generative engines, which require classical SEO, which require both. From those answers come decisions about llms.txt, schema markup priorities, and citation-readiness work on existing pages.

The composite score is a sorting tool, not a recommendation. The recommendation lives in the gap and scope analyses; the composite tells the analyst where to start reading.

## A note on terminology

This skill uses the following terms with specific meanings.

**Demand graph**: the structure of intents, topics, and entities reflected by a corpus of queries. Not a knowledge graph in the information retrieval sense; a working construct for prioritization.

**Scope**: a defined analytical lens applied to the keyword set (intent, cluster, AIO eligibility, and so on). The skill currently runs twelve scopes; see [analysis-scopes.md](analysis-scopes.md).

**Composite score**: a weighted aggregate of normalized signals, computed per keyword, in four variants (main, quick-win, strategic, AEO/defensive).

**Gap dimension**: a category along which a content portfolio can be missing relative to the observed demand. The skill identifies seven; see [scoring-formulas.md](scoring-formulas.md).

**Artifact**: one of the five output files produced by a run (Markdown report, JSON, enriched CSV, TXT executive summary, per-cluster content briefs). The structure of each appears in [output-artifacts.md](output-artifacts.md).

For unfamiliar acronyms, definitions appear inline in the file where the term is first used. The skill keeps no separate glossary because terminology that needs a separate glossary usually needs a clearer first occurrence in the text.

## Theoretical foundations

Three reference documents complement the operational files above by covering the theoretical ground on which the skill rests.

[semantics.md](semantics.md) covers the three semantics (formal, distributional, vector-space), the timeline from LSA to dense retrieval, word and sentence embeddings, the Google milestones (Hummingbird, RankBrain, BERT, MUM, AI Overviews, Gemini), passage ranking, query fan-out, and the methodological reasons the skill stays rule-based. An analyst evaluating the skill against modern semantic-search literature should read this file before challenging the design choices.

[clustering.md](clustering.md) covers the algorithmic families (partitional, hierarchical, density-based, distribution-based, graph-based), SERP-based clustering with thresholds and failure modes, embedding-based clustering with model choice and ANN libraries, hybrid clustering with multi-signal weighting, LLM-assisted clustering, cluster quality evaluation, and the roadmap toward an embedding-augmented v2 of this skill.

[entity-and-topical-authority.md](entity-and-topical-authority.md) covers the entity layer of modern SEO: the «strings to things» moment, NER and entity linking, named practitioners (Slawski, Volpini, Jones, Krum, Barnard, Scholz, Kopp, Gubur, Solis, King), Wikipedia and Wikidata pathways, schema.org as entity declaration, brand SERP optimization, AEO and GEO with the foundational and follow-up academic work, and how this skill's surface-level entity approximations relate to proper entity linking.

These three files are not required for operational use of the skill. They are required for an analyst who needs to defend the methodology against alternatives, who needs to plan a hybrid v2, or who needs to cite the relevant academic and patent literature in client deliverables.
