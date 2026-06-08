# Citation Grid

## Contents

- What it produces
- Why it is offline and expected
- The six citability components
- The readiness blend
- Expected share, and what it is not
- The structural-signal checklist
- Parameters
- Positioning
- Limitations

## What it produces

Citation Grid estimates how ready each cluster is to be cited by AI answer
surfaces (Google AI Overviews, ChatGPT search, Perplexity, Gemini, Claude with
web search) and turns the estimate into concrete editorial actions. It writes
`modules.citation_grid`: per cluster, an expected citation-readiness from 0 to
100, the inputs behind it, an expected share of the client portfolio, and a
six-item structural-signal checklist. It is a pure step and changes nothing else.

It reads the Fan-Out Radar and Entity Web slots when they are present and degrades
gracefully without them. The engine scopes alone are enough to produce a readiness
estimate.

## Why it is offline and expected

The module runs with no content corpus. There is no passage text to read, so it
cannot measure a real passage. Every figure it reports is labelled `expected`,
never `observed`. The split matters: a score that depends on signals unavailable
offline has an expected (offline) form and an observed (Live Wire) form, and the
two are never mixed.

An observed citation share, and the competitor split, cannot be computed offline.
The run-state carries no competitor domains, so there is nothing to count. That
measurement belongs to the optional Live Wire path, which consumes pasted AI
answers and overrides the expected figures with observed ones.

## The six citability components

Citability is decomposed into six components, drawn from the public record on what
generative engines select:

- **Extractability.** A section that opens with a short, self-contained answer is
  the unit an engine lifts. Question-form subheadings are more retrievable than
  noun labels.
- **EntityCoverage.** Engines reason about entities; explicitly named and defined
  entities are cited more often.
- **StructuredSignals.** Tables, ordered lists, explicit statistics with units,
  and quotations are parsed and cited more readily than prose. In the GEO study of
  Aggarwal et al. (arXiv:2311.09735; KDD 2024, DOI 10.1145/3637528.3671900), the
  two highest-performing tactics were adding statistics and adding quotations.
- **InformationGain.** Content that adds information beyond the competing pages is
  favoured. This mirrors Google's "Contextual estimation of link information gain"
  patent family (US11354342B2 and its continuations US11720613B2, US12013887B2,
  US12326889B2; inventors Carbune and Gonnet Anders). The offline approximation of
  novelty follows the temporal-IDF method of Karkali et al. (arXiv:1401.1456).
- **FreshnessProxy.** A visible, recent date helps, more so when demand is moving.
- **SourceCues.** Citing authoritative sources, a credentialed author byline, and
  Organization schema signal trustworthiness to retrieval-augmented systems.

Two of the six, InformationGain and SourceCues, can only be measured on real
passage text. Offline they are checklist-only: they shape the actions but carry no
number. The other four have a demand-side signal in the run-state and feed the
readiness number.

## The readiness blend

Readiness is a weighted mean of the inputs that have a value offline, rescaled to
0 to 100. The inputs:

- **Eligibility.** The engine's AIO eligibility scope scores, from 0 to 100,
  whether a query is the kind that triggers an AI answer surface. A query also
  routed to a GEO opportunity (cited by third-party generative engines even when
  Google shows no AI Overview) is nudged up. This is the surface gate: it asks
  whether an AI answer is shown for the cluster at all.
- **Query family.** The Fan-Out Radar coverage of the sub-query family for the
  cluster. Citation in a fan-out world goes to content that answers the sub-queries,
  not just the head query.
- **Entity coverage.** The Entity Web topical authority for the cluster, the
  demand-weighted share of its entities the client already owns.
- **Extractability.** The share of the cluster's keywords that are answer-shaped
  (a question, a People-Also-Ask term, or a featured-snippet SERP feature). A
  cluster whose demand is already answer-shaped has more passage handles to win.
- **Structured demand.** The share of the cluster's keywords whose SERP shows a
  structure-rewarding feature (featured snippet, People-Also-Ask, shopping).
- **Freshness.** Present only when Demand Pulse has run: a rising or seasonal
  cluster raises the freshness signal. Absent otherwise.

Each input carries a base weight. When an input has no value (an upstream module
did not run, or Demand Pulse is absent), it is dropped and the remaining weights
are renormalised, so the score degrades rather than breaking. Eligibility,
extractability, and structured demand come from the engine scopes, which are always
present, so a readiness is produced even when no other module has run. The output
records each input's value, base weight, and effective weight, so any figure is
auditable.

## Expected share, and what it is not

The expected share weights each cluster's readiness by its demand and normalises
the result to sum to 100 across the client's own clusters. It is a within-portfolio
priority signal: where, across the client's topics, citation readiness and demand
coincide. A cluster with no demand contributes no share even when its readiness is
high.

It is not a competitor share. It does not claim a percentage of the citations on
any engine. It is not observed. The observed competitor share is a Live Wire
output, computed from pasted AI answers, and is the figure that overrides this one
when real data is available.

## The structural-signal checklist

Every cluster carries a six-item checklist, one item per component, built from the
run-state:

1. **Extractability.** Open each section with an answer of 25 words or fewer. The
   examples are the cluster's own answer-shaped queries.
2. **EntityCoverage.** Name and define the cluster's entities; close the owned-gap
   entities first. The examples come from the Entity Web gaps and entities.
3. **StructuredSignals.** Add a table or list and an explicit statistic. The
   examples are the structure-rewarding SERP features present for the cluster.
4. **InformationGain.** Answer the gatekeeper sub-queries no one targets and the
   missing fan-out angles. The examples come from Fan-Out Radar. Flagged as needing
   passage text.
5. **FreshnessProxy.** Show a visible date; refresh on a cadence that matches the
   demand trend, which is named when Demand Pulse has run.
6. **SourceCues.** Cite authoritative sources, add a credentialed byline, and
   Organization schema. Flagged as needing passage text.

## Parameters

The six input weights and the number of checklist examples are parameters with
documented defaults, not facts from any source. Their spirit follows the published
citability components, adapted to demand-side signals because there is no passage
text offline. They are overridable per run, and the chosen values are recorded in
the output so any result is reproducible from them.

## Positioning

Citation readiness measures extractable structure: answer-shaped passages, named
entities, statistics, citations, and structured data. These operate through
ordinary indexing. Google's own guidance is explicit that no special markup, no
AI-specific files, and no AI-specific optimisation are required to appear in
generative AI search. Citation Grid is therefore rigor on structure a content team
can control, not a secret channel into any model.

## Limitations

Offline, the readiness is an estimate from demand-side signals, not a measurement
of any passage. Two of the six components are checklist-only without passage text.
The novelty approximation behind InformationGain is corpus-relative, while the
patented signal it mirrors is contextual and user-history dependent; the offline
form captures only the corpus-relative part. The eligibility input rests on the
engine's scopes, which are themselves heuristic. The expected share is bounded by
the supplied keyword set and is a within-portfolio distribution, never a competitor
share. Observed figures require the Live Wire path.
