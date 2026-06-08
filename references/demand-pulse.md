# Demand Pulse

## Contents

- What it produces
- The series input, and why it is optional
- Trend: Mann-Kendall and Theil-Sen
- Momentum
- Seasonality (STL, optional)
- The per-cluster state
- Parameters
- Limitations

## What it produces

Demand Pulse classifies the demand trend of each cluster and writes
`modules.demand_pulse`: per cluster, a state (rising, declining, seasonal, flat,
or unknown), the trend statistics behind it, a momentum ratio, an optional
seasonal strength, and a marker-derived seasonal flag. It is a pure step and
changes nothing else.

The classification rests on a monthly volume series. The canonical engine state
carries one volume per keyword, not a series, so when no series is supplied every
cluster is reported as unknown and only the marker-derived flag is set. This is
the default behaviour on a volume-only corpus.

## The series input, and why it is optional

A keyword export records a single search volume per keyword, a snapshot. A trend
test needs the same quantity observed over time. That observation is not present
in a standard export, so Demand Pulse takes the series as a separate, optional
input rather than inventing one.

The series file is a wide CSV: a `keyword` column (or the first column) followed
by one column per month, each header in `YYYY-MM` form. Cells may be empty; an
empty cell drops that point for that keyword. Keywords are matched to the corpus
on a normalised form, so casing and spacing do not have to match exactly. The
series is an input, not derived state, so it never enters `run.json`; only the
computed results do.

Per cluster, the member keyword series are summed period by period into one
cluster series. Summing is the demand-weighted aggregation: a high-volume keyword
contributes proportionally more absolute volume to the cluster total.

## Trend: Mann-Kendall and Theil-Sen

Two non-parametric methods carry the trend, both reimplemented in the standard
library:

- The Mann-Kendall test gives the direction and whether it is statistically
  significant. It counts, over every pair of points, how often the later value
  exceeds the earlier one, standardises that count against its variance with a
  tie correction, and returns a two-sided p-value (Mann, H.B., 1945,
  "Nonparametric Tests Against Trend", Econometrica 13(3), 245-259; Kendall,
  M.G., 1948, "Rank Correlation Methods", Charles Griffin, London).
- The Theil-Sen estimator gives the magnitude. The slope is the median of the
  slopes between all pairs of points, which resists outliers far better than
  ordinary least squares (Theil, H., 1950, "A Rank-Invariant Method of Linear
  and Polynomial Regression Analysis", Proceedings of the Koninklijke
  Nederlandse Akademie van Wetenschappen 53, Part I 386-392; Sen, P.K., 1968,
  "Estimates of the Regression Coefficient Based on Kendall's Tau", Journal of
  the American Statistical Association 63(324), 1379-1389).

The test runs only when the cluster series has at least a minimum number of
points; below that a result is too noisy to trust and the cluster stays unknown.

## Momentum

Momentum is the recent window mean divided by the preceding window mean, minus
one: a short-horizon rate of change that complements the long-horizon slope. A
cluster can have a flat overall slope yet positive recent momentum, or the
reverse. It is reported only when the series is long enough to hold both windows.

## Seasonality (STL, optional)

Seasonal strength comes from an STL decomposition (Cleveland, R.B., Cleveland,
W.S., McRae, J.E., Terpenning, I., 1990, "STL: A Seasonal-Trend Decomposition
Procedure Based on Loess", Journal of Official Statistics 6(1), 3-33). The
strength is the measure of Wang, Smith and Hyndman (2006,
"Characteristic-Based Clustering for Time Series Data", Data Mining and Knowledge
Discovery 13(3), 335-364): `max(0, 1 - Var(remainder) / Var(seasonal +
remainder))`, bounded in [0, 1].

STL has no standard-library equivalent, so it sits behind an optional dependency
and runs only when that dependency is present and the series spans at least two
full periods. When it is absent, Demand Pulse skips seasonal strength and still
reports trend, momentum, and state from the standard-library methods. The output
records which backend produced each result.

Independently of the series, the engine assigns a marker-based seasonality label
from seasonal terms in the keyword itself (for example a holiday or an event
name). Demand Pulse surfaces this as `seasonal_marker`, kept separate and
labelled as marker-derived, never merged into the series-based state.

## The per-cluster state

The state is decided in order:

1. seasonal, when STL is available and the seasonal strength clears its cutoff;
2. rising, when Mann-Kendall is significant and the Theil-Sen slope is positive;
3. declining, when Mann-Kendall is significant and the slope is negative;
4. flat, when the series is long enough but no significant trend is found;
5. unknown, when there is no usable series for the cluster.

## Parameters

The significance level, the minimum series length, the momentum window, the
seasonal-strength cutoff, and the assumed period are parameters with documented
defaults, not facts from any source. They are overridable per run, and the
chosen values are recorded in the output so any result is reproducible from them.

## Limitations

The base Mann-Kendall test assumes independent observations. Monthly demand is
often autocorrelated, which can overstate significance; a variance correction for
autocorrelation is a future option, and the limitation is stated in the output.
The state describes the supplied series only: a short or sparse series yields
unknown rather than a guessed trend. Seasonal strength depends on the optional
decomposition; without it, a genuinely seasonal cluster may read as flat unless
its keywords carry a seasonal marker.
