---
name: click-ceiling
description: "Use when estimating the band of winnable monthly organic clicks per cluster from CTR by position and SERP features, reporting a band and never a single number. Triggers: winnable clicks, click potential, CTR by position, SERP feature suppression, AI Overview suppression, traffic opportunity, click band, striking distance value, organic traffic estimate."
user-invokable: true
argument-hint: "[inputs] [output]"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Click Ceiling

## Overview

Click Ceiling reports a band of winnable monthly organic clicks per cluster, never a
single number, from a dated CTR-by-position table and SERP-feature adjustments. The band
widens where a CTR cell is filled by formula rather than confirmed by a source. It runs
offline and writes the `click_ceiling` slot.

## When to use

- A cluster needs a defensible traffic-opportunity figure that shows its uncertainty as
  a band, not false precision.
- A plan needs the winnable clicks split by intent and the top keyword opportunities.

## Run it

```bash
python scripts/spektr_run.py run --inputs exports/ --output run.json \
  --modules entity_web fan_out_radar citation_grid click_ceiling
```

The prior modules sharpen the band (Citation Grid readiness, Demand Pulse trend, Entity
Web authority, Fan-Out coverage), each optional and degrading. The CTR table is at
`data/ctr_table_2026Q2.json`, dated and with per-cell provenance.

## What it writes

The `click_ceiling` slot: per cluster, a `current_clicks_estimate`, a `ceiling_band`, a
`winnable_band`, the SERP and AI-Overview pressures, the prior-module `adjusters`
applied, the `top_opportunities`, and a `position_provenance_mix`. A run-level summary
totals the winnable band and splits it by intent.

## Methodology

For why a band, the dated CTR table and its provenance, the per-keyword estimate, the
SERP and AI-Overview adjustments, and the parameters, see
[references/click-ceiling.md](../../references/click-ceiling.md).
