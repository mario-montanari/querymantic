# Click Ceiling

## Contents

- What it produces
- Why a band and not a number
- The dated CTR table and its provenance
- The per-keyword click estimate
- SERP-feature adjustment
- AI Overview suppression and recovery
- The winnable band
- How the prior modules sharpen the band
- Parameters
- Limitations

## What it produces

Click Ceiling writes `modules.click_ceiling`: per cluster, an estimate of the
current organic clicks, a ceiling band, a winnable-clicks band, the SERP and
AI-Overview pressures in play, the prior-module adjustments applied, and the top
keyword opportunities. A run-level summary totals the winnable band and splits it
by intent. It is a pure step and changes nothing else.

## Why a band and not a number

A single click-through-rate curve is a crude approximation. Real CTR varies by
intent, brand, device, and industry, and the realistic target rank for a cluster
is itself a range, not a point. Reporting one number would hide that uncertainty
behind false precision. So every click figure that depends on an improved rank is
reported as a low-to-high band. The width of the band is not decorative: it grows
when the underlying CTR cell is filled by formula rather than confirmed by a
source, and when the realistic rank target spans a wider range.

## The dated CTR table and its provenance

The table lives in `data/ctr_table_2026Q2.json`. It is dated and carries a source
record, and every cell is labelled with how it was obtained:

- `confirmed`: an exact value stated in the primary source. The anchor positions
  1, 2, 3, and 10 carry SISTRIX's published average mobile CTRs (28.5%, 15.7%,
  11.0%, 2.5%), from Johannes Beus, "Why (almost) everything you knew about
  Google CTR is no longer valid", SISTRIX, 14 July 2020, over 80 million
  keywords.
- `interpolated`: positions 4 to 9, filled by a monotone log-linear curve between
  the confirmed anchors at 3 and 10. Not a source value.
- `extrapolated`: positions 11 to 20, the same log-linear decay extended past the
  last confirmed anchor. Not a source value.
- `derived`: the SERP-feature factors, computed from SISTRIX's published
  position-1 CTRs under each SERP layout (for example 23.3% with a featured
  snippet against the 28.5% average, the documented 5.3 percentage-point drop).

A fuller public position 1 to 20 curve exists (Advanced Web Ranking, updated
monthly from Google Search Console), but it is served from an interactive chart
whose per-position numbers were not capturable as text, so the confirmed anchors
come from SISTRIX. Users can supply their own table; the shape and the provenance
labels are all that the module requires.

## The per-keyword click estimate

For a keyword with a search volume and a current rank, the estimated clicks are
`volume x CTR(rank | SERP features)`. A keyword with no recorded rank is treated
as unranked: its current clicks are zero and its whole ceiling is winnable, which
is the honest reading of a high-volume term the client does not yet rank for.

## SERP-feature adjustment

SERP features that take clicks away from the organic result lower the CTR. The
module applies the single strongest suppression among the present features, taken
from the derived factors, rather than multiplying several uncertain factors
together and compounding the error. Features without a confirmed factor (People
Also Ask, local pack, video, news, images) carry a factor of 1.0 and are marked
unmeasured: no penalty is invented for them, and the band absorbs the unknown.

## AI Overview suppression and recovery

On a query that triggers an AI Overview, the organic click-through rate is
suppressed. The factor comes from Seer Interactive's September 2025 analysis of
3,119 informational queries across 42 organizations: organic CTR on AI-Overview
queries fell 61% (from 1.76% to 0.61%), so the baseline organic multiplier is
0.39. The same study found that pages cited inside an AI Overview earned 35% more
organic clicks than uncited pages on the same result page, so a page that is
answer-ready and cited recovers part of the loss, up to a 1.35 factor over the
suppressed baseline. The scope is informational queries; the figure is not
generalised verbatim to commercial intent.

The current-clicks estimate assumes no recovery, since the page is not cited yet.
The optimistic end of the winnable band lets the recovery apply, scaled by the
cluster's citation readiness from the Citation Grid module.

## The winnable band

Winnable clicks are the extra clicks a cluster could capture by improving its
rank, summed over the keywords:

- The optimistic endpoint targets rank 1 and lets the AI-Overview recovery apply.
- The conservative endpoint targets rank 3 (never worse than the current rank)
  with no AI-Overview recovery.
- A keyword whose current rank sits on an interpolated, extrapolated, or unranked
  cell widens its own band, so weaker verification shows up as a wider range.

The cluster ceiling band is the current clicks plus the winnable band. The
run-level summary totals the winnable band across clusters and by dominant intent.

## How the prior modules sharpen the band

Each prior module is optional; without it the module degrades rather than breaks.

- Citation Grid readiness sets how much of the AI-Overview suppression the
  optimistic endpoint recovers. A cluster that is answer-ready recovers more.
- Demand Pulse trend lifts the upper endpoint on rising demand and trims both
  endpoints on declining demand.
- Entity Web topical authority leans the band: high authority keeps the rank-1
  target credible; low authority trims the upper endpoint.
- Fan-Out Radar coverage trims the upper endpoint on AI-heavy clusters whose
  sub-query family is poorly covered, since the answer surface captures clicks
  before the open web.

Every adjustment is recorded per cluster with its factor and its basis, so the
band can be traced back to the signals that shaped it.

## Parameters

The target-rank range (optimistic rank 1, conservative rank 3), the per-slot
adjustment factors, the credibility floors, and the CTR-cell uncertainty widths
are project parameters with documented defaults, not facts from any source. They
are overridable per run, and the chosen values are recorded in the output.

## Limitations

The CTR table is a mobile, cross-intent average; a single curve cannot capture
how CTR shifts by intent, brand, device, and industry, which is why the result is
a band and why a user-supplied table is supported. The positions between the
confirmed anchors are modelled, not measured. The AI-Overview figures come from
one informational-query panel and are treated as a prior with a stated scope, not
a universal constant. The estimate is offline and demand-side: it models the
clicks a rank could earn, not the work required to reach that rank. Observed
clicks, when available from Search Console through the optional Live Wire path,
override these expected figures.
