# Entity Web

## Contents

- What it produces
- The entity extractor
- Ownership and demand
- Co-occurrence graph
- Entity gaps
- Topical authority
- Limitations

## What it produces

Entity Web reads the engine analysis in `run.json` and writes an entity layer to
`modules.entity_web`: a ranked entity list, a co-occurrence graph, the entity gaps,
and a topical-authority score per cluster. It is a pure step and changes nothing
else in the run-state.

## The entity extractor

Entities are surface terms drawn from the keyword phrases, not knowledge-graph
nodes. The extractor is interchangeable; the default is `tfidf_position`, an own
scorer built from first principles:

- Each keyword phrase is a short document. Tokens are lowercased word characters of
  length two or more; grammatical function words are removed with a per-language
  stop list.
- Candidates are unigrams and bigrams from runs of adjacent non-stopword tokens.
- For each candidate the extractor computes term frequency, document frequency,
  inverse document frequency, and a head-position factor (the mean of `1 / (1 + i)`
  over the documents, where `i` is the index of the term's first token).
- Ranking salience is `df * position_factor`. On a keyword corpus the central
  entities are common by design, so inverse document frequency is reported for
  per-cluster distinctiveness but is not used to rank, which would penalise the very
  entities that define the topic.

A term must appear in at least `min_df` documents (default two) to count, which
drops one-off noise. The interface leaves room for a clean-room keyword-extraction
algorithm and an opt-in embedding-based extractor without changing the modules.

## Ownership and demand

An entity's demand is the sum of search volume over the keywords that contain it. An
entity is owned when the analyzed domain ranks for at least one of those keywords,
inferred from a present ranking position at or above the threshold (default top 20).

## Co-occurrence graph

Two entities are linked when they share at least one keyword; the edge weight is the
number of shared keywords. The graph keeps the top entities by salience to stay
compact, and each node carries its weighted degree. Community detection is left to an
optional graph backend.

## Entity gaps

An entity gap is a demand entity the client does not own. Gaps are ranked by demand
and each carries the cluster where its keywords concentrate, so the finding maps to a
place to act.

## Topical authority

Per cluster, topical authority is the demand-weighted share of the cluster's entities
that are owned, between zero and one. The demand figures are sums of per-entity
demand, not cluster search volume, so the ratio is the signal and the absolute sums
only weight it.

## Limitations

Entities are surface forms, so the same entity can appear under variants. Authority
is corpus-bounded: it describes coverage relative to the provided keyword set, not
absolute search authority. Where ranking position reflects a competitor rather than
the client, ownership is read from the data as provided; supplying Search Console
data sharpens it.
