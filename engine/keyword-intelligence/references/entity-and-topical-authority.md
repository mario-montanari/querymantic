# Entity SEO and topical authority

## Contents

- The «strings to things» moment
- Named-entity recognition, entity linking, salience
- Subject-predicate-object triples and brand context
- Practitioner approaches: ten people who built the field
- Wikipedia, Wikidata, and the brand entity pathway
- Entity gap analysis and co-occurrence
- Topical authority: definition, history, mechanisms
- YMYL and E-E-A-T integration
- Failure modes in topical-authority work
- Schema.org and structured data
- Brand SERP optimization
- Multilingual and cross-lingual entity SEO
- AEO and GEO: foundational and follow-up academic work
- Industry empirical findings, with caveats
- Operational implications across the skill
- How this skill uses entity and topical signals

## The «strings to things» moment

Google's Knowledge Graph was announced on May 16, 2012 with the slogan «from strings to things». Entities are defined by Google as «a thing or concept that is singular, unique, well-defined, and distinguishable». The Knowledge Graph draws from Wikipedia, Wikidata, Freebase (acquired and absorbed), licensed data sources, and Google's own extraction pipelines.

Hummingbird (September 2013) was the underlying ranking framework rewrite that made entity-based interpretation operational. It affected more than 90 percent of queries from launch and reframed search as the matching of an entity-and-attribute structure rather than a string-and-string overlap.

This is the moment when SEO began the transition from keyword-centric optimization to entity-centric optimization. The transition is still in progress in 2026: most production SEO programs blend both, weighted differently by vertical, but the pure keyword-density optimization that dominated 2008-2012 is no longer competitive.

## Named-entity recognition, entity linking, salience

Named Entity Recognition (NER) identifies spans of text as instances of entity types (Person, Place, Organization, Event, Product, Work, MedicalCondition, and so on). Open-source NER tools used in SEO workflows include spaCy, Stanza (Stanford), Flair, GLiNER, BLINK from Facebook, and Google Cloud Natural Language API.

Entity linking (or entity disambiguation) maps a recognized mention to a canonical knowledge-base identifier: a Wikidata QID, a Wikipedia URL, a Google Knowledge Graph MID. This is the step that distinguishes «Apple the company» from «apple the fruit». Modern entity linkers operate on contextual embeddings of the surrounding text and compare against entity descriptions in the target knowledge base.

Entity salience measures how central an entity is to a piece of content. Google's Cloud Natural Language API exposes both entity recognition and salience scores. SEOs frequently use this API to audit content: an article that lists «Tom Hanks» but assigns him a low salience score has not centered him as a topic, even if his name appears.

Operational consequence: a page about Tom Hanks should mention Tom Hanks early, with high salience, and should co-occur with the entities that the knowledge graph associates with Tom Hanks (Forrest Gump, Saving Private Ryan, Steven Spielberg, Apollo 13). Failing to mention these adjacent entities signals weak topical coverage to Google's interpretation.

## Subject-predicate-object triples and brand context

Subject-predicate-object (SPO) triples are the atomic unit of semantic web data (RDF). For SEO, the operational claim by Olaf Kopp is that «Google uses NLP to identify entities and their context. This works via grammatical sentence structures, triples and tuples made up of nouns and verbs».

Olaf Kopp's «brand context optimization» methodology (kopp-online-marketing.com, 2026) emphasizes Entity-Attribute-Value triples and writing in syntactically simple sentences that minimize coreference distance between entity and attribute. The practical advice: write «Aufgesang offers GEO consulting» rather than «We offer this consulting», so that pronoun resolution does not have to bridge across sentences for the LLM to attach the attribute to the brand entity.

This advice generalizes. Every page that wants to be cited in generative-engine answers should optimize the closeness of entity, predicate, and attribute, both within a sentence (avoid pronouns when the entity is the topic) and across sentences (early sentence in each section names the entity explicitly).

## Practitioner approaches: ten people who built the field

The semantic-and-entity-SEO field has roughly ten named practitioners whose work is referenced across the industry. The list below is a methodological reference, not an endorsement.

**Bill Slawski** (Go Fish Digital, «SEO by the Sea», deceased 2022) was the foundational interpreter of Google patents for the SEO industry. His patent analyses over two decades trained the field to think in terms of entities, knowledge graphs, ranked entities, question answering, and information gain. He identified that Google's first semantic-search invention was patented in 1999 by Sergey Brin. His archived blog remains the field's canonical patent reference.

**Andrea Volpini** (CEO, WordLift; co-founder Insideout10) operationalized knowledge graphs as SEO infrastructure starting around 2013. WordLift constructs a per-site knowledge graph in RDF and JSON-LD, automatically annotates entities, builds sameAs cross-references, and outputs schema markup. Volpini's 2026 work emphasizes «Recursive Language Models on Knowledge Graphs» as the foundation for AI-search visibility (WordLift blog, January 21, 2026).

**Dixon Jones** (CEO, InLinks; previously CMO, Majestic) authored «Entity SEO: Moving from Strings to Things» (ISBN 978-1916192003). InLinks's methodology centers on Wikipedia and Wikidata entity definitions and uses internal-linking automation to consolidate topical authority on a single canonical page per concept. Jones launched Waikay in March 2025 specifically for LLM brand visibility.

**Cindy Krum** (CEO, MobileMoxie) coined «Fraggles» (Fragments + Handles) in 2017 to describe the indexing of sub-page units, and proposed in 2018-2019 that mobile-first indexing was actually entity-first indexing because entities are language-agnostic and let Google build a single global index. Her thesis predicted Passage Ranking and the modern fan-out architecture.

**Jason Barnard** (CEO, Kalicube; «The Brand SERP Guy») coined «Brand SERP» in 2013 and «Answer Engine Optimization» in 2018. The Kalicube Process is a three-pillar methodology: Understandability, Credibility, Deliverability. Kalicube Pro database holds over 9 billion brand data points across 70 million brands. Book: «The Fundamentals of Brand SERPs for Business» (2022, ISBN 978-1956464108).

**Jes Scholz** (independent SEO consultant, Sydney; SEOktoberfest 2022 SEO World Champion) approaches entity SEO through information architecture. Her Search Engine Land article «How to establish your brand entity for SEO: A 5-step guide» (June 1, 2023) is canonical. Her position: «A well-known, top rated and trusted brand entity is the cornerstone of organic visibility».

**Olaf Kopp** (Co-founder, CBDO, Head of SEO and AI Search, Aufgesang GmbH) is the leading German-language semantic-SEO authority and founder of the SEO Research Suite, «the world's first database for patents and research papers». His 2026 work on «Brand Context Optimization» for GEO is the most rigorous practitioner framework on optimizing entity-attribute connections for LLM understanding.

**Koray Tugberk Gubur** (founder, Holistic SEO and Digital) coined «Topical Authority» in its modern operational sense on May 18, 2022. His framework combines Topical Coverage with Historical Data, uses 41 content rules including «one macro context per page», «H2 headings as user questions», «40-word extractive answers», and full Entity-Attribute-Value coverage with hub-and-spoke internal linking. His self-reported case study claims «0 to 128,000 organic traffic in 123 days, 12,000 organic clicks per day in 162 days». Treat self-reported case study claims with appropriate skepticism. The methodology principles are well-supported by patent and NLU literature even if specific numbers are unverified.

**Aleyda Solis** (founder, Orainti; SEOFOMO; learningseo.io) integrates international and semantic SEO. Her 2025-2026 framework «The AI Search Optimization Roadmap» emphasizes coverage topic clusters, chunk-level retrieval optimization, query-fan-out targeting, and authority and citation building.

**Mike King** (founder, iPullRank) provides the deepest practitioner-level analysis of Google's AI Mode and AI Overviews patents. His 2024-2025 analyses of «Contextual estimation of link information gain» (US patent US20200349181A1, granted June 2024) and the «Search with stateful chat» patent (powering AI Mode) are the operational reference for understanding fan-out, AIV (Attributed Influence Value), and citation mechanics.

Additional names cited in the practitioner literature without dedicated paragraphs above: Lily Ray (Amsive), Marie Haynes (Marie Haynes Consulting), Glenn Gabe (G-Squared Interactive), Cyrus Shepard (Zyppy SEO), Barry Schwartz (Search Engine Land, Search Engine Roundtable), Danny Sullivan (Google SearchLiaison).

## Wikipedia, Wikidata, and the brand entity pathway

The Wikipedia and Wikidata pathway. Notability per Wikipedia's General Notability Guideline («significant coverage in reliable sources independent of the subject»). For most brands, Wikipedia is unreachable directly because the notability bar is high; Wikidata is the more practical entry. Wikidata is structured (statements, properties, qualifiers) and accepts entries below Wikipedia's notability threshold.

The sameAs construction in schema.org Organization markup points Google's disambiguator to authoritative external IDs. A Wikidata QID, a Wikipedia URL, a Crunchbase profile, a LinkedIn company page, an official social profile: each becomes a node in a graph that disambiguates the brand for Google's interpretation.

Operational steps for a brand that does not yet have a strong entity in the Knowledge Graph:

1. Create or strengthen a Wikidata entry with structured statements (founded, headquarters, industry, official website, sameAs links).
2. Add Organization schema with @id (a stable URI) and sameAs cross-references to Wikipedia, Wikidata, Crunchbase, LinkedIn, and any other authoritative external sources.
3. Build out the on-site brand entity page with semantic markup, founder and key-personnel information, awards, recognized industry associations.
4. Pursue earned media (third-party authoritative coverage) to satisfy the notability bar over time.
5. Monitor the Knowledge Panel for the brand's name as the lagging indicator.

## Entity gap analysis and co-occurrence

The practical workflow for entity-gap analysis. Extract entities from top-ranking competitor content for a target topic using Google NLP API or open-source NER (spaCy, Stanza, Flair). Compute the union set across competitors. Identify entities you do not cover. Prioritize by frequency and salience.

Co-occurrence at the document and sentence level signals to Google which entities are conceptually related. A Tom Hanks page that fails to mention Forrest Gump, Saving Private Ryan, Steven Spielberg, and Apollo 13 is signaling weak topical coverage even if Tom Hanks himself appears with high salience. The skill `keyword-intelligence` exposes this dimension as the «entity gap» in [scoring-formulas.md](scoring-formulas.md).

## Topical authority: definition, history, mechanisms

Topical authority is the operational claim that demonstrating depth and breadth across an entire topic graph improves ranking probability across all queries within that graph, beyond what page-level link signals would predict.

The hub-and-spoke (pillar-cluster) articulation comes from HubSpot's content-strategy team around 2017. Koray Tugberk Gubur formalized topical authority with a semantic-network framing in 2022.

The mechanisms that plausibly underlie topical-authority signals: site-wide entity coverage, internal-linking density and quality, anchor-text relevance, content depth per cluster page, freshness, author E-E-A-T signals, historical user-satisfaction data. None of these is independently confirmed by Google as a «topical authority score». The mechanism is multi-signal and emergent.

Operational consequences for content programs:

- Cover the topic graph, not just the high-volume keywords. The skill's gap analysis identifies the missing nodes.
- Connect cluster pages with explicit internal links to and from a hub. Sibling pages cross-link selectively, not blanket.
- Prefer depth over breadth in the early stages of a new topic. A 30-page topic graph with deep coverage of each node beats a 300-page graph with shallow coverage.
- Author signals matter for YMYL topics. The same content under a different byline can rank differently.

## YMYL and E-E-A-T integration

Google Quality Rater Guidelines (QRG) define YMYL (Your Money or Your Life) as content where low quality could harm «future happiness, health, financial stability, or safety». E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) was expanded to include Experience in December 2022.

Topical authority at the domain level interacts with E-E-A-T at the author and entity level. Olaf Kopp's framing is that entities (publisher, author) are evaluated for E-E-A-T relative to the topical context they are attempting to be authoritative within. Spreading too thin dilutes the entity-topic fit. A medical publisher that branches into automotive content reduces its entity-topic alignment for both topics.

For brand entities and author entities, the practical mapping:

- Experience signals: first-person accounts, original photos, demonstrated use, dated case studies.
- Expertise signals: credentials, professional affiliations, citations in authoritative sources.
- Authoritativeness signals: third-party recognition, high-quality earned media, presence in industry associations and curated lists.
- Trustworthiness signals: transparent ownership, contact details, editorial policies, fact-checking processes, error correction history.

Each signal has a corresponding optimization tactic and a corresponding measurement, but none of them is a single ranking factor. They contribute jointly to the emergent topical-authority assessment.

## Failure modes in topical-authority work

Shallow pillar content with deep cluster pages but no consolidating hub. The cluster pages compete with each other and with the pillar, splitting authority instead of accumulating it.

Hub pages that are essentially link directories with no original synthesis. Google's information-gain mechanism rewards original framing; a directory hub adds no information beyond its links and gets ranked below the cluster pages it tries to organize.

Cluster pages that fail to link back to the hub. The hub-and-spoke topology only works when both directions are explicit. One-way linking from hub to cluster is the most common error.

Internal linking that crosses clusters indiscriminately. This dilutes the topical signal because Google interprets cross-cluster links as evidence that the clusters are not actually distinct.

Publishing volume without coverage strategy. 200 articles distributed across 50 topics produces less topical authority than 50 articles concentrated on 5 topics, even if the total word count is the same.

Treating «content gap analysis» as keyword gap rather than entity-and-attribute gap. Keyword gap names the strings that competitors target. Entity-and-attribute gap names the topics, properties, and relationships that competitors cover. The latter is the right level for architecture work.

## Schema.org and structured data

Schema.org was founded by Google, Microsoft, Yahoo, and Yandex in 2011. As of 2024, «over 45 million web domains markup their web pages with over 450 billion Schema.org objects» per schema.org. Encodings: JSON-LD, Microdata, RDFa. Google explicitly recommends JSON-LD: «Google recommends using JSON-LD for structured data... as it's the easiest solution... to implement and maintain at scale» (Google Search Central).

The high-value types for most engagements: Article (NewsArticle, BlogPosting), Product, Recipe, FAQPage, HowTo, Event, Organization (with sameAs cross-references), Person, LocalBusiness, BreadcrumbList, ImageObject, VideoObject, Review, AggregateRating. Less common but high-value when applicable: Course, JobPosting, Dataset, ClaimReview (fact-checking), MedicalEntity, SoftwareApplication, Book.

Schema as entity declaration. The construction `@id` (a stable URI) plus `sameAs` (linking to Wikipedia, Wikidata, Crunchbase, LinkedIn, official profiles) constitutes an explicit entity declaration. Google's documented behavior is to use these to disambiguate the entity for the Knowledge Graph. WordLift's methodology centers on this construction.

Schema and rich results. Eligibility for rich results requires both correct schema and adherence to content-quality and policy guidelines. The Rich Results Test is the Google-specific validator; schema.org's Schema Markup Validator handles general validation. Per Google: «Google does not guarantee that your structured data will show up in search results, even if your page is marked up correctly».

Schema for AI and generative engines. Industry analysis (multiple sources, late 2025) suggests pages with proper schema markup are roughly 3 times more likely to earn AI Overview citations, though the mechanism is plausibly causal through better content understanding rather than direct schema-to-citation rewarding.

## Brand SERP optimization

The Brand SERP is the search-results page for a brand-name query. Per Jason Barnard, it functions as «your new business card, an honest critique of your content strategy and a reflection of your brand's digital ecosystem».

Controllable elements on a Brand SERP: the Knowledge Panel (via Wikidata, Wikipedia, schema markup, official sources), site links, social-profile links, video carousels, «People also ask» boxes, news mentions, and the order in which they appear.

Brand entity in the LLM era. Per Olaf Kopp's «brand context optimization» (kopp-online-marketing.com, February 2026), brands must be syntactically and semantically tightly connected to their attributes («Aufgesang offers GEO consulting», not «We offer this consulting») so that LLM coreference resolution succeeds. The same principle applies to product-attribute associations and to executive-and-company associations.

The skill `keyword-intelligence` does not generate Brand SERP audits, but its branded-versus-non-branded scope (scope 9) and its AEO/defensive composite identify the queries where Brand SERP optimization should be the next step.

## Multilingual and cross-lingual entity SEO

MUM's multilingual capability across 75 languages enables cross-language information transfer at retrieval time. hreflang remains the canonical mechanism for declaring language and regional targeting.

Cross-language entity equivalence is increasingly handled by Google through Wikidata and the Knowledge Graph. A brand with a strong Wikidata entity inherits its cross-language identity automatically. A brand without a Wikidata entity must build per-language entity signals separately, which is more expensive and slower.

Translation versus transcreation. For international SEO, transcreation (cultural and idiomatic rewriting) outperforms direct translation for content that depends on regional intent and entity associations. Cross-region SEO that relies on machine translation alone produces content that ranks but rarely converts.

## AEO and GEO: foundational and follow-up academic work

The foundational paper. Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, Deshpande, «GEO: Generative Engine Optimization», KDD 2024 (arXiv:2311.09735, DOI:10.1145/3637528.3671900). Authors from Princeton, Georgia Tech, Allen Institute, IIT Delhi. GEO-bench: 10,000 queries (8K/1K/1K splits), 80 percent informational, across 25 domains. Nine optimization methods tested.

Headline finding: «The best methods improve upon baseline by 41 percent and 28 percent on Position-Adjusted Word Count and Subjective Impression respectively». Top performers: Quotation Addition (PAWC 27.2 versus baseline 19.3), Statistics Addition (25.2), Cite Sources (24.6), Fluency Optimization (24.7). Combination of Fluency Optimization plus Statistics Addition outperformed any single strategy by 5.5 percent. Critically, per the paper: keyword stuffing performs 10 percent worse than baseline on Perplexity. Statistics Addition lifted Subjective Impression by up to 37 percent on Perplexity in real-world deployment.

Follow-up work in 2025-2026. Tian, Chen, Tang, Liu, Jia, «AgentGEO: Diagnosing and Repairing Citation Failures in Generative Engine Optimization» (arXiv:2603.09296, March 2026). Headline: «AgentGEO achieves over 40 percent relative improvement in citation rates while modifying only 5 percent of content, compared to 25 percent for baselines».

Chen, Wang, Chen, Koudas (University of Toronto), «Generative Engine Optimization: How to Dominate AI Search» (arXiv:2509.08919, September 2025). Key empirical claim: «AI Search exhibit a systematic and overwhelming bias towards Earned media (third-party, authoritative sources) over Brand-owned and Social content».

Kumar and Palkhouski, «AI Answer Engine Citation Behavior: An Empirical Analysis of the GEO-16 Framework» (arXiv:2509.10762, September 2025). 70 prompts, 1,702 citations, 1,100 unique URLs, 16 B2B SaaS verticals. Top correlations with AI Overview citation likelihood (Pearson, all p < 0.001): Metadata and Freshness r=0.68, Semantic HTML r=0.65, Structured Data r=0.63, Evidence and Citations r=0.61, Authority and Trust r=0.59, Internal Linking r=0.57. Logistic regression Nagelkerke R² = 0.743; odds ratio for GEO score = 4.2 [3.1, 5.7]. Threshold: pages scoring G ≥ 0.70 with ≥ 12 pillar hits achieve a 78 percent cross-engine citation rate.

Miroyan et al. (UC Berkeley), «Search Arena: Analyzing Search-Augmented LLMs» (arXiv:2506.05334, June 2025; v2 March 2026). 24,069 conversations, 12,652 paired human preference votes. Bradley-Terry coefficients: response length β=0.334; number of citations β=0.209; supporting citations β=0.29; irrelevant citations β=0.27; citing Wikipedia β=−0.071. Notable finding: «users do not distinguish between supporting and irrelevant citations and generally prefer more citations, even if the citations do not directly support the claims».

Citation Selection to Citation Absorption study (arXiv:2604.25707, April 2026). 602 controlled prompts. Per-prompt citation counts: Perplexity 16.35, Google 12.06, ChatGPT 6.88. «High-influence pages are longer, more modular, more semantically aligned with the generated answer, and more likely to contain extractable evidence genres such as definitions, numerical facts, comparisons, and procedural steps».

## Industry empirical findings, with caveats

Treat these as industry-research-grade rather than peer-review-grade. They are useful for sizing and direction.

Ahrefs's updated study (January 2026, 863K keyword SERPs, 4M AI Overview URLs): top-10 organic overlap with AI Overview citations dropped from approximately 76 percent (July 2025) to 38 percent (early 2026). Attributed both to improved Ahrefs parsing methodology and to expanded query-fan-out behavior under Gemini 3.

BrightEdge (February 2026) reported 17 percent overlap on a different methodology. SeoClarity contemporaneous finding: 97 percent of AI Overviews still cite at least one source from the top 20 organic results, even if not the top 10. The reconciliation: fan-out broadens the citation pool well beyond the trigger-query top 10 but still draws from organically discoverable, authoritatively ranked content.

Seer Interactive (September 2025): organic CTR for AI-Overview-triggering queries dropped from 1.76 percent to 0.61 percent (61 percent decline). Pages cited inside AI Overviews earned 35 percent more organic clicks and 91 percent more paid clicks than uncited competitors.

Conductor Q1 2026: AI Overview prevalence approximately 25 percent across 21.9M queries. BrightEdge March 2026: 48 percent across nine commercial verticals. Healthcare, Education, B2B Tech, Insurance show highest AI Overview presence.

Reported AI Overview citation share: Reddit approximately 21 percent (Profound aggregated 2025-2026). YouTube has overtaken Reddit as most-cited source across all LLM answers per Adweek, January 2026.

## Operational implications across the skill

Optimize for chunk-level retrieval. Each H2 section should be independently understandable as a passage. Keep passages tightly focused (one idea per section). Use clearly structured «Summary» and «Key takeaways» when the section warrants them.

Add original statistics, original quotations, named expert sources, and verifiable facts. Cite authoritative sources within content. The information-gain patent (US20200349181A1) explicitly rewards this.

Build authentic third-party mentions («earned media»), since AI engines weigh these heavily. Do not substitute brand-owned content for third-party validation; the Toronto study shows AI search systematically prefers earned media.

Treat YouTube as part of the AI search surface, not just a video platform. Adweek's January 2026 finding that YouTube has overtaken Reddit as most-cited source matters for content programs that previously treated video as ancillary.

Build the entity layer in parallel with the content layer. Wikidata entry, Organization schema with sameAs, brand entity page on the site, third-party authoritative coverage. The skill's gap analysis surfaces the missing entities; the program team converts them into editorial commissions.

## How this skill uses entity and topical signals

The skill `keyword-intelligence` does not implement entity linking, salience scoring, or knowledge-graph traversal. It implements a pragmatic surface-level approximation across several scopes.

The branded-versus-non-branded scope (scope 9) uses regex matching against an analyst-supplied brand list with fuzzy variations. This is a coarse approximation of entity recognition limited to the client's own brand. Detail in [analysis-scopes.md](analysis-scopes.md).

The entity gap dimension in [scoring-formulas.md](scoring-formulas.md) operates on capitalized multi-word phrases, recognized geographic markers, and the brand-list parameter. It surfaces entities the corpus references that the client does not own. This is a coarse approximation of entity linking limited to NER-by-pattern.

The intent vector (scope 1) and its temporal axis identify event-driven queries through year markers and named-event markers. This is a partial substitute for proper temporal-entity recognition.

The cluster strength score in the main and strategic composites is a partial substitute for topical-authority measurement: it rewards keywords inside coherent clusters, which is the operational signature of topical-authority work.

The skill is honest about these approximations. They are deliberately surface-level so the skill stays offline, deterministic, and reproducible. An analyst who needs proper entity linking and salience scoring runs the skill for the SERP-and-keyword-graph dimension and combines its output with a Google Cloud Natural Language API audit on the actual content. The two outputs are complementary, not redundant.

The roadmap toward an entity-aware v2 follows the same shape as the embedding-aware v2 in [clustering.md](clustering.md): pin the entity-extraction tool and version, store the extracted entities as a workspace artifact, weight the entity signal in the composite scores with explicit confidence, never use it to replace the deterministic core.

For the analyst who wants to take this farther today, the practitioner references at the start of this file are the starting points: WordLift for knowledge-graph automation, InLinks for entity-driven internal linking, Kalicube for brand-entity diagnostics, the SEO Research Suite for patent and academic-paper depth.
