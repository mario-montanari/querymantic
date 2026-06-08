# AIO and GEO optimization

This file covers the operational patterns for AI Overviews (Google AIO) and generative engines (GEO). For the academic foundations (the GEO-bench paper by Aggarwal et al. KDD 2024, the AgentGEO follow-up, the Toronto study on earned-media bias, the GEO-16 framework, the UC Berkeley Search Arena work) and for the practitioner reference map, see [entity-and-topical-authority.md](entity-and-topical-authority.md). For the semantic-retrieval mechanisms that make AI Overviews and generative engines work (BERT, MUM, Gemini, dense retrieval, query fan-out), see [semantics.md](semantics.md).

## Contents

- The three search experiences
- AI Overviews (Google AIO)
- Generative engines (Perplexity, ChatGPT, Claude, Gemini)
- Query fan-out
- Citation readiness
- The llms.txt protocol
- AI crawler accessibility
- Brand mention signals
- Passage-level citability
- Routing recommendations per scope output
- Operational checklist

## The three search experiences

A keyword in 2026 can route to three distinct search experiences, and the same query often routes to more than one depending on the user's surface. The skill treats these as separate optimization problems rather than as variations of one problem.

Classical SERP. The user types into Google or Bing, sees ten blue links plus SERP features. Optimization here is the SEO most analysts know: page-level on-page work, internal linking, technical SEO, backlinks, schema markup. The skill's quick-win, striking-distance, and content-gap scopes target this experience.

AI Overviews (AIO). The user types into Google, and Google synthesises an answer drawn from multiple ranked sources, displayed above the blue links. The user may or may not click through. Optimization here is partly classical SEO (you must rank in the underlying retrieval to be a candidate source) and partly answer-engine optimization (your content must be structured so the answer extractor finds extractable, citable passages).

Generative engines. The user prompts ChatGPT, Perplexity, Claude, or Gemini directly. The model retrieves and synthesises sources or relies on training data, depending on the engine. Optimization here is GEO: making sure your content is reachable by AI crawlers, structured for passage-level extraction, and represented in the brand-mention graph that LLMs use as priors.

The skill's AIO eligibility scope (3) targets the second experience. The GEO opportunity scope (4) targets the third. Together they identify the queries that should not be optimized only for classical SERP.

## AI Overviews (Google AIO)

Google AI Overviews appear on a subset of queries Google judges to be informational, comparative, or how-to in nature. Eligibility is not stable: Google has expanded and contracted the surface multiple times, and the share of queries triggering an AI Overview varies by topic, market, and user signal.

What gets cited. AI Overviews draw from sources that already rank in the underlying retrieval (Google's index), passing them through an extractor that prefers content with clear, self-contained, declarative passages. A well-ranked page that buries its answers under marketing prose is less likely to be cited than a less-ranked page that opens with a direct answer.

Operational implications. To be a candidate AIO source, a page must rank well enough to be retrieved (classical SEO matters). To be the cited source, a page must contain extractable passages that answer the query directly. Two structural patterns improve passage extractability:

1. Lead the section with the answer in 1-3 sentences, then expand. The extractor reads the opening of each section first.
2. Structure with H2/H3 subheadings that match the question shape. A subheading «How long does X take» followed by a 2-sentence answer is highly extractable.

What suppresses citation. Marketing-style openers («In today's fast-moving world…»), buried answers, and walls of text without clear question-shaped subheadings. Pages that fail extractability tests still rank in the blue links but rarely show up in the AI Overview.

The skill flags every keyword in the corpus where AIO eligibility scores ≥ 60. The recommendation for those keywords is twofold: rank well enough to be retrieved (the classical scoring path) and structure the supporting page for passage extraction (the structural recommendations live in the action class assigned by gap analysis).

## Generative engines (Perplexity, ChatGPT, Claude, Gemini)

The four major generative engines treat sources differently from each other and from Google.

Perplexity is the closest to a classical search engine wrapped with an answer model. It uses live retrieval, cites sources by URL with footnotes, and ranks sources roughly by retrieval relevance and domain authority signals. Optimization for Perplexity overlaps significantly with classical SEO and with AIO optimization.

ChatGPT search (and the equivalent in Claude and Gemini when their search modes are enabled) does live retrieval but with different retrieval mechanisms and different citation styles. ChatGPT search has been observed to favor sites with explicit structured content (schema markup, well-formed Q&A sections) and clear E-E-A-T signals.

ChatGPT without search mode (and any LLM in pure-generation mode) draws from training data. Visibility here depends on having been mentioned and cited across the web by the time the model was trained. The brand-mention graph matters: how many third-party sources reference the brand or topic, in what contexts, with what verbal patterns. This is GEO at its purest: a slow-moving optimization that rewards being talked about authoritatively across the web.

Gemini integrates with Google's index but applies different ranking and extraction logic than classical SERP or AI Overviews. Optimization is partially shared with AIO and partially distinct.

The skill's GEO opportunity scope identifies keywords that are characteristic of generative-engine queries: long, conversational, multi-clause, often containing imperatives or comparatives. These keywords benefit from optimization on three axes: content structure (passage extraction), crawl accessibility (the engines must be able to reach the page), and brand mention signals (the engines must already know the brand).

## Query fan-out

Generative engines decompose a single user prompt into multiple sub-queries before retrieval. A user prompt like «what's the best running shoe for marathon training under $200» is split into sub-queries that may include «best running shoes for marathon», «running shoes under $200», «marathon training shoe recommendations», and so on. The engine retrieves for each sub-query, synthesises across the retrieved sources, and produces one answer.

Implications for keyword intelligence. A keyword corpus optimized only for the head form of the user's prompt will miss the sub-queries. The skill's GEO opportunity scope flags long-tail conversational keywords as candidates, and the corpus expansion phase (Stage 1, sourcing) explicitly includes generative AI sourcing as a category to capture these sub-query forms.

Operational tactic. When optimizing a page for a head term that is a likely user prompt, plan the page so it visibly contains content that maps to the predictable sub-queries. A page about «marathon training shoes under $200» should explicitly address budget options, marathon-specific features, and (in a clear sub-section) the comparison with mid-range and premium options. Each predictable sub-query gets its own extractable section.

## Citation readiness

A page is citation-ready when a generative engine can extract a self-contained passage that answers the query and attribute it to the source. Five properties improve citation readiness.

Self-contained passages. Each section should answer its question without forward or backward references. A section that says «as we'll see below» or «as discussed in the previous section» is harder to cite because the citation context is incomplete.

Explicit factual claims. Specific numbers, dates, named entities, and concrete examples cite better than vague claims. «Marathon training plans typically last 16-20 weeks» cites better than «marathon training plans take a long time».

Source-traceable claims. Claims that link to or name their source («according to a 2025 USATF survey…») cite more reliably because the engine can verify and reinforce the citation chain.

Schema markup. Article schema, Q&A schema, and HowTo schema give the engine machine-readable hooks for the content's structure. Schema is not a magic bullet, but its absence makes extraction harder.

Headings that match question shapes. Subheadings phrased as questions create natural extraction units. The engine reads the question, finds the answer in the next 1-3 sentences, cites the page.

The action class assigned by gap analysis (`create`, `update`, `restructure`) takes citation readiness into account: a `restructure` action on a high-GEO-opportunity keyword frequently means «rewrite the page to be citation-ready» rather than «rebuild the URL hierarchy».

## The llms.txt protocol

llms.txt is a proposed standard, modeled on robots.txt, for sites to publish a machine-readable summary of their content for AI consumption. A site publishes a `/llms.txt` file at the root listing its high-value pages, key topics, brand information, and citation preferences. Generative engines (those that respect the protocol) read this file when they encounter the site.

Adoption is uneven. As of the methodology version cutoff, Anthropic, Stripe, Cloudflare, and a growing list of sites publish llms.txt. The protocol has not been universally adopted by all generative engines, and its exact effect on citation rates is debated.

Operational stance. Publishing llms.txt is low cost. The skill recommends publication for any site whose corpus contains a non-trivial share of GEO-opportunity keywords. The structure of llms.txt should mirror the cluster architecture identified by the skill's cluster scope: each major cluster gets a section in llms.txt with links to the cluster's hub and key spokes.

A separate `/llms-full.txt` or `/llms-large.txt` can host a long-form summary of the entire site for engines that consume larger context. The skill does not generate these files, but the gap analysis output identifies which clusters and which entities deserve a place in them.

## AI crawler accessibility

Generative engines crawl with named user agents distinct from classical search crawlers. The major ones to consider:

- `GPTBot` (OpenAI)
- `ClaudeBot` (Anthropic)
- `PerplexityBot` (Perplexity)
- `Google-Extended` (Google's signal for AI training opt-in)
- `CCBot` (Common Crawl, used by many model providers as a training data source)

A site that blocks these user agents in robots.txt removes itself from generative-engine retrieval and from training data ingestion. A site that allows them but has slow response times, frequent error pages, or aggressive rate-limiting suffers reduced effective coverage.

The skill does not crawl the live site, so it cannot verify accessibility directly. It does flag, in the GEO gap output, when the analyst should run a manual check: a site with a high share of GEO-opportunity keywords that has not confirmed AI crawler accessibility is at structural risk.

## Brand mention signals

Generative engines use brand mention patterns as priors when synthesising answers. A brand cited frequently and authoritatively in a topic space gets recommended in queries adjacent to that space, even when no exact-match retrieval surfaces the brand. This is the slow-moving optimization that classical SEO never had to think about.

What counts as a high-quality brand mention. References from sites the model treats as authoritative for the topic (Wikipedia for many topics, recognized industry publications, regulatory bodies, academic sources). Brand mentions in named-entity contexts: «Brand X, the maker of Y, is one of the leaders in Z». Brand mentions in comparative contexts: «Brand X versus Brand Y» tables.

What does not move the needle much. Self-published content on the brand's own site (the engines already know the brand owns the site). Press releases distributed without earned coverage. Mass-produced guest posts on low-trust sites.

Operational stance for keyword intelligence. The skill's entity gap dimension surfaces entities the corpus references that the client does not own. Two patterns matter most for brand mention work:

1. Entities that frequently co-occur with the client's category but where the client is absent. These are the missed contexts: the client should be mentioned alongside competitor X when industry articles list category players, and is not.
2. Entities the client is named alongside in the client's own content but not in third-party content. These reveal contexts the client has tried to claim and where third-party validation is missing.

These patterns inform a digital PR and earned-media strategy that runs parallel to the SEO program.

## Passage-level citability

Generative engines do not cite full pages. They cite passages: a paragraph, a sentence, a list item. The unit of optimization is the passage, not the page. A page can rank well, contain the answer, and still not be cited because the answer is buried inside a multi-paragraph block with no clear extraction boundary.

Five practical patterns improve passage citability.

Question-shaped subheadings (already covered in citation readiness).

Lead-in answer sentences. Open the answer with one sentence that contains the full answer, then expand. The extractor preferentially picks the first sentence after the heading.

Specific numerals and dates. Passages with concrete numbers («16-20 weeks», «$120-$200») cite at higher rates than passages with vague qualifiers.

Definitional opening for technical terms. A subheading «What is X» followed by «X is a Y that does Z» extracts cleanly and gets cited as a canonical definition.

Lists for enumerable answers. When the answer is a list of items, format as a list. Engines extract list items as discrete cite-units.

The skill's gap analysis surfaces keywords where citation readiness is the limiting factor. The recommended action for those gap findings is `update` (refresh existing pages for passage extractability) rather than `create`.

## Routing recommendations per scope output

The combination of AIO eligibility and GEO opportunity routes each keyword to one of four optimization paths.

| AIO eligibility | GEO opportunity | Recommended path |
|---|---|---|
| Confirmed or eligible | High | Dual: optimize for AIO and GEO together. Both share the structural recommendations (passage extraction, schema, citation readiness). The keyword commits the largest content investment. |
| Confirmed or eligible | Low | AIO-only: focus on classical retrieval rank plus passage extraction. GEO-specific work (llms.txt visibility, brand mentions) is lower priority. |
| Not eligible | High | GEO-only: the keyword may not show in Google AI Overviews but is asked frequently of generative engines. Focus on crawl accessibility, citation readiness, brand mention signals. |
| Not eligible | Low | Classical: standard SEO applies. The keyword does not need the AIO/GEO playbook. |

This routing is exposed in the JSON output and in the Markdown report's per-keyword recommendation column. The executive summary calls out the share of corpus in each path so the strategic discussion can allocate effort proportionally.

## Operational checklist

For each engagement where the corpus contains a non-trivial share of AIO-eligible or GEO-opportunity keywords, six operational items move the program forward.

1. Confirm AI crawler accessibility. Inspect robots.txt for explicit blocks of GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot. Decide whether the site's policy is intentional and document.
2. Publish or update llms.txt. Mirror the cluster architecture identified by the skill. Include the brand summary, key topics, and links to top hub pages.
3. Audit the top 20 AIO/GEO keywords for citation readiness. Use the five passage-citability patterns as a checklist.
4. Add or improve schema markup on those top 20 pages: Article, Q&A, HowTo, Product as appropriate. Schema is not a guarantee but it removes an extraction friction.
5. Map the entity gaps to a digital PR and earned-media plan. The targets are not random sites; they are the contexts where the client should appear alongside competitors and currently does not.
6. Re-run the keyword intelligence analysis quarterly. AI search algorithms shift faster than classical search; thresholds and routing recommendations age faster too. The freshness gap dimension is precisely the warning system for this.
