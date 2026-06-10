# Fan-Out Radar

## Contents

- What it produces
- The seven archetypes
- Coverage (expected, offline)
- Gatekeeper queries
- The sub-query count
- Limitations

## What it produces

Fan-Out Radar models how a head query fans out into the sub-queries a generative
search system would explore, then measures how well each cluster's keywords already
cover that fan-out. It writes `modules.fan_out_radar`: per cluster, the generated
sub-queries with their coverage, the Cover@tau score, the missing archetypes, and the
gatekeeper queries. It is a pure step and changes nothing else.

It runs fully offline. With no content corpus, the cluster's own keywords are the
documents, so the coverage is an expected coverage, not an observed one. The `mode`
field records this.

## The seven archetypes

The sub-query archetypes follow Mike King's account of AI Mode fan-out (iPullRank,
2025): related, implicit, comparative, recent, personalized, reformulation, and
entity-expanded. Each is generated deterministically:

- Related: the head plus a co-occurrence neighbor from the Entity Web graph, or a
  frequent cluster token when the graph is absent.
- Implicit: a question word (what, why, how, when) plus the head.
- Comparative: the head versus the most similar sibling cluster heads.
- Recent: the head plus a year token around the reference year.
- Personalized: only from explicit audience signals, which the offline corpus does
  not carry, so it is skipped here by design.
- Reformulation: a head token swapped for a synonym from a small bundled gazetteer.
- Entity-expanded: a neighbor entity's distinctive token paired with the head noun.

Archetypes are merged round-robin under a per-cluster cap so the set keeps its
diversity.

## Coverage (expected, offline)

Each sub-query is scored against the cluster's keyword documents with BM25 (Lucene
defaults k1 = 1.2, b = 0.75). The coverage threshold tau is the median of the
per-sub-query best scores in the cluster. A sub-query is covered when its best score
is at or above tau. Cover@tau is the covered fraction, and the missing archetypes are
those with no covered sub-query: the gaps the cluster's content does not yet answer.

## Gatekeeper queries

A gatekeeper query is an internal term for a sub-query that is central to the
fan-out, because several of the cluster's keywords answer it, yet has no originating
search volume. Nobody types it, but a content set has to answer it to enter the
candidate pool. Detection is deterministic: a sub-query is a gatekeeper when at least
a set number of cluster keywords score it above tau and its exact form matches no
keyword with volume.

## The sub-query count

A real fan-out is often quoted as producing eight to twelve sub-queries. That figure
is a secondary industry estimate, not a number from any search-engine source. Here it
is only a configurable cap on how many sub-queries to generate per cluster, and it is
labeled as such in the output.

## Limitations

Offline simulation cannot reproduce the stateful, personalised fan-out a live system
performs. Coverage is expected, derived from the keyword set itself; pasted real
sub-queries or a content corpus would turn it into observed coverage. Engine-specific
archetype weighting is available as a configuration but defaults to uniform, since
engines change their behavior without notice.
