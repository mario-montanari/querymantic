# Multi-language

This file documents the per-language rules the skill applies. For the cross-language entity equivalence and the role of MUM in multilingual retrieval, see [entity-and-topical-authority.md](entity-and-topical-authority.md). For the embedding models that handle multilingual semantic similarity (BGE-M3, Multilingual E5), see [semantics.md](semantics.md).

## Contents

- Supported languages and scope
- Language detection
- Per-language reference
  - English
  - French
  - German
  - Spanish
- Stop words per language
- Morphological normalization
- Intent markers per language
- Question detection per language
- Stemming rules
- Mixed-language keywords
- What stays out of scope

## Supported languages and scope

The skill supports four languages with full per-language rule sets: English, French, German, and Spanish. These four cover the majority of commercial keyword research engagements outside the Asian markets and form a coherent IndoEuropean cluster where the same methodology applies with language-specific parameter tables.

For other languages (Italian, Portuguese, Dutch, Polish, and so on), the skill runs in degraded mode: it accepts the keywords, performs token statistics and basic intent detection using the language-agnostic rules, but does not apply morphological normalization, language-specific stop word filtering, or language-tuned intent markers. The output flags every keyword in unsupported languages with `language_support: degraded` so the analyst knows the confidence is lower.

Adding a new language requires extending the four reference tables in this file (stop words, intent markers, question patterns, stemming rules) and the language-detection signal table. The architecture is designed for incremental language expansion.

## Language detection

When the source CSV provides a language column (Semrush, Ahrefs, Moz support this), the skill trusts it. When the column is absent or the value is empty, the skill infers the language from three signals applied in order.

Character set check. Keywords containing characters outside the basic Latin range receive an immediate language vote: `ñ` and `¿` for Spanish, `ü` `ö` `ä` `ß` for German, `é` `è` `ç` `à` for French, none of these for English. A single distinctive character is a strong signal but not conclusive: a Spanish keyword might lack `ñ`, a German keyword might lack umlauts.

Stop word matching. The skill counts how many tokens in the keyword appear in each language's stop-word list. The language with the highest match count wins, with ties resolved by the character set check.

Morphological marker check. Specific suffixes signal language: `-tion` and `-ment` (English-French ambiguity, resolved by the rest of the keyword), `-ung` and `-keit` (German), `-ción` and `-dad` (Spanish), `-eur` and `-eux` (French). These are tiebreakers, not primary signals.

The detector outputs a language code (ISO 639-1) and a confidence score from 0 to 1. Confidence above 0.7 routes the keyword to the full language-specific rule set. Confidence between 0.4 and 0.7 routes the keyword with a flag for analyst review. Confidence below 0.4 marks the keyword as `language: unknown` and uses the language-agnostic fallback rules.

## Per-language reference

The reference tables below cover the high-frequency tokens, markers, and patterns the skill uses. The tables are intentionally compact: a long stop-word list is counterproductive (it removes useful tokens like «with» or «for» that distinguish related queries). Each list represents the working compromise between noise reduction and signal preservation.

### English

Search behavior. Highest data quality across all major commercial tools. Highest baseline volumes. Strongest intent stratification because tools have invested most in English intent labeling. SERP features richest in English markets.

Practical implications. English corpora support the full scope battery with the highest confidence. AIO eligibility detection is most reliable. GEO opportunity classification is most reliable because long-tail conversational data is densest in English.

### French

Search behavior. Strong tool coverage but with consistent volume undercount versus English for equivalent intent. The French market is more sensitive to formal versus informal register: «vous» (formal you) versus «tu» (informal you) in conversational queries shifts the implied user demographic and the SERP.

Practical implications. The skill applies a `register_marker` flag to French keywords containing `vous` or `tu`-form verbs. This does not enter scoring directly but appears in the enrichment output for analyst awareness. Apostrophes are common in queries (`l'assurance`, `d'achat`); the tokenizer splits them and treats both halves as significant tokens for matching.

### German

Search behavior. Compound nouns are a defining feature: `Krankenversicherung` (health insurance), `Kindergeldnachweis` (child benefit certificate). Search behavior often produces single-token «keywords» that are semantically multi-word in any other language.

Practical implications. The skill applies a compound-decomposition pass on German keywords with token length above 8 characters and a recognized compound suffix (`-versicherung`, `-system`, `-recht`, `-schutz`, `-nachweis`, `-bericht`). The decomposition is not stored as separate tokens but is exposed in `evidence` for cluster assignment: a single-token compound keyword can match a multi-token cluster head if the compound contains the head's significant tokens.

Capitalization. German nouns are capitalized in well-formed text but search queries usually arrive lowercased. The skill lowercases before processing but applies an uppercasing heuristic for proper-noun detection during entity extraction.

### Spanish

Search behavior. Significant variation between European Spanish (es-ES) and Latin American Spanish (es-MX, es-AR, and others). Same query intent is sometimes phrased with different verbs and prepositions across regions. «Coche» (Spain) versus «carro» (Mexico) for «car» is a frequent example.

Practical implications. The skill respects the country code when present in the canonical schema. When a Spanish corpus mixes Spain and Latin American sources, the skill flags the regional split in the corpus-level summary so the analyst can choose to segment the analysis by country.

Inverted question marks. Spanish queries that arrive as full sentences include `¿` at the start. The skill detects this as a definitive question signal (higher confidence than English question detection because the `?` at end is sometimes typed and sometimes not).

## Stop words per language

The stop-word lists are intentionally minimal. Each list contains 40-60 entries: articles, common prepositions, basic conjunctions, and frequent auxiliary verbs. The skill does not include topic-bearing words, long modal expressions, or rare function words.

| Language | Sample of stop words |
|---|---|
| English | the, a, an, of, in, on, at, to, for, by, with, and, or, but, is, are, was, were, be, been, being, has, have, had, do, does, did, will, would, can, could, should, may, might, must, this, that, these, those |
| French | le, la, les, un, une, des, de, du, des, à, au, aux, en, dans, sur, sous, pour, par, avec, sans, et, ou, mais, est, sont, était, étaient, être, a, ont, avait, avoir, ce, cette, ces, je, tu, il, elle, nous, vous, ils, elles |
| German | der, die, das, den, dem, ein, eine, einen, einem, einer, eines, und, oder, aber, in, an, auf, bei, mit, von, zu, für, ist, sind, war, waren, sein, hat, haben, hatte, hatten, ich, du, er, sie, es, wir, ihr |
| Spanish | el, la, los, las, un, una, unos, unas, de, del, en, a, al, por, para, con, sin, sobre, y, o, pero, es, son, era, eran, ser, ha, han, había, habían, haber, esto, esta, este, estos, estas, yo, tú, él, ella, nosotros, vosotros, ellos, ellas |

The full lists are part of the analyze script's internal data and the analyst can override them via `--stop-words-<lang>` parameters when a domain-specific list is needed (legal corpora frequently need shorter stop-word lists; medical corpora frequently need lists that retain certain prepositions).

## Morphological normalization

Morphological normalization aims to detect that two surface forms refer to the same underlying intent without losing the distinction when the distinction matters. The skill applies four transformations.

Lowercasing applies in all languages. Original casing is preserved in `keyword_original`.

Diacritic-tolerant matching for languages with optional diacritics in user input. A user typing `cafe` and a user typing `café` are treated as expressing the same query for matching purposes; the canonical form keeps the diacritic when the source provided it.

Plural normalization for cluster matching only, not for keyword identity. The cluster algorithm treats `running shoe` and `running shoes` as cluster siblings, but they remain separate rows in the canonical corpus with their separate volume signals.

Light suffix stripping per language for the cluster overlap calculation:

- English: `-s`, `-es`, `-ies` (with `y` restoration), `-ed`, `-ing`, `-er`, `-est`
- French: `-s`, `-e`, `-es`, `-ent` (verb plural)
- German: `-en`, `-er`, `-es` (genitive), `-e` (plural)
- Spanish: `-s`, `-es`, `-as`, `-os`

Stemming is intentionally light. Aggressive stemming (Porter, Snowball) collapses useful distinctions. The skill prefers under-stemming with manual cluster review over over-stemming with apparent precision.

## Intent markers per language

Each language has a marker table for the four intent layers used by the intent classification scope. The tables are reference, not exhaustive: real corpora produce variations, and the analyst can extend tables via `--intent-markers-<lang>` configuration.

### Transactional markers

| Language | Markers |
|---|---|
| English | buy, purchase, order, get, find, where to buy, near me, deal, deals, discount, sale, price, prices, cheap, cheapest, free shipping, in stock |
| French | acheter, achat, commander, où acheter, prix, pas cher, soldes, réduction, livraison gratuite, en stock |
| German | kaufen, bestellen, wo kaufen, preis, preise, günstig, billig, rabatt, angebot, kostenloser versand, auf lager |
| Spanish | comprar, compra, pedir, dónde comprar, precio, barato, ofertas, descuento, envío gratis, en stock |

### Commercial-investigation markers

| Language | Markers |
|---|---|
| English | best, top, vs, versus, review, reviews, comparison, compare, alternative, alternatives, pros and cons |
| French | meilleur, meilleurs, top, contre, vs, avis, comparaison, comparer, alternative |
| German | bester, beste, top, gegen, vs, test, tests, bewertung, vergleich, alternative |
| Spanish | mejor, mejores, top, contra, vs, reseña, opinión, comparación, comparar, alternativa |

### Informational markers

| Language | Markers |
|---|---|
| English | what, how, why, when, where, who, which, guide, tutorial, learn, meaning, definition, examples |
| French | quoi, comment, pourquoi, quand, où, qui, quel, quelle, guide, tutoriel, apprendre, signification, définition, exemples |
| German | was, wie, warum, wann, wo, wer, welche, welcher, anleitung, tutorial, lernen, bedeutung, definition, beispiele |
| Spanish | qué, cómo, por qué, cuándo, dónde, quién, cuál, guía, tutorial, aprender, significado, definición, ejemplos |

### Navigational markers

| Language | Markers (plus brand list) |
|---|---|
| English | login, log in, sign in, account, support, help, contact, careers |
| French | connexion, se connecter, compte, support, aide, contact, carrières |
| German | anmeldung, anmelden, einloggen, konto, support, hilfe, kontakt, karriere |
| Spanish | iniciar sesión, conexión, cuenta, soporte, ayuda, contacto, carreras |

Branded navigational queries combine these markers with the brand list provided to the skill.

## Question detection per language

Question detection runs three tests in OR for every language:

1. The keyword starts with an interrogative pronoun for the language.
2. The keyword ends with `?`.
3. The keyword matches a language-specific question pattern.

The language-specific patterns include forms that do not start with a pronoun but are still question-shaped:

- English: «<verb> X to Y» where the verb is `do/does`, `is/are`, `can/could`, `will/would` («can I cancel my subscription»).
- French: inversion patterns with hyphen («peut-on annuler»), «est-ce que» constructions.
- German: verb-first patterns («kann man X»), «gibt es» constructions.
- Spanish: queries starting with verbs in indicative or subjunctive, presence of `¿` at the start.

The detector returns a confidence score reflecting which test fired. A keyword passing all three tests has higher confidence than one passing only the third.

## Stemming rules

The stemming applied during cluster overlap calculation is light-touch, language-specific, and reversible.

Reversibility matters because the skill never modifies the canonical keyword. Stemming runs on a derived `_token_stem` field used only for cluster matching. The display form, the scoring form, and the citation form are always the original keyword.

Light-touch matters because aggressive stemming collapses useful distinctions. «Run» (verb) and «runner» (noun) are usefully separate in many corpora, and the skill keeps them separate by default. The configuration accepts a `--stemming-aggressive` flag for analysts who prefer broader collapse.

The exact stemming rules per language are codified in the analyze script and surfaced through the `--show-stemming` flag. The rules covered above (suffix stripping table) are the defaults.

## Mixed-language keywords

Real corpora contain mixed-language keywords. Two patterns are common.

Brand mixed with native language. «Nike scarpe» (Italian-English mix) or «Apple Macbook acheter» (French-English mix). The skill detects these by sampling tokens against multiple language stop-word lists and choosing the dominant language. The mixed nature is flagged in `evidence`.

English technical terms in non-English queries. «WordPress installer» (French) or «cloud backup einrichten» (German). The skill recognizes a small list of high-frequency English technical terms (`wordpress`, `seo`, `cloud`, `api`, `dashboard`, `analytics`) as language-neutral; their presence does not disqualify the dominant-language detection.

Mixed-language queries are processed using the dominant language's rule set. The mix is preserved in the canonical keyword.

## What stays out of scope

Right-to-left languages (Arabic, Hebrew). The character-set detection identifies them, the skill marks them as `language_support: out_of_scope`, and processing stops at token statistics.

CJK languages (Chinese, Japanese, Korean). Tokenization in CJK requires segmentation algorithms that are out of scope for an offline standard-library skill. CJK keywords are processed as single tokens with degraded confidence.

Hindi, Thai, and other Indic and Southeast Asian languages. Same treatment as CJK: detected, flagged, processed at degraded confidence.

The skill is honest about these limits. A corpus that requires CJK or RTL analysis at full quality needs a different tool. The skill's value for those markets is limited to the universal computations (token statistics, score arithmetic on already-supplied volumes and difficulties).
