# Live Wire capture guide

Live Wire is the opt-in path that brings observed data into a Querymantic run. It reads
one file, `livewire_capture.json`, and pairs the observed numbers with the offline
estimates already in the run. Nothing here runs by default and nothing leaves your
machine. Copy `livewire_capture.template.json`, fill the two blocks below, and pass
the file with `--livewire`.

Either block can be left out. Fill the one you have data for.

## Block 1: Search Console (observed clicks)

This block overrides Click Ceiling's modeled current clicks with your measured
clicks, and re-anchors the winnable band to what you actually earn today.

Where the data comes from: the Search Console **Performance report** (Search
results). Set your date range, open the **Queries** tab, and use the **Export**
button. The export carries five fields per query:

| Field | Meaning | Format in the export |
|---|---|---|
| Query | the search query | text (column may read "Top queries") |
| Clicks | clicks to your site from Search | whole number |
| Impressions | times your site appeared in Search | whole number |
| CTR | clicks divided by impressions | percent, for example `6.7%` |
| Position | average position of your topmost result | decimal, for example `3.2` |

Source for the field meanings: Google Search Console Help, "Performance report
(Search results)" and the Search Analytics API reference, where CTR is a value
from 0 to 1 and position is an average decimal.

Put each row under `search_console.rows`:

```json
{"query": "running shoes", "clicks": 2840, "impressions": 42500, "ctr": 0.067, "position": 3.2}
```

`ctr` may be pasted either as a fraction (`0.067`) or as the export's percent
string (`"6.7%"`); both are accepted. `position` is the decimal average. Empty
cells are read as missing, not as zero.

## Block 2: AI citations (observed citation share)

This block measures the share of AI-answer citations that point to your domain
against your competitors. Citation Grid can only estimate a within-portfolio
expected share offline; this is the measured share.

There is no export for this. You observe it by hand: run your queries on the AI
surfaces you care about (Google AI Overviews, Perplexity, ChatGPT, Gemini, Claude
with web search), and record which domains each surface cited. One row per query
per surface:

```json
{
  "query": "best running shoes",
  "surface": "perplexity",
  "observed_on": "2026-05-20",
  "citations": [
    {"domain": "yourdomain.com", "is_client": true},
    {"domain": "competitor1.com", "is_client": false}
  ]
}
```

`is_client` is optional: if you set `client_domain` at the top of the file, any
citation to that domain or a subdomain is recognized as yours automatically.

Keep the observations honest and dated. AI answer surfaces vary by session and by
personalization and are not reproducible, so treat the result as a sample, not a
guarantee.

## How the queries join

Live Wire matches each captured query to the keyword corpus by the same
normalization the engine uses, so casing and spacing do not matter. Queries that
do not match anything in the corpus are still counted in the portfolio totals and
are listed under `unmatched_queries`, so the coverage of your capture stays
visible.
