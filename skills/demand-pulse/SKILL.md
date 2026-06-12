---
name: demand-pulse
description: "Use when classifying clusters as rising, declining, seasonal, or flat from a monthly volume series, or reading demand trend, momentum, and seasonal strength. Triggers: demand trend, seasonality, rising keywords, declining keywords, momentum, Mann-Kendall, Theil-Sen, trend classification, monthly volume series, seasonal demand."
user-invokable: true
argument-hint: "[inputs] [output] --series series.csv"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.2.0"
  category: marketing
---

# Demand Pulse

## Overview

Demand Pulse classifies each cluster as rising, declining, seasonal, flat, or unknown
from a monthly volume series, using Mann-Kendall for direction and significance,
Theil-Sen for the slope, a momentum ratio, and an optional STL seasonal strength. It
runs offline and writes the `demand_pulse` slot.

## When to use

- A monthly series exists and clusters need a trend state and momentum, not a single
  volume snapshot.
- A plan needs to separate genuinely rising demand from seasonal swings.

## Run it

The canonical run-state carries volume only, so the series is an optional second input:
a wide CSV with a `keyword` column plus `YYYY-MM` columns.

```bash
python scripts/querymantic_run.py run --inputs exports/ --output run.json \
  --modules demand_pulse --series series.csv
```

Without `--series`, every cluster is classified `unknown` (honest, not guessed). A
sample series is at `assets/series/sample_series.csv`.

## What it writes

The `demand_pulse` slot: per cluster, the `state`, the Mann-Kendall statistics, the
Theil-Sen slope, the momentum ratio, the STL seasonal strength when `statsmodels` is
installed, and a separate marker-derived `seasonal_marker` flag kept distinct from the
series-based state.

## Methodology

For the statistical methods, the autocorrelation caveat, the optional STL path, and the
classification thresholds, see [references/demand-pulse.md](../../references/demand-pulse.md).
