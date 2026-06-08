# Semantics

## Contents

- The three semantics that govern modern search
- From LSA to dense retrieval: a working timeline
- Word embeddings, statics and contextual
- Sentence and passage embeddings
- Dense retrieval, late interaction, hybrid
- The Google milestones: Hummingbird, RankBrain, BERT, MUM, Gemini
- Passage ranking and query fan-out
- Bi-encoders versus cross-encoders
- Knowledge graph and entity-based semantics
- Multilingual and cross-lingual semantics
- Operational implications for content
- Why this skill stays rule-based and how that connects to the semantics literature

## The three semantics that govern modern search

When the SEO industry says «semantic search» it is collapsing three different traditions into one term. The traditions overlap in practice but use different tools and have different limits.

The first is **formal semantics**, descended from Frege, Tarski, Montague. Meaning is compositional: the meaning of the sentence is a function of the meaning of the parts plus the rules of composition. Formal semantics underwrites every project that relies on ontologies, description logics, or symbolic knowledge bases. In SEO it appears indirectly through Schema.org, Wikidata, DBpedia, and the entire structured-data layer.

The second is **distributional semantics**, summarized in J.R. Firth's 1957 dictum: «you shall know a word by the company it keeps». The meaning of a term is approximated by its distribution of co-occurrence in corpora. From this tradition come every data-driven model of meaning, from Latent Semantic Analysis (Deerwester et al., 1990) to modern transformer embeddings.

The third is **vector-space semantics in its modern form**, an operational specialization of the second. The meaning of a word, sentence, or document is a vector in a high-dimensional space, and «similar in meaning» becomes «small in distance». The 2013-2018 wave (word2vec, GloVe, FastText) produced static embeddings. The 2018-2024 wave (ELMo, BERT, RoBERTa, sentence-BERT, the E5 and BGE families) produced contextual and instruction-tuned embeddings. This is the tradition that operationalizes most of what Google does at retrieval and ranking time.

The three are not exclusive. Production-grade search stacks combine them: embeddings for retrieval and rough ranking, knowledge graphs for entity disambiguation and ground-truth checks, formal semantics in the structured-data layer that publishers control directly.

## From LSA to dense retrieval: a working timeline

Latent Semantic Analysis was patented in 1988 (US patent issued June 13, 1989) by Deerwester, Dumais, Furnas, Harshman, Landauer, Lochbaum, Streeter, and formally published as «Indexing by Latent Semantic Analysis» in the Journal of the American Society for Information Science 41(6), 1990, pp. 391-407. LSA applies Singular Value Decomposition to a term-document matrix to derive a lower-dimensional «semantic» space where words that co-occur in similar documents map to nearby vectors.

A long-standing terminology trap in SEO blogs is the phrase «LSI keywords». In the original Deerwester sense, LSA produces concept vectors, not lists of synonyms or related terms. Google has never claimed to use LSI for ranking, and Google's John Mueller has publicly denied that LSI keywords exist as a Google concept. The term as used in SEO marketing is a simplification for «semantically related terms», which is what modern transformer-based encoders capture, and which RankBrain, BERT, and MUM operationalize through learned embeddings rather than SVD over a fixed term-document matrix.

Latent Dirichlet Allocation (Blei, Ng, Jordan, JMLR 2003) replaced LSA in many topic-modeling settings. LDA is a generative probabilistic model that represents documents as mixtures of latent topics and topics as distributions over words. For long documents it is still useful. For keyword corpora (queries of one to five tokens) the bag-of-words is too small to estimate stable distributions, and LDA is rarely the right tool.

word2vec (Mikolov, Sutskever, Chen, Corrado, Dean, NeurIPS 2013, «Distributed Representations of Words and Phrases and their Compositionality») introduced shallow neural-network embeddings that captured analogical relationships in vector arithmetic («king minus man plus woman is approximately queen»). GloVe (Pennington, Socher, Manning, 2014) and FastText (Bojanowski, Grave, Joulin, Mikolov, 2017) followed with corpus-statistics-based and subword-aware variants. FastText in particular handles out-of-vocabulary words by composing subword units, which matters for morphologically rich languages.

BERT (Devlin, Chang, Lee, Toutanova, NAACL 2019, arXiv:1810.04805) introduced bidirectional masked language modeling and set new state of the art on numerous NLP tasks. Google announced BERT in search on October 25, 2019 via a post by Pandu Nayak (then Google Fellow and VP of Search), describing it as «one of the biggest leaps forward in the past five years, and one of the biggest leaps forward in the history of Search», initially affecting «1 in 10 searches in the U.S. in English».

Sentence-BERT (Reimers and Gurevych, EMNLP 2019, arXiv:1908.10084) modified BERT with siamese and triplet network architectures to produce sentence embeddings whose geometric structure supports direct cosine-similarity comparison. Per the paper: «This reduces the effort for finding the most similar pair from 65 hours with BERT and RoBERTa to about 5 seconds with SBERT, while maintaining the accuracy from BERT». Sentence-BERT is the foundation of most production embedding stacks today.

Dense Passage Retrieval (Karpukhin, Oguz, Min, Lewis, Wu, Edunov, Chen, Yih, EMNLP 2020, arXiv:2004.04906) demonstrated that pure dense retrieval with two BERT encoders outperformed BM25 by 9 to 19 absolute percentage points in top-20 retrieval accuracy on open-domain QA benchmarks.

ColBERT (Khattab and Zaharia, SIGIR 2020, arXiv:2004.12832) introduced late interaction over BERT, separating query and document encoding and computing fine-grained MaxSim similarity at query time, retaining quality while accelerating retrieval by orders of magnitude. ColBERTv2 (Santhanam, Khattab, Saad-Falcon, Potts, Zaharia, NAACL 2022, arXiv:2112.01488) added residual compression and denoised supervision, reducing storage by a factor of 6 to 10 while improving quality.

Modern embedding model families sit at the production frontier in 2026. The BGE family (Xiao, Liu, Zhang, Muennighoff, «C-Pack: Packed Resources for General Chinese Embeddings», arXiv:2309.07597, plus BGE-M3 in arXiv:2402.03216), the E5 family (Wang, Yang, Huang, Jiao, Yang, Jiang, Majumder, Wei, arXiv:2212.03533, plus Multilingual E5 in arXiv:2402.05672), GTE from Alibaba, Jina embeddings v3, Voyage AI, OpenAI's text-embedding-3 series, and Cohere Embed v3 are evaluated against MTEB (Muennighoff, Tazi, Magne, Reimers, EACL 2023, arXiv:2210.07316), the canonical benchmark across 8 task types and 56 to 58 datasets.

## Word embeddings, statics and contextual

The first generation of word embeddings produced one vector per word regardless of context. word2vec, GloVe, and FastText all share this property. The geometric structure they learned was useful enough to power the first wave of practical applications (analogy completion, simple search expansion, basic clustering) but had a structural limit: a word like «bank» got one vector that conflated its financial sense and its river-side sense.

Contextual embeddings, starting with ELMo (Peters et al., 2018) and continuing with BERT, RoBERTa, and their successors, produce a different vector for the same word in different sentences. «I went to the bank to deposit money» and «I sat on the bank of the river» now produce distinguishable representations of «bank». This is the property that makes modern semantic retrieval and reranking feasible.

For SEO and keyword research, the practical consequence is that two queries with surface-level lexical similarity but different intent (for example, «iphone case» and «iphone case insurance») can be told apart by a contextual model in a way that lexical methods (TF-IDF, BM25, plain token overlap) cannot. This is the kernel of why Google rankings increasingly disagree with what a TF-IDF analysis would predict.

## Sentence and passage embeddings

Sentence-BERT (SBERT) generates one vector per sentence with a structure suitable for cosine similarity comparison. Mean pooling, max pooling, and CLS-token pooling are the three most common pooling strategies. SBERT trained with triplet loss and contrastive learning produces embeddings where semantic similarity correlates with vector distance.

Production-grade modern alternatives to SBERT in 2026:

- **The BGE family** (BGE-base, BGE-large, BGE-M3 multilingual). BGE-M3 is multilingual, multi-functional (dense, sparse, and multi-vector retrieval in one model), and multi-granularity (handles short queries up to 8K-token documents). Open license.
- **The E5 family** (E5-base, E5-large, multilingual-e5-large, e5-mistral-7b-instruct). Trained with weakly-supervised contrastive pre-training on a large corpus of mined positive pairs. Open license.
- **GTE family** from Alibaba. State-of-the-art on MTEB English at multiple scale points. Open license.
- **Jina embeddings v3** with task-specific instruction tuning (separate models for retrieval, classification, clustering).
- **Voyage AI** (closed, paid API). Strong domain-specific variants (voyage-code, voyage-finance, voyage-law).
- **OpenAI text-embedding-3-large** and **text-embedding-3-small**. Closed, paid API.
- **Cohere Embed v3** with task-specific input types (search query, search document, classification, clustering).

Selection criteria: model size and dimensionality, training data domain match, language coverage, MTEB score on the relevant task type, license, inference cost. For multilingual keyword work, BGE-M3 and Multilingual E5 are the strongest open options. For pure English, GTE-large and BGE-large lead on MTEB.

Threshold calibration is empirical. Cosine similarity scores for «same topic» typically land in 0.75 to 0.85 for sentence embeddings, but the absolute distribution depends on the model. Calibrate against a hand-labeled validation set of 100 to 500 keyword pairs before using a threshold operationally.

## Dense retrieval, late interaction, hybrid

Three retrieval paradigms coexist in 2026.

**Sparse lexical retrieval**: BM25 (Robertson and Zaragoza), TF-IDF, query likelihood. Inverted index, exact term match. Fast, interpretable, but blind to synonyms and paraphrases. Still the right baseline for most production stacks.

**Dense retrieval**: bi-encoders that encode query and document independently and compare with dot product or cosine similarity. DPR, Sentence-BERT, BGE, E5, GTE. Captures semantic similarity, blind to exact-term importance for proper nouns and technical terms.

**Late interaction**: ColBERT and ColBERTv2. Encode query and document independently, compare token-level vectors with MaxSim aggregation. Better quality than pure dense at quadratic-but-tractable cost.

**Hybrid retrieval** combines sparse and dense signals via reciprocal rank fusion or weighted sum. The 2023-2026 industry consensus is that hybrid outperforms either pure-sparse or pure-dense on most realistic benchmarks. Cross-encoder reranking on top-K (typically top 50 to top 200) is the third stage in modern stacks.

For keyword clustering specifically, dense embeddings provide the similarity backbone, but clustering quality improves when combined with SERP-overlap signals (which are essentially the labels Google itself produces) and with rule-based intent and brand checks. The hybrid approach is documented in detail in [clustering.md](clustering.md).

## The Google milestones

The moments when Google publicly changed its semantic approach are five, and each changed what SEO had to optimize.

**Hummingbird (September 2013)**. Underlying ranking framework rewrite that made entity-based interpretation operational, affecting more than 90 percent of queries from launch. First moment when keyword-stuffing started losing efficacy and the industry began talking about «semantically related terms».

**RankBrain (October 2015)**. First confirmed machine-learning ranking signal. Confirmed by Google in a Bloomberg interview with Greg Corrado on October 26, 2015. Corrado described RankBrain as the «third-most important signal contributing to the result of a search query». RankBrain handled unfamiliar queries through vector embeddings, recognizing words and phrases with similar meaning.

**BERT in search (October 2019)**. First time bidirectional contextual embeddings entered the core ranking. Per Pandu Nayak's announcement, applied initially to 10 percent of US English queries, then expanded. Practical consequence: queries with significant prepositions and conjunctions started getting semantically correct answers.

**MUM (May 2021)**. Multitask Unified Model, T5-based, multimodal, trained across 75 languages. Per Prabhakar Raghavan: «MUM is 1,000 times more powerful than BERT. MUM not only understands language, but also generates it. It's trained across 75 different languages and many different tasks at once». Cross-language information transfer at retrieval time became a real capability.

**AI Overviews and AI Mode (2024-2026)**. Generative synthesis above the classical SERP, drawing from multiple ranked sources. Gemini 3 deployed globally to AI Overviews in January 2026. The consequence for SEO: optimizing to be cited as a passage diverges from optimizing to receive clicks. The skill `keyword-intelligence` separates these two objectives explicitly in the AIO eligibility scope and in the AEO/defensive composite.

## Passage ranking and query fan-out

Passage ranking was announced by Google in October 2020 and confirmed launched February 11, 2021 for US English. Per Pandu Nayak: «Very specific searches can be the hardest to get right, since sometimes the single sentence that answers your question might be buried deep in a webpage. We've recently made a breakthrough in ranking and are now able to better understand the relevancy of specific passages». Despite the initial label «passage indexing», Danny Sullivan (@searchliaison) clarified that Google still indexes pages, not passages, but ranks them based on passage-level relevance. Initial impact: 7 percent of queries globally.

Query fan-out is Google's term, popularized at I/O 2025 by Elizabeth Reid, for the process by which AI Mode decomposes a single user query into multiple sub-queries retrieved in parallel. Per Aleyda Solis: «Query fan-out is an information retrieval technique that expands a single user query into multiple sub-queries to capture different possible user intents, retrieving more diverse, broader results from different sources». Mike King at iPullRank documented in his 2025 analysis of Google's «Search with stateful chat» patent that AI Mode generates 8 to 12 sub-queries for standard queries and hundreds for Deep Search.

The operational implication is large. A page optimized for a single trigger query is a page optimized for one of 8 to 12 retrieval events. Optimizing for the family of fan-out sub-queries that derive from a trigger query is a different task, and it is increasingly the right task.

## Bi-encoders versus cross-encoders

Bi-encoders (DPR, SBERT, BGE, E5, GTE) encode query and document independently. Pre-computation of document vectors is possible. Retrieval is fast (vector search over millions of documents). Quality is bounded by the assumption that the joint score is a function of two independent representations. Reduced accuracy compared to cross-encoders.

Cross-encoders process query and document jointly through a single transformer pass. Higher accuracy because the model attends across query and document tokens. Quadratic cost in context length and impossible to pre-compute, so practical only for reranking small candidate sets (top 50 to 200).

Modern production stacks combine both: bi-encoder retrieval at scale, cross-encoder reranking on top-K. ColBERT's late interaction is a middle ground that retains some of cross-encoder quality at sub-quadratic cost.

For the skill `keyword-intelligence`, neither approach is implemented because the methodology stays offline and rule-based. Both are described here for the analyst who wants to extend the skill with embedding-based clustering or with cross-encoder reranking at the cluster-validation stage.

## Knowledge graph and entity-based semantics

The knowledge graph is the modern reincarnation of formal semantics inside the distributional pipeline. Google's Knowledge Graph was announced May 16, 2012. Entities are defined by Google as «a thing or concept that is singular, unique, well-defined, and distinguishable». The Knowledge Graph draws from Wikipedia, Wikidata, Freebase (acquired and absorbed), licensed data sources, and Google's own extraction pipelines.

Wikidata in 2026 contains roughly 110 million items with structured statements, properties, and qualifiers. DBpedia extracts equivalent structured data from Wikipedia. Schema.org publishes a shared vocabulary that lets sites declare in machine-readable form what an entity is («this is a Product», «this is a Review», «this is a Person») and how it relates to others.

For SEO, knowledge graph plays three operational roles, all detailed in [entity-and-topical-authority.md](entity-and-topical-authority.md):

- Entity disambiguation. «Apple» is the company, the fruit, or the 2025 film. Entity linkers (spaCy, Stanza, Flair, GLiNER, BLINK from Facebook) map mentions to canonical knowledge-base IDs (Wikidata QID, Wikipedia URL, Google Knowledge Graph MID).
- Authority signal. Pages declaring entities correctly via schema markup get interpretable signals for both classical search (rich results) and generative engines (citation extraction).
- Coverage measurement. The portfolio of entities covered by a site can be compared with the portfolio referenced by competitors or by the demand graph. The «entity gap» dimension in [scoring-formulas.md](scoring-formulas.md) implements this measurement.

## Multilingual and cross-lingual semantics

MUM's multilingual capability across 75 languages enables cross-language information transfer at retrieval time. A page authoritative on a topic in one language can rank for a query in another language when the entity graph connects the two.

For the skill, the practical implication is that multilingual corpora can share entity-level signals while remaining linguistically separate at the surface level. The convention in [multi-language.md](multi-language.md) is to cluster per-language and to perform cross-language entity equivalence only for entity-resolution purposes, not for content consolidation. hreflang remains the canonical mechanism for declaring language and regional targeting; the skill respects but does not generate hreflang.

Translation versus transcreation matters. For international SEO, transcreation (cultural and idiomatic rewriting) outperforms direct translation for content that depends on regional intent and entity associations. The skill flags language-region splits in the corpus summary so the analyst can decide whether the engagement requires per-region work.

## Operational implications for content

The semantic literature converges on a small set of operational implications for content production. They are not new, but they are now empirically supported by multiple peer-reviewed studies and by patent disclosures.

Longer-tail conversational queries are now understood by ranking models. Content can rank for queries it does not lexically contain. Sub-query optimization (optimizing for the family of fan-out queries that derive from a trigger query) replaces single-keyword optimization for the queries that route through AI Mode and AI Overviews.

H2 and H3 subheadings phrased as user questions create natural extraction units for passage ranking and for AI Overview citation. Concise direct answers in 40 to 60 words after the question, then expansion, is the operational chunk-friendly pattern (per Koray Tugberk Gubur and Aleyda Solis).

Original data, original quotations, named expert sources, and verifiable facts are explicitly rewarded by the «Contextual estimation of link information gain» mechanism (US patent US20200349181A1, granted June 2024) beyond what semantic similarity alone would predict.

Schema markup is not a magic bullet but its absence makes extraction harder. Industry analysis (multiple sources, late 2025) suggests pages with proper schema markup are roughly 3 times more likely to earn AI Overview citations, though the mechanism is plausibly causal through better content understanding rather than direct schema-to-citation rewarding.

These implications inform the recommended action classes (`create`, `update`, `restructure`) that gap analysis attaches to each finding in [scoring-formulas.md](scoring-formulas.md).

## Why this skill stays rule-based

Given that the semantic literature points strongly toward dense embeddings, contextual models, and graph-based retrieval, why does this skill stay rule-based and offline?

Three reasons, all methodological rather than technical.

**Reproducibility**. Two analysts running the skill on the same input through the same parameters must produce the same output. Dense embeddings introduce probabilistic and version-dependent variance: the same model at version v1.2 produces different vectors from v1.3, and clustering algorithms over those vectors produce different cluster boundaries. The reproducibility commitment in [methodology-overview.md](methodology-overview.md) is incompatible with this drift unless versions are pinned and embeddings are frozen artifacts of each engagement.

**Vendor neutrality**. Embedding models live behind APIs (OpenAI, Cohere, Voyage) or as large open-source artifacts (BGE, E5) with their own update schedules and licensing terms. The skill commits to standard-library-only Python and to offline operation. A skill depending on a 1.5 GB embedding model is no longer vendor-neutral; it has acquired a new vendor.

**Transparency**. Every score the skill produces can be recomputed by hand for any single keyword. An analyst who disagrees with a score can change a parameter, re-run, see the new result. A black-box scorer based on opaque embeddings does not give the analyst this kind of control.

The methodological cost is real. The skill's clustering, by token overlap with light per-language stemming, is less semantically aware than what BGE-M3 plus HDBSCAN would produce. Synonym resolution is weaker. Cross-paraphrase detection is weaker. The intent classification rules cannot capture what a fine-tuned cross-encoder would.

The methodological gain is reproducibility, transparency, and honesty about what the skill knows and what it does not. These are the conditions under which an analyst can defend recommendations in front of a client.

The roadmap toward an embedding-augmented v2 is documented in [clustering.md](clustering.md), in the section on hybrid clustering. The principle for v2 is that any embedding-derived signal must be added with explicit version pinning and explicit confidence weighting, never as a replacement for the deterministic core but as an enrichment whose contribution to the composite is itself auditable.

## A note on terminology used in this file

«Embedding» refers to a dense vector representation of a token, sentence, or document, produced by a neural model. «Dense retrieval» is retrieval over these embeddings using cosine similarity or dot product. «Semantic similarity» is the working name for «proximity in an embedding space whose geometry reflects meaning».

«Knowledge graph» refers throughout to the formal-semantic infrastructure (entities, attributes, relations, identifiers) regardless of which specific graph (Wikidata, DBpedia, Google's Knowledge Graph) is meant in a given paragraph.

«Entity» follows Google's definition: a thing or concept that is singular, unique, well-defined, and distinguishable. The skill's entity work is documented in [entity-and-topical-authority.md](entity-and-topical-authority.md).

«Passage» follows the Pandu Nayak usage: a self-contained section within a longer document, typically a paragraph or a list, that can independently answer a query.

«Citation» in the GEO context refers to inclusion as a source in a generated answer, which is operationally distinct from ranking in the classical SERP.
