# Live Wire

## Contents

- What it produces
- Why a separate, opt-in path
- The capture file
- Search Console override: measured clicks
- AI citations override: measured citation share
- Expected against observed
- Joining the capture to the corpus
- Limitations

## What it produces

Live Wire writes `modules.live_wire`: an observed overlay that pairs measured data
with the offline estimates already in the run. It has two override blocks, each
optional. The Search Console block turns modelled current clicks into measured
current clicks and re-anchors the winnable band. The AI-citations block turns the
within-portfolio expected citation share into a measured share of real citations,
with the competitor split. It is a pure step and changes nothing else; the offline
slots are left exactly as their modules wrote them.

## Why a separate, opt-in path

Every other module in the suite is offline and deterministic: the same input gives
the same output, with no network and no live surface. That property is worth
protecting. Observed data breaks it by definition, because a click count or an AI
citation is a measurement taken at a moment, not a calculation. So observed data
lives behind its own opt-in step that runs only when a capture file is supplied,
and it writes its own slot rather than editing the offline ones. The run stays
honest about which numbers are modelled and which are measured.

## The capture file

Live Wire reads one file, `livewire_capture.json`, described for the analyst in
`forge/templates/livewire_paste_guide.md`. It carries a `client_domain` and up to
two blocks, `search_console` and `ai_citations`. At least one block must be
present. The file is an input, like Demand Pulse's monthly series: it is never
written into `run.json`; only the computed comparison is.

The parser is tolerant where the source format varies. A click-through rate is
accepted both as the Search Console export's percent string (`6.7%`) and as the
API fraction (`0.067`); a trailing percent sign divides by 100. An empty cell is
read as missing, never silently as zero.

## Search Console override: measured clicks

Source: the Google Search Console performance report. Per query it reports clicks,
impressions, click-through rate, and the average position of the topmost result
for the site. Clicks and impressions are counts; the rate is clicks divided by
impressions, a value from 0 to 1; the position is an average decimal. These
definitions are from Google Search Console Help and the Search Analytics API
reference.

Live Wire joins each captured query to the keyword corpus and aggregates per
cluster:

- **Measured current clicks**: the sum of the matched queries' clicks. This is the
  measured counterpart to Click Ceiling's modelled `current_clicks_estimate`.
- **Average position**: impression-weighted across the matched queries, so a
  high-impression query carries more of the cluster's position than a marginal one.
- **Re-anchored winnable band**: the ceiling endpoints stay as Click Ceiling
  modelled them, since they describe the reachable rank range, not today's
  performance. The winnable band becomes the ceiling minus the measured current,
  floored at zero. A cluster already capturing most of its ceiling shows a smaller
  winnable band than the offline estimate assumed, which is the point.

When Click Ceiling has not run, the block still reports measured current clicks per
cluster but forms no band, since there is no ceiling to anchor against.

## AI citations override: measured citation share

Offline, and with no competitor domains anywhere in the run-state, a true citation
share cannot be measured: Citation Grid reports only a within-portfolio expected
share, a demand-weighted priority across the client's own clusters. Live Wire
measures the real thing from observation.

Each observed query carries a weight equal to its search volume, or one when the
query is not in the corpus. Within a query, every citation carries an equal
fraction of that weight, so across the capture the client's share and every
competitor's share sum to 100. The portfolio figures are computed over all
observed queries; the per-cluster figures over the queries that map to each
cluster. The competitor split lists domains by their weighted share, with the
longest tail folded into a single `other` entry.

## Expected against observed

The two kinds of number are never blended. Each cluster in the overlay carries the
observed value next to the expected one it corresponds to, so a reader can see both
and judge the gap. A downstream consumer reads observed when it is present and
falls back to expected otherwise. The expected slots themselves are untouched, so a
run with and without a capture differ only in the presence of the `live_wire` slot.

## Joining the capture to the corpus

Queries match the corpus by the engine's own normalisation (lowercasing and
tokenisation), so casing and spacing do not matter. A query that matches nothing is
still counted in the portfolio totals and is listed under `unmatched_queries`, so
the coverage of a capture is always visible and a thin capture cannot masquerade as
a complete one.

## Limitations

- **Observed data is a sample.** AI answer surfaces vary by session and by
  personalization and are not reproducible. A citation share is the share seen in
  the captured observations, not a guarantee of future behaviour.
- **Coverage is the analyst's responsibility.** Live Wire measures only what the
  capture contains. The unmatched lists and the matched-query counts make the
  coverage auditable, but they cannot fill a sparse capture.
- **Position is an average.** Search Console reports the average position of the
  topmost result, which blends every impression in the range and every device, so a
  single decimal hides real variance.
