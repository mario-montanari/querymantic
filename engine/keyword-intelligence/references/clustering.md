# Clustering

## Contents

- Conceptual foundations
- Pre-modern history of keyword grouping
- SERP-based clustering
- Embedding-based clustering
- Algorithmic families
- Graph-based clustering and community detection
- Topic modeling for short text
- Hybrid clustering: the production-grade default
- LLM-assisted clustering
- Cluster quality evaluation
- Cluster membership roles and hierarchy
- Cluster-to-content mapping
- Clustering at scale
- Scenarios that need different recipes
- Common failure modes
- Why this skill ships a deterministic three-pass clusterer
- Roadmap toward a hybrid v2

## Conceptual foundations

Clustering in SEO is the partitioning of a keyword list into subsets where each subset corresponds to a distinct user intent or content asset. It differs from general data-science clustering in one key way: the validation criterion is operational, not statistical. A cluster is correct when one URL can rank for it, not when within-cluster cohesion exceeds between-cluster separation.

Three definitions anchor the rest of this file. A topic is a broad subject domain. A keyword is a specific query string. A cluster is a set of keywords that share intent and SERP behavior closely enough to be served by a single content asset.

The shift from one-keyword-one-page to one-cluster-one-asset is the central modern operating principle. The economic argument is simple: keyword universes scale to millions, content production does not. Clustering reduces production cost per organically reachable query while increasing per-page authority, because every page accumulates internal-link signal and topical-coverage signal proportional to the size of the cluster it serves.

Two universal quality dimensions: cohesion (high within-cluster similarity) and separation (low between-cluster similarity). The bias-variance trade-off in clustering has a direct SEO interpretation. Lower thresholds produce larger, more inclusive clusters: high recall but low precision, the page risks straddling distinct intents. Higher thresholds produce smaller, stricter clusters: high precision but low recall, the analyst ends up with too many pages and orphan content.

## Pre-modern history of keyword grouping

The spreadsheet era. SEOs grouped keywords by shared modifiers, intent labels, and judgment. A column for «head term», a column for «modifier», a column for «intent class». The work was manual and broke at scale (above 10,000 keywords) and missed semantic equivalences (synonyms, paraphrases, regional variants).

Rule-based and pattern-matching clustering. Regex on shared n-grams. «contains 'best'», «contains 'review'», «matches /how (to|do)/». Useful as a first pass for intent labeling, insufficient as a clustering method.

The first systematic approach was SERP overlap, which became the industry default circa 2018-2020 and remains the strongest single signal as of 2026.

## SERP-based clustering

The principle is simple and operationally compelling. If two queries return substantially overlapping top-N organic results, Google has effectively decided they are the same query for ranking purposes, and one page can target both.

Methodology: pull the top-N (typically top-10) organic URLs for each keyword. Compute pairwise overlap. Treat keywords as nodes, draw edges where overlap exceeds a threshold, partition into connected components. Each component is a cluster.

The standard 3-of-10 threshold (3 shared URLs out of top 10) became conventional through industry tooling, though contemporary practice uses 4 to 6. Per Keyword Insights documentation: «due to the increasing number of SERP features (AI Overviews, Quick Answers, Featured Snippets), Google no longer consistently shows 10 traditional links in the top 10 results. We adjusted the threshold to between 1-7». Per HubSpot's 2026 reference: «if two keywords share 3 or more of the same top-10 URLs, they belong in the same cluster. If the overlap is 0 or 1, they likely warrant separate pages». Per Oncrawl: «medium (4-6) requires substantive similarity; higher (7+) produces strict small clusters».

Position weighting. Matches at position 1 carry more signal than matches at position 9. Reciprocal rank weighting (1/position) is the standard correction. Position weighting reduces noise from high-volatility low positions.

Jaccard similarity is the formal version of overlap counting: |A ∩ B| / |A ∪ B|. For top-10 SERPs A and B with 4 URLs in common, Jaccard equals 4/16 = 0.25. Many SERP-clustering implementations use absolute counts because thresholds are easier to communicate, even though Jaccard normalizes for cases where the top-N is shorter than 10 (a common case under AI Overviews).

Connected component analysis is the partitioning method. Pairwise comparison cost is O(n²); for large n, optimization via inverted indexing on URLs (group keywords sharing each URL, compute overlap only among those candidate pairs) reduces practical cost substantially.

SERP-based clustering has known failure modes. Volatile SERPs where ranking churn means same-query same-day overlap is unstable. Thin SERPs where statistical signal is weak. Brand-dominated SERPs where queries containing brand names produce trivially overlapping branded results. Freshness-sensitive queries (news, events) where the top URLs change daily. AI Overview-heavy SERPs where reduced organic real estate weakens the signal.

For AI Overview SERPs, the industry recommendation (Aleyda Solis, Mike King) is to include AI Overview cited sources in the overlap computation, expanding beyond pure top-10 organic. Keyword Cupid clusters explicitly on URL-level SERP overlap with retrained ML for finer granularity.

The cost of capturing fresh SERP data at scale is real. Google does not provide a public SERP API. Practitioners use SerpApi, DataForSEO, ScraperAPI, ValueSerp, or Bright Data. Per-query cost typically lands at 0.50 to 5 USD per 1000 SERPs. For 100,000 keyword clustering, raw SERP capture costs 50 to 500 USD per pass.

## Embedding-based clustering

Vector representations span a hierarchy from sparse to dense. One-hot vectors (vocabulary-sized, sparse). Bag-of-words. TF-IDF (sparse weighted). word2vec, GloVe, FastText (dense static embeddings, 100 to 300 dimensions). Contextual embeddings from BERT and successors. Sentence and passage embeddings from SBERT, the BGE family, the E5 family, GTE, Jina, Voyage, OpenAI, Cohere.

The selection criteria for production keyword work: model size and dimensionality, training data domain match (general versus domain-specific), language coverage (English-only versus multilingual), MTEB benchmark performance, license terms, inference cost. For multilingual keyword work, BGE-M3 and Multilingual E5 are the strongest open options. For pure English, GTE-large and BGE-large lead on MTEB. Detail on embedding model choice is in [semantics.md](semantics.md).

Similarity metrics: cosine similarity (dot product of L2-normalized vectors) is standard for sentence embeddings. Euclidean distance is equivalent to cosine on normalized vectors up to monotonic transformation. Dot product is used directly when vectors are not normalized (DPR, some OpenAI embeddings).

For 100K+ keyword clustering, exact pairwise comparison becomes prohibitive. Approximate nearest-neighbor libraries (ANN) handle this. FAISS (Facebook AI, supports IVF, IVF-PQ, HNSW indexes), HNSWlib (Malkov and Yashunin 2016, arXiv:1603.09320), ScaNN (Google, anisotropic vector quantization, Guo et al. ICML 2020), Annoy (Spotify), Pinecone, Weaviate, Qdrant, Milvus.

Threshold calibration is empirical and per-model. Cosine similarity thresholds for «same topic» typically land at 0.75 to 0.85 for sentence embeddings, but the absolute distribution depends on the model. Calibrate against a hand-labeled validation set of 100 to 500 keyword pairs before using a threshold operationally.

Why pure embedding clustering fails when used as the sole signal. Over-clustering: distinct intents with surface-level lexical similarity (for example, «iphone case» and «iphone case insurance») cluster together because the embedding model is not intent-aware. Under-clustering: same intent with very different lexical surface (for example, «best laptop for video editing» and «video editing computer recommendations») may not exceed the threshold because the surface-form difference dominates the semantic signal at this scale.

SERP overlap captures Google's actual ranking judgment. Embeddings capture lexical-semantic similarity. The two are not equivalent. This is why hybrid approaches dominate in production tooling.

## Algorithmic families

Five families of clustering algorithms cover the space.

**Partitional**. K-means (Lloyd's algorithm, 1957) partitions the space into k clusters by minimizing within-cluster variance. K-means++ (Arthur and Vassilvitskii, SODA 2007) improves initialization. Methods to estimate k include the elbow method, silhouette score, and the gap statistic (Tibshirani, Walther, Hastie, JRSS-B 2001). K-means is rarely ideal for keyword clustering: cluster count is not known a priori, varies by topic, and the algorithm assumes spherical equal-size clusters.

**Hierarchical agglomerative clustering** (HAC) merges clusters bottom-up. Linkage methods: single (minimum distance, produces chains), complete (maximum distance, produces compact clusters), average (mean distance, balanced), Ward (minimizes variance increase, often best for spherical clusters in Euclidean space). Advantage for SEO: the dendrogram allows post-hoc choice of granularity by cutting at different heights. Cost is O(n²) or O(n³), impractical above tens of thousands of points.

**Density-based**. DBSCAN (Ester, Kriegel, Sander, Xu, KDD 1996) discovers arbitrarily-shaped clusters and explicitly identifies noise. Parameters: eps (neighborhood radius) and min_samples. Limitation: variable density datasets. OPTICS (Ankerst, Breunig, Kriegel, Sander, SIGMOD 1999) addresses this with a reachability ordering.

**HDBSCAN** (Campello, Moulavi, Sander, PAKDD 2013, plus Campello, Moulavi, Zimek, Sander, ACM TKDD 10(1) 2015, plus McInnes, Healy, Astels, JOSS 2017) extends DBSCAN with hierarchical density estimates. Parameters: min_cluster_size, min_samples, cluster_selection_method (`eom` for excess of mass, `leaf` for finer granularity). Why this is the modern default for embedding-based clustering: handles variable density automatically, no k specification needed, identifies noise, stable across reasonable parameter values. The McInnes implementation is the standard.

**Distribution-based**. Gaussian Mixture Models with Expectation Maximization (probabilistic, soft assignment). Useful when the analyst wants probabilistic membership rather than hard assignment.

**Other** algorithms in production use: Affinity Propagation (Frey and Dueck, Science 2007, no k, message-passing), Mean Shift (Comaniciu and Meer, PAMI 2002, mode-seeking), BIRCH (Zhang, Ramakrishnan, Livny, SIGMOD 1996, for very large datasets via CF-tree), Spectral Clustering (Ng, Jordan, Weiss, NIPS 2002, useful for non-convex clusters but expensive at scale).

Algorithm-by-scenario quick reference:

| Scenario | Recommended algorithm |
|---|---|
| Small (<1,000), known k | K-means |
| Small to medium, unknown k, want hierarchy | Agglomerative (Ward linkage) |
| Medium to large, unknown k, dense clusters with noise | HDBSCAN |
| Very large (>1M), need streaming | BIRCH |
| Need probabilistic assignment | GMM |
| Graph structure (SERP edges) | Louvain or Leiden community detection |

## Graph-based clustering and community detection

Treat keywords as nodes, edges weighted by SERP overlap or embedding similarity above threshold. Apply community-detection algorithms.

**Louvain** (Blondel, Guillaume, Lambiotte, Lefebvre, J. Stat. Mech. 2008, P10008): greedy modularity optimization, scales to millions of nodes. The 2008 paper has been cited 20,000+ times per the authors' 2023 retrospective (arXiv:2311.06047).

**Leiden** (Traag, Waltman, van Eck, Scientific Reports 9, 2019, doi:10.1038/s41598-019-41695-z, arXiv:1810.08473) fixes Louvain's badly-connected-community defect with a refinement phase. The paper documents that up to 25 percent of Louvain communities are badly connected and up to 16 percent are disconnected. Leiden is faster than Louvain and produces better partitions. It is the standard community-detection default in 2026.

**Modularity** (Newman 2006) measures the density of edges within communities relative to a null model. The resolution parameter γ trades off cluster size: higher γ produces smaller communities. The resolution limit (Fortunato and Barthelemy 2007) means standard modularity cannot detect clusters below a size threshold; multi-resolution methods address this.

When graph-based methods outperform: when the relationship structure between keywords is more informative than absolute similarity (transitive SERP overlap chains where keyword A overlaps with B and B overlaps with C, but A and C share no direct overlap, are correctly clustered together by community detection).

## Topic modeling for short text

LDA (Blei, Ng, Jordan, JMLR 2003) is the classical generative probabilistic topic model. For keyword data its limit is severe: short text (most keywords are 1 to 5 words) provides insufficient co-occurrence, and LDA assumes longer documents.

NMF (Lee and Seung, Nature 1999) often produces more interpretable topics than LDA on short text, but still struggles below paragraph-length input.

**BERTopic** (Grootendorst, arXiv:2203.05794, March 2022) is the modern default for transformer-based topic modeling on short text. The pipeline:

1. Sentence-transformer embeddings (any model from SBERT, BGE, E5, GTE, etc.)
2. UMAP dimensionality reduction (typically to 5 to 15 dimensions)
3. HDBSCAN clustering on the reduced space
4. Class-based TF-IDF (c-TF-IDF) for topic representation

Top2Vec (Angelov 2020, arXiv:2008.09470) is a contemporary alternative with a similar pipeline.

When to use topic modeling versus clustering. Clustering produces hard assignments; topic modeling produces soft (probabilistic) assignments and explicit topic representations. For SEO, BERTopic can label clusters automatically, making it a useful complement to a clustering pipeline rather than a replacement for one.

## Hybrid clustering: the production-grade default

No single signal is sufficient. Production-quality clustering combines three:

1. **SERP overlap** as the primary «ground truth» signal because it reflects Google's actual ranking judgment.
2. **Embedding similarity** to detect semantic equivalences not captured by SERP overlap (especially for keywords with thin SERPs or new queries).
3. **Rule-based corrections** for intent classification, brand-versus-generic separation, and language separation.

Sequential approaches: pre-cluster on embeddings, refine with SERP overlap, or vice versa. Multi-signal weighted: edge weight = α · SERP_overlap + β · cosine_similarity + γ · intent_match.

Documented hybrid implementations (mentioned for methodology comparison only): Keyword Insights (SERP-first with NLP refinement), KeywordCupid (SERP overlap with ML pipeline), ContentGecko (SERP-based), Surfer SEO, Semrush Keyword Manager.

Validation rule layers. For each cluster, classify dominant intent (informational, commercial, transactional, navigational); reject clusters with mixed dominant intent; separate by language; separate brand-modified queries from generic. Per Keyword Insights documentation: «We start by clustering keywords based on SERP overlaps, then classify the intent for each keyword within the cluster. From there, we determine the dominant search intent for the entire cluster».

## LLM-assisted clustering

Direct LLM clustering of small lists (under 200 keywords) by giving the list and prompting for clusters with rationale. Quality is high but stochastic, and consistency across runs is low. Not the right level of granularity for production work.

LLM-assisted cluster labeling. Take embedding-clustered or SERP-clustered keyword groups, prompt the LLM for a canonical topic label, a primary keyword recommendation, and a content-brief seed. This is the highest-impact LLM application in clustering: cost is dominated by cluster count, not keyword count, so the unit economics work even for large corpora.

LLM-assisted cluster validation. For each cluster, prompt the LLM to evaluate intent coherence, flag clusters with mixed intent for manual review.

Edge-case resolution. For keywords near the cluster boundary (similarity score just below threshold), prompt the LLM to decide assignment.

Prompt patterns. Explicit instruction to consider search intent, expected user, content type. Structured JSON output. Few-shot examples for boundary cases. Chain-of-thought to expose reasoning when assignment is contested.

Limitations. Scalability (large input lists exceed context window). Consistency (run-to-run variance). Cost (versus deterministic clustering at scale). Hallucination (LLM may invent groupings not justified by the data).

## Cluster quality evaluation

### Internal metrics

Silhouette score (Rousseeuw, J. Comp. Appl. Math. 1987): per-point measure of cohesion versus separation, range -1 to +1, higher is better. Calinski-Harabasz index (1974): ratio of between-cluster to within-cluster dispersion, higher is better. Davies-Bouldin index (1979): average similarity between each cluster and its most similar cluster, lower is better. Dunn index. Per Chicco et al. PeerJ Computer Science 11:e3309 (2025): «The Silhouette coefficient and the Davies-Bouldin index are more informative and reliable than [Dunn, Calinski-Harabasz, Shannon entropy, Gap statistic] when assessing convex-shaped and non-nested clusters in the Euclidean space».

### External metrics

When ground truth is available: Rand Index, Adjusted Rand Index (Hubert and Arabie 1985), Normalized Mutual Information, Fowlkes-Mallows Index. Adjusted Rand Index is the field standard.

### SEO-specific evaluation

Cluster purity by intent (homogeneity of informational, commercial, transactional, navigational within each cluster). SERP cohesion within cluster (average pairwise SERP overlap across all keywords in the cluster). Cluster size distribution (heavy-tailed; flag implausibly large clusters). Manual review on a stratified sample of clusters by size and density.

### Visualization

t-SNE (van der Maaten and Hinton, JMLR 2008) and UMAP (McInnes, Healy, Melville, arXiv:1802.03426, 2018) for 2D visualization of embedding-based clusters. UMAP is faster, preserves more global structure, and is the default for inspecting embedding clusters.

## Cluster membership roles and hierarchy

Within each cluster, identify three roles. The primary keyword (highest volume, or most representative, or best matches business intent). Secondary keywords (close synonyms, paraphrases, intent-aligned variants). Supporting keywords (longer-tail entry points to the same content).

The hierarchical cluster structure: topic > sub-topic > cluster > keyword. The hierarchy informs information architecture. Pillar pages map to topics. Cluster pages map to sub-topics or specific clusters. Supporting pages address specific keywords or questions.

Selection strategies for the primary keyword: highest search volume; lowest difficulty among high-volume; highest commercial intent for revenue-priority clusters; broadest semantic coverage for hub pages.

## Cluster-to-content mapping

The «one cluster, one URL» principle: each cluster corresponds to exactly one content asset. Three legitimate exceptions: very large clusters that warrant a hub plus sub-pages; geographic variations served by separate URLs (location pages); product variants with separate inventory pages; intent splits within a cluster that warrant separate decision-stage and consideration-stage assets.

Mapping clusters to existing content versus new content. For each cluster, find the best-matching existing URL by primary-keyword query, or by content similarity to the cluster's keywords. If no good match exists, create new content.

Cannibalization prevention. If two URLs already rank for keywords in the same cluster, consolidate (301 redirect, content merge, canonical) to prevent split signals.

Internal linking implied by cluster structure. Cluster pages should link to and from the hub page. Siblings within a cluster should cross-link only when contextually useful, not blanket.

## Clustering at scale

At 10,000 keywords, any standard approach works on a laptop in minutes. At 100,000 keywords, SERP capture is the bottleneck (50 to 500 USD per pass), embedding generation is fast on GPU, clustering itself is feasible but pairwise comparisons require optimization. At 1 million keywords and above, sampling, ANN, and distributed processing become necessary.

Sampling strategies: random; stratified by volume; stratified by query length; stratified by intent classification (pre-cluster, then sample within strata).

Incremental clustering. HDBSCAN supports approximate prediction (predict cluster for new points without re-fitting). For SERP-based, recompute affected clusters when adding keywords whose SERPs overlap existing clusters.

Cluster stability over time: SERPs drift. Recompute quarterly for stable industries, monthly for fast-moving (news, e-commerce). Always recompute after major Google updates or industry shifts.

Re-clustering cadence triggers: major Google algorithm update; significant SERP feature change (AI Overview rollout to a vertical); seasonal shifts; addition of large new keyword batches; observed drift in existing cluster cohesion.

## Scenarios that need different recipes

E-commerce. Cluster by product (category-level keywords for category pages, product-level for PDP). Attribute clusters (size, color, material) for filter and facet pages. Cluster validation includes purchase-intent check: separate transactional from research-stage queries.

Editorial. Cluster by topic for evergreen content. Freshness-weighted clustering for news. For news, SERP overlap is unstable and embedding similarity is the better primary signal.

Local SEO. Location-based clustering (city + service). Service-area clusters. Do not cluster across distinct geographic markets even with high embedding similarity.

B2B. Persona-based (decision maker, end user, evaluator). Industry-vertical-based. Use-case-based. Combine with stage-of-buyer-journey.

Multilingual. Cluster per-language as the default. Cross-language clustering only for entity-resolution purposes (mapping equivalent entities across languages), not for content consolidation, since hreflang governs language separation.

AEO/GEO clustering. Optimize for the query family generated by fan-out, not the single trigger query. Per Mike King, a single trigger query may decompose into 8 to 12 sub-queries; the page should cover the entity-attribute combinations across that family. Cluster by trigger query but produce content satisfying the fan-out family.

## Common failure modes

Single-method clustering (embedding-only or SERP-only) produces systematic errors. Wrong threshold for the use case: too low merges distinct intents, too high fragments same-intent. Ignoring cluster-quality validation. Treating clusters as static (set-and-forget). Tiny clusters (1 to 2 keywords) often indicate the keyword should join an existing cluster. Huge clusters (above 50 keywords) often need decomposition by intent or by sub-topic.

Clustering before cleaning. Deduplication, normalization (lowercasing, plural and singular handling, stop-word handling per language), and intent classification must precede clustering. The cleaning-before-clustering ordering is a precondition for correctness, not an optimization.

## Why this skill ships a deterministic three-pass clusterer

The skill `keyword-intelligence` does not implement SERP overlap, embedding-based clustering, or graph community detection. It implements a deterministic three-pass algorithm based on parent-topic seeding, token overlap with light per-language stemming, and singleton formation for residuals. The full algorithm appears in [analysis-scopes.md](analysis-scopes.md) under scope 2.

The choice is justified by three commitments documented in [methodology-overview.md](methodology-overview.md). Reproducibility (two analysts on the same input must produce the same output, which excludes probabilistic and version-dependent methods unless the artifacts are pinned). Vendor neutrality (offline standard-library Python, no embedding-model dependencies). Transparency (every cluster boundary can be recomputed by hand for any pair of keywords).

The methodological cost is real. Token overlap is a weaker semantic signal than sentence embeddings. Cross-paraphrase clustering is poor. Synonym resolution depends on whether the synonyms share tokens after stemming. Pure long-tail conversational queries that share no significant tokens with their cluster head get marked as singletons more often than they should.

The methodological gain is real too. Two analysts produce identical clusters. The clustering survives every Google algorithm update and every embedding-model release without rework. Every disputed cluster boundary is resolvable by inspection of the input pair, not by reading vector dumps.

For corpora where embedding-based clustering would dominate (paraphrase-heavy long-tail conversational data, multilingual content where translation-equivalents must cluster together), the skill's deterministic approach is a baseline, not the final word. The next section describes the path to a hybrid v2.

## Roadmap toward a hybrid v2

A hybrid v2 of this skill would extend the deterministic core with three optional enrichment stages, each documented with version pinning and confidence weighting so that reproducibility is preserved.

**Stage A: SERP overlap** as a fourth pass after parent-topic, token-overlap, and singleton formation. The analyst supplies a SerpApi or DataForSEO export with top-10 organic URLs per keyword. Clusters are merged when SERP overlap exceeds 4-of-10. The skill records the SerpApi snapshot date in metadata so the analysis is reproducible against the specific snapshot, not against live SERPs.

**Stage B: Embedding similarity** as a fifth pass, using a pinned embedding model (BGE-M3 v1.0 or Multilingual E5 large v2 are the leading candidates as of 2026). Vectors are computed offline once per corpus and saved as a pinned artifact in the workspace directory. Cluster boundaries get adjusted by a documented threshold (default 0.80 cosine for the chosen model). The model version becomes part of the methodology version.

**Stage C: LLM-assisted labeling** as an optional output enrichment, not a clustering step. Cluster heads receive a one-line semantic label produced by a pinned LLM call (model and temperature recorded). The labels appear in the Markdown report and the JSON, never in the cluster-membership decision.

The principle for v2: every embedding-derived signal must be added with explicit version pinning and explicit confidence weighting, never as a replacement for the deterministic core but as an enrichment whose contribution to the composite is itself auditable.

The technical work is feasible. The methodological work, designing the version pinning and the confidence-weighting protocol, is the harder part and is where most of v2 design effort would land.

## Tool implementations referenced in this file

Mentioned for methodology comparison only, not endorsement.

Python: scikit-learn (KMeans, AgglomerativeClustering, DBSCAN, OPTICS, SpectralClustering, MeanShift, GaussianMixture, AffinityPropagation, Birch); the hdbscan library by McInnes; sentence-transformers by Reimers and Gurevych; FAISS; FlagEmbedding (BGE); InstructorEmbedding; networkx, igraph, graph-tool for community detection (Louvain, Leiden); BERTopic by Grootendorst.

R: cluster, dbscan, dbscan::hdbscan, igraph, factoextra, NbClust packages.

Commercial SEO clustering tools (mentioned for methodology comparison only): Keyword Insights (SERP-based, 1-7 overlap configurable, NLP refinement, intent classification); KeywordCupid (SERP-based ML); Ahrefs Keyword Manager; Semrush Keyword Strategy Builder; Surfer SEO; ClusterAI; SE Ranking; ContentGecko (free SERP-based tier); Sistrix; SearchPilot for empirical validation.

For a vendor-neutral framework, custom implementation against documented methodology remains preferable. The skill `keyword-intelligence` is one such implementation, and the path to extending it through hybrid v2 is documented above.
