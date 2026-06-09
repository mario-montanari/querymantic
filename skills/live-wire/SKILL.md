---
name: live-wire
description: "Use when bringing observed data (Google Search Console clicks, AI-citation observations) into a run to compare measured against expected, opt-in. Triggers: observed clicks, Search Console import, GSC export, measured CTR, observed citation share, competitor citation split, live data overlay, expected vs observed, measured vs modelled."
user-invokable: true
argument-hint: "[inputs] [output] --livewire capture.json"
license: MIT
metadata:
  author: Mario Montanari
  version: "0.1.0"
  category: marketing
---

# Live Wire

## Overview

Live Wire is the only place observed data enters a run, and it never runs by default. It
reads one capture file and pairs the measured values with the offline estimates without
overwriting them, so expected and observed are visible side by side and never conflated.
It writes its own `live_wire` slot with `mode: observed`.

## When to use

- Real Search Console clicks exist and should override the modelled current clicks and
  re-anchor the winnable band.
- AI-surface citation observations exist and should give a measured citation share and
  the competitor split, which Citation Grid can only approximate offline.

## Run it

```bash
python scripts/querymantic_run.py run --inputs exports/ --output run.json \
  --modules entity_web fan_out_radar citation_grid click_ceiling live_wire \
  --livewire capture.json
```

It runs only when `--livewire` is passed. A paste template and guide are at
`forge/templates/livewire_capture.template.json` and
`forge/templates/livewire_paste_guide.md`; a sample capture is at
`assets/livewire/sample_capture.json`.

## What it writes

The `live_wire` slot: a `search_console` override (measured clicks, re-anchored winnable
band, impression-weighted average position) and an `ai_citations` override (demand-
weighted client citation share, competitor split summing to 100), each paired with its
expected counterpart. Queries that do not match the corpus are listed under
`unmatched_queries`. It leaves the offline slots byte-identical.

## Methodology

For the capture contract, the override mechanics, the expected-against-observed rule,
and the limitation that AI surfaces vary by session, see
[references/live-wire.md](../../references/live-wire.md).
