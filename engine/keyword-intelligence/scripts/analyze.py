#!/usr/bin/env python3
"""
analyze.py - Keyword intelligence pipeline.

Runs the seven-stage analysis on one or more keyword CSV exports and produces
the canonical JSON state. Output artifacts (Markdown, JSON, CSV, TXT) are
written by report.py from the same canonical state.

Usage:
    python analyze.py --inputs file1.csv file2.csv \\
        --client-domain example.com \\
        --brand-list "example,ex" \\
        --output output/run_2026-05-05/

For full parameter list, run: python analyze.py --help

Methodology version: 1.0.0
Skill version: 1.0.0
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import logging
import math
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

METHODOLOGY_VERSION = "1.0.0"
SKILL_VERSION = "1.0.0"

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logger = logging.getLogger("keyword_intelligence")


# =====================================================================
# Constants and language tables
# =====================================================================

SUPPORTED_LANGUAGES = ("en", "fr", "de", "es")

STOP_WORDS = {
    "en": {"the", "a", "an", "of", "in", "on", "at", "to", "for", "by", "with",
           "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
           "has", "have", "had", "do", "does", "did", "will", "would", "can",
           "could", "should", "may", "might", "must", "this", "that", "these",
           "those", "i", "you", "he", "she", "it", "we", "they"},
    "fr": {"le", "la", "les", "un", "une", "des", "de", "du", "à", "au", "aux",
           "en", "dans", "sur", "sous", "pour", "par", "avec", "sans", "et",
           "ou", "mais", "est", "sont", "était", "étaient", "être", "a", "ont",
           "avait", "avoir", "ce", "cette", "ces", "je", "tu", "il", "elle",
           "nous", "vous", "ils", "elles"},
    "de": {"der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
           "einer", "eines", "und", "oder", "aber", "in", "an", "auf", "bei",
           "mit", "von", "zu", "für", "ist", "sind", "war", "waren", "sein",
           "hat", "haben", "hatte", "hatten", "ich", "du", "er", "sie", "es",
           "wir", "ihr"},
    "es": {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
           "en", "a", "al", "por", "para", "con", "sin", "sobre", "y", "o",
           "pero", "es", "son", "era", "eran", "ser", "ha", "han", "había",
           "habían", "haber", "esto", "esta", "este", "estos", "estas", "yo",
           "tú", "él", "ella", "nosotros", "vosotros", "ellos", "ellas"},
}

INTENT_MARKERS = {
    "en": {
        "transactional": ["buy", "purchase", "order", "find", "near me",
                          "deal", "deals", "discount", "sale", "price",
                          "prices", "cheap", "cheapest", "free shipping",
                          "in stock"],
        "commercial": ["best", "top", "vs", "versus", "review", "reviews",
                       "comparison", "compare", "alternative", "alternatives",
                       "pros and cons"],
        "informational": ["what", "how", "why", "when", "where", "who",
                          "which", "guide", "tutorial", "learn", "meaning",
                          "definition", "examples"],
        "navigational": ["login", "log in", "sign in", "account", "support",
                         "help", "contact", "careers"],
    },
    "fr": {
        "transactional": ["acheter", "achat", "commander", "où acheter",
                          "prix", "pas cher", "soldes", "réduction",
                          "livraison gratuite", "en stock"],
        "commercial": ["meilleur", "meilleurs", "top", "contre", "vs", "avis",
                       "comparaison", "comparer", "alternative"],
        "informational": ["quoi", "comment", "pourquoi", "quand", "où", "qui",
                          "quel", "quelle", "guide", "tutoriel", "apprendre",
                          "signification", "définition", "exemples"],
        "navigational": ["connexion", "se connecter", "compte", "support",
                         "aide", "contact", "carrières"],
    },
    "de": {
        "transactional": ["kaufen", "bestellen", "wo kaufen", "preis",
                          "preise", "günstig", "billig", "rabatt", "angebot",
                          "kostenloser versand", "auf lager"],
        "commercial": ["bester", "beste", "top", "gegen", "vs", "test",
                       "tests", "bewertung", "vergleich", "alternative"],
        "informational": ["was", "wie", "warum", "wann", "wo", "wer",
                          "welche", "welcher", "anleitung", "tutorial",
                          "lernen", "bedeutung", "definition", "beispiele"],
        "navigational": ["anmeldung", "anmelden", "einloggen", "konto",
                         "support", "hilfe", "kontakt", "karriere"],
    },
    "es": {
        "transactional": ["comprar", "compra", "pedir", "dónde comprar",
                          "precio", "barato", "ofertas", "descuento",
                          "envío gratis", "en stock"],
        "commercial": ["mejor", "mejores", "top", "contra", "vs", "reseña",
                       "opinión", "comparación", "comparar", "alternativa"],
        "informational": ["qué", "cómo", "por qué", "cuándo", "dónde",
                          "quién", "cuál", "guía", "tutorial", "aprender",
                          "significado", "definición", "ejemplos"],
        "navigational": ["iniciar sesión", "conexión", "cuenta", "soporte",
                         "ayuda", "contacto", "carreras"],
    },
}

QUESTION_PRONOUNS = {
    "en": ["what", "how", "why", "when", "where", "who", "which", "whose"],
    "fr": ["quoi", "comment", "pourquoi", "quand", "où", "qui", "quel",
           "quelle", "quels", "quelles"],
    "de": ["was", "wie", "warum", "wann", "wo", "wer", "welche", "welcher",
           "welches"],
    "es": ["qué", "cómo", "por qué", "cuándo", "dónde", "quién", "cuál",
           "cuáles"],
}

LANGUAGE_CHARS = {
    "fr": set("àâäçéèêëîïôûùüÿœæ"),
    "de": set("äöüß"),
    "es": set("ñáéíóúü¿¡"),
}

CANONICAL_SERP_FEATURES = {
    "featured snippet": "featured_snippet",
    "people also ask": "paa",
    "paa": "paa",
    "ai overview": "ai_overview",
    "ai_overview": "ai_overview",
    "knowledge panel": "knowledge_panel",
    "local pack": "local_pack",
    "shopping": "shopping",
    "images": "images",
    "video": "video",
    "videos": "video",
    "news": "news",
    "sitelinks": "sitelinks",
}

SOURCE_RELIABILITY = {
    "gsc": 1.0,
    "semrush": 0.9,
    "ahrefs": 0.9,
    "moz": 0.9,
    "ubersuggest": 0.75,
    "generic": 0.7,
    "seed": 0.5,
}


# =====================================================================
# Data classes
# =====================================================================

@dataclass
class KeywordRecord:
    """Canonical representation of one keyword observation."""
    keyword: str
    keyword_original: str
    source: str
    source_file: str
    source_row: int
    language: Optional[str] = None
    language_confidence: float = 0.0
    country: Optional[str] = None
    volume: Optional[int] = None
    # Holds a Decimal between map_row_to_canonical and
    # normalize_difficulty_column, an int afterwards.
    difficulty: Optional[int] = None
    cpc: Optional[float] = None
    position: Optional[int] = None
    serp_features: List[str] = field(default_factory=list)
    traffic_potential: Optional[int] = None
    intent_label_raw: Optional[str] = None
    clicks: Optional[int] = None
    impressions: Optional[int] = None
    ctr: Optional[float] = None
    parent_topic: Optional[str] = None
    competitor_url: Optional[str] = None
    domain_rank: Optional[int] = None
    enrichment: Dict[str, Any] = field(default_factory=dict)
    scopes: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, Any] = field(default_factory=dict)


# =====================================================================
# CLI parsing
# =====================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all parameters."""
    parser = argparse.ArgumentParser(
        prog="analyze",
        description=("Keyword intelligence pipeline. Runs sourcing, "
                     "normalization, enrichment, scope analysis, scoring, "
                     "and gap analysis on CSV exports from keyword "
                     "research tools, then writes the canonical JSON "
                     "state for downstream artifact generation."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See SKILL.md and references/ for full methodology.",
    )

    parser.add_argument("--inputs", nargs="+", required=True,
                        help="One or more CSV files or directories.")
    parser.add_argument("--output", required=True,
                        help="Output directory for the canonical JSON.")
    parser.add_argument("--label", default="",
                        help="Engagement label (sanitized to lowercase).")
    parser.add_argument("--client-domain", default="",
                        help="Client domain for cannibalization, "
                             "striking-distance, content-gap analysis.")
    parser.add_argument("--brand-list", default="",
                        help="Comma-separated brand variations.")
    parser.add_argument("--mapping",
                        help="JSON file with custom column-name mappings.")
    parser.add_argument("--custom-rules",
                        help="JSON file with custom scope rules.")
    parser.add_argument("--content-recency",
                        help="JSON file mapping URL to last-modified "
                             "date for freshness-gap analysis.")

    parser.add_argument("--quickwin-volume-min", type=int, default=100)
    parser.add_argument("--quickwin-volume-max", type=int, default=5000)
    parser.add_argument("--quickwin-difficulty-max", type=int, default=35)
    parser.add_argument("--striking-min", type=int, default=4)
    parser.add_argument("--striking-max", type=int, default=20)
    parser.add_argument("--cluster-overlap-min", type=float, default=0.60)
    parser.add_argument("--aio-eligibility-min", type=int, default=60)
    parser.add_argument("--geo-opportunity-min", type=int, default=60)
    parser.add_argument("--seasonality-cv-min", type=float, default=0.40)
    parser.add_argument("--seasonality-cv-strong", type=float, default=0.70)
    parser.add_argument("--long-tail-tokens-min", type=int, default=5)
    parser.add_argument("--volume-reference", type=int, default=100000)

    parser.add_argument("--cannibalization-include-branded",
                        action="store_true")
    parser.add_argument("--reconciliation",
                        choices=["median", "mean", "max", "min"],
                        default="median")
    parser.add_argument("--csv-line-endings",
                        choices=["crlf", "lf"], default="crlf")
    parser.add_argument("--json-only", action="store_true",
                        help="Skip artifact generation; produce JSON only.")
    parser.add_argument("--show-mapping", action="store_true",
                        help="Print the column mapping for each input "
                             "and exit without analysis.")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")

    return parser


# =====================================================================
# Stage 1-2: Sourcing and normalization
# =====================================================================

# Per-tool column mapping. Lowercased headers map to canonical names.
TOOL_MAPPINGS = {
    "semrush": {
        "keyword": "keyword",
        "volume": "volume",
        "search volume": "volume",
        "keyword difficulty": "difficulty",
        "kd%": "difficulty",
        "kd": "difficulty",
        "cpc": "cpc",
        "cpc (usd)": "cpc",
        "position": "position",
        "pos.": "position",
        "serp features by keyword": "serp_features",
        "serp features": "serp_features",
        "traffic": "traffic_potential",
        "intent": "intent_label_raw",
        "country": "country",
        "parent topic": "parent_topic",
        "url": "competitor_url",
    },
    "ahrefs": {
        "keyword": "keyword",
        "volume": "volume",
        "kd": "difficulty",
        "cpc": "cpc",
        "current position": "position",
        "position": "position",
        "serp features": "serp_features",
        "traffic potential (tp)": "traffic_potential",
        "intents": "intent_label_raw",
        "country": "country",
        "parent topic": "parent_topic",
        "top url": "competitor_url",
        "url": "competitor_url",
        "dr": "domain_rank",
        "clicks": "clicks",
    },
    "gsc": {
        "top queries": "keyword",
        "query": "keyword",
        "clicks": "clicks",
        "impressions": "impressions",
        "ctr": "ctr",
        "position": "position",
        "country": "country",
    },
    "moz": {
        "keyword": "keyword",
        "monthly volume": "volume",
        "volume": "volume",
        "difficulty": "difficulty",
        "organic ctr": "ctr",
        "serp features": "serp_features",
        "country": "country",
    },
    "ubersuggest": {
        "keyword": "keyword",
        "volume": "volume",
        "search volume": "volume",
        "seo difficulty": "difficulty",
        "sd": "difficulty",
        "cpc": "cpc",
    },
    "generic": {
        "keyword": "keyword",
        "volume": "volume",
        "vol": "volume",
        "monthly searches": "volume",
        "difficulty": "difficulty",
        "kd": "difficulty",
        "cpc": "cpc",
        "position": "position",
    },
}

TOOL_SIGNATURES = [
    # (tool_name, set of headers that strongly indicate the tool)
    ("semrush", {"keyword difficulty", "serp features by keyword"}),
    ("semrush", {"kd%", "parent topic"}),
    ("ahrefs", {"kd", "traffic potential (tp)"}),
    ("ahrefs", {"current position", "intents"}),
    ("gsc", {"top queries", "impressions"}),
    ("gsc", {"query", "ctr", "impressions"}),
    ("moz", {"monthly volume", "organic ctr"}),
    ("ubersuggest", {"seo difficulty"}),
]


def detect_tool(headers: List[str]) -> str:
    """Detect the source tool from CSV headers."""
    header_set = {h.strip().lower() for h in headers}
    for tool_name, signature in TOOL_SIGNATURES:
        if signature.issubset(header_set):
            return tool_name
    if "keyword" in header_set:
        return "generic"
    raise ValueError(
        f"Cannot detect tool from headers: {headers}. "
        f"Supply --mapping with explicit column maps."
    )


def detect_encoding(path: Path) -> str:
    """Detect encoding of a CSV file by sniffing first 4 KB."""
    try:
        with path.open("rb") as f:
            head = f.read(4096)
    except OSError as e:
        raise IOError(f"Cannot read file {path}: {e}")

    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if head.startswith(b"\xff\xfe") or head.startswith(b"\xfe\xff"):
        return "utf-16"

    try:
        head.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    try:
        head.decode("latin-1")
        return "latin-1"
    except UnicodeDecodeError:
        raise ValueError(f"Cannot detect encoding for {path}")


def detect_separator(path: Path, encoding: str) -> str:
    """Detect CSV separator by checking consistency on first 10 lines."""
    candidates = [",", ";", "\t", "|"]
    best = ","
    best_score = -1

    with path.open(encoding=encoding) as f:
        head_lines = [f.readline() for _ in range(10)]

    head_lines = [ln for ln in head_lines if ln.strip()]
    if not head_lines:
        raise ValueError(f"File {path} appears empty")

    for sep in candidates:
        counts = [ln.count(sep) for ln in head_lines]
        if not counts or counts[0] == 0:
            continue
        consistency = sum(1 for c in counts if c == counts[0])
        if consistency > best_score:
            best_score = consistency
            best = sep

    return best


def load_csv(path: Path, override_mapping: Optional[Dict[str, str]] = None
             ) -> Tuple[str, List[Dict[str, str]]]:
    """Load a CSV file and return (tool_name, list of row dicts)."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 500:
        raise ValueError(f"File {path} is {size_mb:.1f} MB, exceeds 500 MB limit")

    encoding = detect_encoding(path)
    separator = detect_separator(path, encoding)

    with path.open(encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=separator)
        if reader.fieldnames is None:
            raise ValueError(f"File {path} has no header row")
        rows = list(reader)
        headers = list(reader.fieldnames)

    if not rows:
        raise ValueError(f"File {path} has no data rows")

    if override_mapping:
        tool = "generic"
    else:
        tool = detect_tool(headers)

    logger.info("Loaded %d rows from %s (tool=%s, encoding=%s, sep=%r)",
                len(rows), path.name, tool, encoding, separator)
    return tool, rows


def coerce_int(value: Any) -> Optional[int]:
    """Coerce a string to int, handling locale separators."""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip().replace(",", "").replace(".", "")
    s = s.rstrip("%")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def coerce_float(value: Any) -> Optional[float]:
    """Coerce a string to float, handling locale separators and currency."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    for symbol in ("$", "€", "£", "¥"):
        s = s.replace(symbol, "")
    s = s.strip()
    pct = False
    if s.endswith("%"):
        pct = True
        s = s[:-1]
    s = s.replace(",", "")
    try:
        v = float(s)
        if pct:
            v = v / 100.0
        return v
    except ValueError:
        return None


def coerce_difficulty(value: Any) -> Optional[Decimal]:
    """Parse one difficulty cell, keeping the decimal point meaningful.

    Difficulty is the one metric exported both as a 0-100 integer and as
    a 0-1 decimal, so the thousands-separator stripping of coerce_int
    would corrupt it ("0.5" must stay 0.5, never become 5). This
    dedicated path parses the cell as an exact decimal value; a trailing
    percent sign is dropped. The 0-1 versus 0-100 decision is NOT taken
    here: it belongs to normalize_difficulty_column, which sees the
    whole column.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    s = str(value).strip().rstrip("%").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def coerce_serp_features(value: Any) -> List[str]:
    """Normalize SERP feature labels to canonical lowercase snake_case."""
    if value is None or value == "":
        return []
    items = str(value).split(",")
    out = []
    for item in items:
        normalized = item.strip().lower()
        out.append(CANONICAL_SERP_FEATURES.get(normalized,
                                                f"_unknown_{normalized}"))
    return [x for x in out if x]


def normalize_keyword(raw: str) -> str:
    """Lowercase, trim, NFC normalize, collapse spaces."""
    if raw is None:
        return ""
    s = unicodedata.normalize("NFC", str(raw))
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def map_row_to_canonical(tool: str, row: Dict[str, str], path: Path,
                         row_num: int,
                         override_mapping: Optional[Dict[str, str]] = None
                         ) -> Optional[KeywordRecord]:
    """Map a raw CSV row to the canonical KeywordRecord."""
    mapping = TOOL_MAPPINGS.get(tool, TOOL_MAPPINGS["generic"]).copy()
    if override_mapping:
        for raw_col, canonical in override_mapping.items():
            mapping[raw_col.lower()] = canonical

    canonical_data: Dict[str, Any] = {}
    for raw_col, value in row.items():
        if raw_col is None:
            continue
        canonical_name = mapping.get(raw_col.strip().lower())
        if canonical_name and value not in (None, ""):
            canonical_data[canonical_name] = value

    raw_keyword = canonical_data.get("keyword", "")
    if not raw_keyword:
        logger.debug("Row %d in %s missing keyword, skipping", row_num,
                     path.name)
        return None

    keyword_normalized = normalize_keyword(raw_keyword)
    if not keyword_normalized:
        return None
    if len(keyword_normalized) > 200:
        logger.debug("Row %d in %s keyword too long (%d chars), skipping",
                     row_num, path.name, len(keyword_normalized))
        return None

    record = KeywordRecord(
        keyword=keyword_normalized,
        keyword_original=str(raw_keyword).strip(),
        source=tool,
        source_file=str(path),
        source_row=row_num,
        country=canonical_data.get("country"),
        volume=coerce_int(canonical_data.get("volume")),
        difficulty=coerce_difficulty(canonical_data.get("difficulty")),
        cpc=coerce_float(canonical_data.get("cpc")),
        position=coerce_int(canonical_data.get("position")),
        serp_features=coerce_serp_features(canonical_data.get("serp_features")),
        traffic_potential=coerce_int(canonical_data.get("traffic_potential")),
        intent_label_raw=canonical_data.get("intent_label_raw"),
        clicks=coerce_int(canonical_data.get("clicks")),
        impressions=coerce_int(canonical_data.get("impressions")),
        ctr=coerce_float(canonical_data.get("ctr")),
        parent_topic=canonical_data.get("parent_topic"),
        competitor_url=canonical_data.get("competitor_url"),
        domain_rank=coerce_int(canonical_data.get("domain_rank")),
    )

    if record.position is not None and record.position > 100:
        record.position = None
    return record


def normalize_difficulty_column(records: List[KeywordRecord],
                                path: Path) -> None:
    """Bring one file's difficulty column onto the canonical 0-100 scale.

    Scale detection is per column, never per value: when every valid
    difficulty in the file is <= 1.0, the column is read as a 0-1 scale
    and multiplied by 100. A column holding only the integers 0 and 1 is
    ambiguous (it could be a flag); by design it is treated as a 0-1
    scale too, so 0 maps to 0 and 1 maps to 100. Every value is then
    rounded half-up on its exact decimal value (ROUND_HALF_UP,
    deterministic: 45.5 becomes 46) and values above 100 are clamped
    to 100.
    """
    values = [r.difficulty for r in records if r.difficulty is not None]
    if not values:
        return
    if max(values) <= 1:
        logger.info("Difficulty column in %s has every value <= 1.0: "
                    "reading it as a 0-1 scale and multiplying by 100",
                    path.name)
        for r in records:
            if r.difficulty is not None:
                r.difficulty = r.difficulty * 100
    for r in records:
        if r.difficulty is None:
            continue
        d = int(r.difficulty.quantize(Decimal("1"),
                                      rounding=ROUND_HALF_UP))
        if d > 100:
            logger.warning("Row %d in %s has difficulty %d > 100, clamping",
                           r.source_row, path.name, d)
            d = 100
        r.difficulty = d


# =====================================================================
# Stage 3: Enrichment
# =====================================================================

def detect_language(keyword: str, declared: Optional[str] = None
                    ) -> Tuple[str, float]:
    """Detect language of a keyword, returning (lang_code, confidence)."""
    if declared:
        declared_lower = declared.lower().strip()[:2]
        if declared_lower in SUPPORTED_LANGUAGES:
            return declared_lower, 1.0

    char_set = set(keyword)
    char_votes = {"en": 0, "fr": 0, "de": 0, "es": 0}
    for lang, chars in LANGUAGE_CHARS.items():
        if char_set & chars:
            char_votes[lang] = 2

    tokens = keyword.split()
    stop_votes = {lang: 0 for lang in SUPPORTED_LANGUAGES}
    for tok in tokens:
        for lang in SUPPORTED_LANGUAGES:
            if tok in STOP_WORDS[lang]:
                stop_votes[lang] += 1

    total_votes = {
        lang: char_votes.get(lang, 0) + stop_votes.get(lang, 0)
        for lang in SUPPORTED_LANGUAGES
    }
    best_lang = max(total_votes, key=lambda x: total_votes[x])
    best_score = total_votes[best_lang]

    if best_score == 0:
        return "en", 0.4
    confidence = min(1.0, 0.5 + best_score * 0.15)
    return best_lang, confidence


def detect_intent_vector(keyword: str, lang: str,
                         serp_features: List[str],
                         intent_label_raw: Optional[str]
                         ) -> Tuple[Dict[str, str], float]:
    """Compute four-axis intent vector and confidence."""
    markers = INTENT_MARKERS.get(lang, INTENT_MARKERS["en"])
    weights: Dict[str, float] = {
        "informational": 0.0,
        "navigational": 0.0,
        "transactional": 0.0,
        "commercial_investigation": 0.0,
    }

    pronouns = QUESTION_PRONOUNS.get(lang, QUESTION_PRONOUNS["en"])
    first_token = keyword.split(" ", 1)[0] if keyword else ""
    if first_token in pronouns:
        weights["informational"] += 0.7

    for marker in markers["transactional"]:
        if marker in keyword:
            weights["transactional"] += 0.8
            break

    for marker in markers["commercial"]:
        if f" {marker} " in f" {keyword} " or keyword.startswith(f"{marker} "):
            weights["commercial_investigation"] += 0.7
            break

    for marker in markers["navigational"]:
        if marker in keyword:
            weights["navigational"] += 0.9
            break

    for marker in markers["informational"]:
        if marker in keyword.split():
            weights["informational"] += 0.4
            break

    if "featured_snippet" in serp_features or "paa" in serp_features \
            or "ai_overview" in serp_features:
        weights["informational"] += 0.1

    if "shopping" in serp_features or "local_pack" in serp_features:
        weights["transactional"] += 0.1

    if intent_label_raw:
        raw_lower = intent_label_raw.lower()
        for key in weights:
            if key.replace("_", " ") in raw_lower or key in raw_lower:
                weights[key] += 0.1

    if all(v == 0 for v in weights.values()):
        weights["informational"] = 0.3

    query_type = max(weights, key=lambda k: weights[k])
    confidence = min(1.0, weights[query_type])

    funnel_map = {
        "informational": "awareness",
        "navigational": "consideration",
        "commercial_investigation": "consideration",
        "transactional": "decision",
    }
    funnel_stage = funnel_map[query_type]

    voice_markers = ("near me", "please", "ok google")
    convo_markers = ("can you", "tell me about", "how do i")
    modality = "typed"
    if any(m in keyword for m in convo_markers) or len(keyword.split()) > 8:
        modality = "conversational_ai"
    elif any(m in keyword for m in voice_markers):
        modality = "voice"

    seasonal_markers = ("christmas", "black friday", "easter", "summer",
                        "winter", "spring", "autumn")
    year_pattern = re.compile(r"\b(20\d{2})\b")
    temporal = "evergreen"
    if any(m in keyword for m in seasonal_markers):
        temporal = "seasonal"
    elif year_pattern.search(keyword):
        temporal = "event_driven"

    vector = {
        "query_type": query_type,
        "funnel_stage": funnel_stage,
        "modality": modality,
        "temporal": temporal,
    }
    return vector, confidence


def detect_branded(keyword: str, brand_list: List[str]) -> Tuple[bool, str]:
    """Test if keyword contains any brand variation."""
    if not brand_list:
        return False, ""
    lower = keyword.lower()
    for brand in brand_list:
        b = brand.strip().lower()
        if not b:
            continue
        if b in lower:
            return True, b
    return False, ""


def detect_question(keyword: str, lang: str) -> Tuple[bool, float]:
    """Test if a keyword is question-shaped."""
    confidence = 0.0
    pronouns = QUESTION_PRONOUNS.get(lang, QUESTION_PRONOUNS["en"])
    first = keyword.split(" ", 1)[0] if keyword else ""
    if first in pronouns:
        confidence += 0.6
    if keyword.endswith("?"):
        confidence += 0.5
    if keyword.startswith("¿"):
        confidence += 0.5
    return confidence > 0.4, min(1.0, confidence)


def compute_token_stats(keyword: str) -> Dict[str, Any]:
    """Compute token count, char count, head/mid/tail class."""
    tokens = keyword.split()
    n = len(tokens)
    if n <= 2:
        tail_class = "head"
    elif n <= 4:
        tail_class = "mid"
    else:
        tail_class = "long_tail"
    return {
        "token_count": n,
        "char_count": len(keyword),
        "tail_class": tail_class,
    }


def enrich_record(record: KeywordRecord, brand_list: List[str]) -> None:
    """Run all Stage 3 enrichments on a single record."""
    lang, lang_conf = detect_language(record.keyword, record.language)
    record.language = lang
    record.language_confidence = lang_conf

    intent_vec, intent_conf = detect_intent_vector(
        record.keyword, lang, record.serp_features, record.intent_label_raw
    )

    is_branded, brand_hit = detect_branded(record.keyword, brand_list)
    is_question, q_conf = detect_question(record.keyword, lang)
    token_stats = compute_token_stats(record.keyword)

    record.enrichment = {
        "intent_vector": intent_vec,
        "intent_confidence": intent_conf,
        "branded": is_branded,
        "brand_match": brand_hit,
        "question_shape": is_question,
        "question_confidence": q_conf,
        "language_confidence": lang_conf,
        **token_stats,
    }


# =====================================================================
# Stage 4: Scope analysis
# =====================================================================

def scope_intent_classification(record: KeywordRecord) -> Dict[str, Any]:
    """Scope 1: intent classification (already in enrichment, expose here)."""
    vec = record.enrichment.get("intent_vector", {})
    return {
        "label": vec.get("query_type", "unknown"),
        "confidence": record.enrichment.get("intent_confidence", 0.0),
        "evidence": [f"vector: {vec}"],
    }


def scope_aio_eligibility(record: KeywordRecord, threshold: int
                          ) -> Dict[str, Any]:
    """Scope 3: AI Overview eligibility."""
    if "ai_overview" in record.serp_features:
        return {
            "label": "confirmed",
            "confidence": 1.0,
            "evidence": ["serp feature ai_overview present"],
            "score": 100,
        }

    score = 0
    evidence: List[str] = []
    intent = record.enrichment.get("intent_vector", {}).get("query_type")
    if intent == "informational":
        score += 30
        evidence.append("informational intent")
    if record.enrichment.get("question_shape"):
        score += 25
        evidence.append("question shape")
    if record.enrichment.get("token_count", 0) >= 5:
        score += 10
        evidence.append("long-tail length")
    comp_markers = ["how to", "comment", "wie", "cómo", "vs", "versus"]
    if any(m in record.keyword for m in comp_markers):
        score += 20
        evidence.append("comparison/how-to marker")
    score = min(score, 90)

    if score >= threshold:
        label = "eligible"
    elif score >= 40:
        label = "possibly_eligible"
    else:
        label = "not_eligible"

    return {
        "label": label,
        "confidence": min(1.0, score / 100.0 + 0.1),
        "evidence": evidence,
        "score": score,
    }


def scope_geo_opportunity(record: KeywordRecord, aio_label: str,
                          threshold: int) -> Dict[str, Any]:
    """Scope 4: GEO opportunity."""
    score = 0
    evidence: List[str] = []
    convo_markers = ("can you", "tell me about", "how do i", "what is the best")
    if any(m in record.keyword for m in convo_markers):
        score += 25
        evidence.append("conversational shape")
    if record.enrichment.get("token_count", 0) >= 6:
        score += 20
        evidence.append("long-tail >=6 tokens")
    intent = record.enrichment.get("intent_vector", {}).get("query_type")
    if intent in ("informational", "commercial_investigation"):
        score += 20
        evidence.append("informational/commercial intent")
    temporal = record.enrichment.get("intent_vector", {}).get("temporal")
    if temporal in ("evergreen", "event_driven"):
        score += 15
        evidence.append(f"temporal: {temporal}")
    if "vs" in record.keyword or "versus" in record.keyword:
        score += 20
        evidence.append("comparative")
    score = min(score, 95)

    label = "neither"
    if score >= threshold and aio_label in ("confirmed", "eligible"):
        label = "dual"
    elif score >= threshold:
        label = "geo_only"
    elif aio_label in ("confirmed", "eligible"):
        label = "aio_only"

    return {
        "label": label,
        "confidence": min(1.0, score / 100.0 + 0.1),
        "evidence": evidence,
        "score": score,
    }


def scope_quick_win(record: KeywordRecord, args: argparse.Namespace
                    ) -> Dict[str, Any]:
    """Scope 5: quick wins."""
    if record.volume is None or record.difficulty is None:
        return {"label": "not_quick_win", "confidence": 0.0,
                "evidence": ["volume or difficulty missing"]}

    cond_volume = (args.quickwin_volume_min <= record.volume
                   <= args.quickwin_volume_max)
    cond_difficulty = record.difficulty <= args.quickwin_difficulty_max
    cond_position = record.position is None or (
        args.striking_min <= record.position <= 30
    )
    intent = record.enrichment.get("intent_vector", {}).get("query_type")
    cond_intent = intent != "navigational"

    if cond_volume and cond_difficulty and cond_position and cond_intent:
        margin = args.quickwin_difficulty_max - record.difficulty
        confidence = min(1.0, 0.6 + margin / 100.0)
        return {"label": "quick_win", "confidence": confidence,
                "evidence": ["volume in range", "difficulty under cap",
                             "position permissive", "intent permissive"]}
    return {"label": "not_quick_win", "confidence": 0.5, "evidence": []}


def scope_striking_distance(record: KeywordRecord, args: argparse.Namespace,
                            client_domain: str) -> Dict[str, Any]:
    """Scope 8: striking distance."""
    if record.position is None or record.volume is None:
        return {"label": "not_striking", "confidence": 0.0, "evidence": []}
    if not (args.striking_min <= record.position <= args.striking_max):
        return {"label": "not_striking", "confidence": 0.0, "evidence": []}
    if record.volume < 50:
        return {"label": "not_striking", "confidence": 0.0,
                "evidence": ["volume < 50"]}
    if client_domain and record.competitor_url \
            and client_domain not in record.competitor_url:
        return {"label": "not_striking", "confidence": 0.0,
                "evidence": ["url not client domain"]}

    pos = record.position
    if pos <= 7:
        return {"label": "top_page_climb", "confidence": 0.85,
                "evidence": [f"position {pos}, top page candidate"]}
    if pos <= 13:
        return {"label": "second_page_break", "confidence": 0.75,
                "evidence": [f"position {pos}, second page lift"]}
    return {"label": "third_page_lift", "confidence": 0.65,
            "evidence": [f"position {pos}, third page lift"]}


def scope_branded(record: KeywordRecord) -> Dict[str, Any]:
    """Scope 9: branded vs non-branded."""
    if record.enrichment.get("branded"):
        return {"label": "branded", "confidence": 0.95,
                "evidence": [f"matched: {record.enrichment.get('brand_match')}"]}
    return {"label": "non_branded", "confidence": 0.95, "evidence": []}


def scope_question_paa(record: KeywordRecord) -> Dict[str, Any]:
    """Scope 10: questions and PAA."""
    is_q = record.enrichment.get("question_shape", False)
    has_paa = "paa" in record.serp_features
    if is_q and has_paa:
        label = "question_and_paa"
    elif is_q:
        label = "question"
    elif has_paa:
        label = "paa_only"
    else:
        label = "neither"
    return {"label": label, "confidence": 0.9 if (is_q or has_paa) else 0.95,
            "evidence": []}


def scope_long_tail(record: KeywordRecord, args: argparse.Namespace
                    ) -> Dict[str, Any]:
    """Scope 12: long tail."""
    n = record.enrichment.get("token_count", 0)
    if n >= args.long_tail_tokens_min:
        modality = record.enrichment.get("intent_vector", {}).get("modality")
        if modality == "conversational_ai":
            return {"label": "long_tail_conversational", "confidence": 0.9,
                    "evidence": [f"tokens={n}, conversational"]}
        return {"label": "long_tail_classical", "confidence": 0.85,
                "evidence": [f"tokens={n}"]}
    if n >= 3:
        return {"label": "mid", "confidence": 0.8, "evidence": []}
    return {"label": "head", "confidence": 0.85, "evidence": []}


def scope_seasonality(record: KeywordRecord) -> Dict[str, Any]:
    """Scope 11: seasonality (lite, marker-based without trend data)."""
    seasonal = ("christmas", "black friday", "easter", "summer", "winter",
                "spring", "autumn", "halloween", "thanksgiving",
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november",
                "december")
    year_pattern = re.compile(r"\b(20\d{2})\b")
    for s in seasonal:
        if s in record.keyword:
            return {"label": "seasonal", "confidence": 0.9,
                    "evidence": [f"marker: {s}"]}
    if year_pattern.search(record.keyword):
        return {"label": "event_driven", "confidence": 0.85,
                "evidence": ["year marker"]}
    return {"label": "evergreen", "confidence": 0.7, "evidence": []}


def run_per_keyword_scopes(record: KeywordRecord, args: argparse.Namespace,
                            client_domain: str) -> None:
    """Run scopes that operate per single keyword."""
    record.scopes["intent_classification"] = \
        scope_intent_classification(record)
    aio = scope_aio_eligibility(record, args.aio_eligibility_min)
    record.scopes["aio_eligibility"] = aio
    record.scopes["geo_opportunity"] = scope_geo_opportunity(
        record, aio["label"], args.geo_opportunity_min)
    record.scopes["quick_wins"] = scope_quick_win(record, args)
    record.scopes["striking_distance"] = scope_striking_distance(
        record, args, client_domain)
    record.scopes["branded"] = scope_branded(record)
    record.scopes["question_paa"] = scope_question_paa(record)
    record.scopes["long_tail"] = scope_long_tail(record, args)
    record.scopes["seasonality"] = scope_seasonality(record)


# =====================================================================
# Cluster assignment (corpus-level)
# =====================================================================

def light_stem(token: str, lang: str) -> str:
    """Light suffix stripping for cluster matching."""
    if len(token) <= 3:
        return token
    if lang == "en":
        for suf in ("ies", "es", "s", "ed", "ing", "er", "est"):
            if token.endswith(suf) and len(token) - len(suf) >= 3:
                return token[:-len(suf)] + ("y" if suf == "ies" else "")
    elif lang == "fr":
        for suf in ("ent", "es", "s", "e"):
            if token.endswith(suf) and len(token) - len(suf) >= 3:
                return token[:-len(suf)]
    elif lang == "de":
        for suf in ("en", "er", "es", "e"):
            if token.endswith(suf) and len(token) - len(suf) >= 3:
                return token[:-len(suf)]
    elif lang == "es":
        for suf in ("es", "as", "os", "s"):
            if token.endswith(suf) and len(token) - len(suf) >= 3:
                return token[:-len(suf)]
    return token


def significant_tokens(keyword: str, lang: str) -> List[str]:
    """Tokens excluding stop words, length >= 3, lightly stemmed."""
    stops = STOP_WORDS.get(lang, STOP_WORDS["en"])
    return [light_stem(t, lang) for t in keyword.split()
            if t not in stops and len(t) >= 3]


def assign_clusters(records: List[KeywordRecord], overlap_min: float
                    ) -> List[Dict[str, Any]]:
    """Three-pass deterministic clustering."""
    clusters: List[Dict[str, Any]] = []
    assigned: Dict[int, int] = {}

    by_parent: Dict[str, List[int]] = {}
    for idx, r in enumerate(records):
        if r.parent_topic:
            by_parent.setdefault(r.parent_topic, []).append(idx)

    for parent, indices in by_parent.items():
        head_idx = max(indices, key=lambda i: records[i].volume or 0)
        head = records[head_idx]
        cluster = {
            "head": head.keyword,
            "head_index": head_idx,
            "members": indices,
            "parent_topic": parent,
            "confidence": 0.95,
        }
        clusters.append(cluster)
        for i in indices:
            assigned[i] = len(clusters) - 1

    sorted_unassigned = sorted(
        [i for i in range(len(records)) if i not in assigned],
        key=lambda i: records[i].volume or 0,
        reverse=True,
    )

    for idx in sorted_unassigned:
        if idx in assigned:
            continue
        r = records[idx]
        tokens = set(significant_tokens(r.keyword, r.language or "en"))
        if not tokens:
            continue

        best_cluster = -1
        best_overlap = 0.0
        for ci, cluster in enumerate(clusters):
            head = records[cluster["head_index"]]
            head_tokens = set(significant_tokens(
                head.keyword, head.language or "en"))
            if not head_tokens:
                continue
            overlap = len(tokens & head_tokens) / max(
                len(tokens), len(head_tokens))
            if overlap > best_overlap:
                best_overlap = overlap
                best_cluster = ci

        if best_cluster >= 0 and best_overlap >= overlap_min:
            clusters[best_cluster]["members"].append(idx)
            assigned[idx] = best_cluster
        else:
            clusters.append({
                "head": r.keyword,
                "head_index": idx,
                "members": [idx],
                "parent_topic": None,
                "confidence": 0.7,
            })
            assigned[idx] = len(clusters) - 1

    for ci, cluster in enumerate(clusters):
        cluster["size"] = len(cluster["members"])
        cluster["volume_total"] = sum(
            records[i].volume or 0 for i in cluster["members"])
        intents = [records[i].enrichment.get("intent_vector", {}).get(
            "query_type") for i in cluster["members"]]
        intents = [x for x in intents if x]
        if intents:
            from collections import Counter
            cluster["dominant_intent"] = Counter(intents).most_common(1)[0][0]
        else:
            cluster["dominant_intent"] = "unknown"

    for idx, ci in assigned.items():
        records[idx].scopes["cluster_assignment"] = {
            "label": clusters[ci]["head"],
            "confidence": clusters[ci]["confidence"],
            "evidence": [f"cluster size {clusters[ci]['size']}"],
            "cluster_index": ci,
        }

    return clusters


# =====================================================================
# Stage 5: Scoring
# =====================================================================

def normalize_volume(volume: Optional[int], reference: int) -> Optional[float]:
    if volume is None or volume <= 0:
        return None
    return min(100.0, 100.0 * math.log10(max(1, volume)) / math.log10(reference))


def normalize_position(position: Optional[int]) -> Optional[float]:
    if position is None:
        return None
    if position == 1:
        return 100.0
    if position <= 3:
        return 90.0
    if position <= 10:
        return 80.0 - (position - 4) * 5
    if position <= 20:
        return 50.0 - (position - 11) * 3
    if position <= 50:
        return max(5.0, 25.0 - (position - 21) * 0.5)
    return 5.0


def intent_score_for(intent: str, variant: str = "main") -> float:
    if variant == "main":
        return {"commercial_investigation": 100, "transactional": 100,
                "informational": 80, "navigational": 60}.get(intent, 50)
    if variant == "quick_win":
        return {"commercial_investigation": 100, "transactional": 80,
                "informational": 70, "navigational": 0}.get(intent, 40)
    if variant == "aeo":
        return {"navigational": 100, "informational": 70,
                "commercial_investigation": 50, "transactional": 30}.get(
                    intent, 40)
    return 50.0


def compute_main_composite(record: KeywordRecord, args: argparse.Namespace
                           ) -> Tuple[float, float]:
    """Compute main composite score and confidence."""
    volume_score = normalize_volume(record.volume, args.volume_reference) or 0
    diff_score = (100 - record.difficulty) if record.difficulty is not None \
        else 50
    intent = record.enrichment.get("intent_vector", {}).get(
        "query_type", "informational")
    int_score = intent_score_for(intent, "main")
    pos_score = normalize_position(record.position) or 30
    cluster_strength = 60.0
    if record.scopes.get("cluster_assignment", {}).get("cluster_index", -1) >= 0:
        cluster_strength = 70.0
    serp_winn = 60.0 if record.serp_features else 50.0

    score = (0.35 * volume_score + 0.25 * diff_score + 0.15 * int_score
             + 0.10 * pos_score + 0.10 * cluster_strength
             + 0.05 * serp_winn)

    completeness = sum([
        0.35 if record.volume is not None else 0,
        0.25 if record.difficulty is not None else 0,
        0.15,
        0.10 if record.position is not None else 0.05,
        0.10,
        0.05 if record.serp_features else 0.025,
    ])
    source_rel = SOURCE_RELIABILITY.get(record.source, 0.7)
    enrichment_cert = (
        record.enrichment.get("language_confidence", 0.5)
        * record.enrichment.get("intent_confidence", 0.5)
    ) ** 0.5
    confidence = (completeness * source_rel * enrichment_cert) ** (1 / 3)
    return round(score, 1), round(confidence, 3)


def compute_quick_win_composite(record: KeywordRecord,
                                 args: argparse.Namespace
                                 ) -> Tuple[float, float]:
    if record.scopes.get("quick_wins", {}).get("label") != "quick_win":
        return 0.0, 0.0
    volume_score = normalize_volume(record.volume, args.volume_reference) or 0
    diff_score = (100 - record.difficulty) if record.difficulty is not None \
        else 50
    proximity = 80.0 if record.position is None else (
        normalize_position(record.position) or 30)
    intent = record.enrichment.get("intent_vector", {}).get(
        "query_type", "informational")
    int_score = intent_score_for(intent, "quick_win")
    cluster_bonus = 60.0
    serp_winn = 60.0 if record.serp_features else 50.0

    score = (0.30 * diff_score + 0.25 * volume_score + 0.15 * proximity
             + 0.15 * int_score + 0.10 * cluster_bonus + 0.05 * serp_winn)
    return round(score, 1), 0.85


def compute_strategic_composite(record: KeywordRecord,
                                 args: argparse.Namespace
                                 ) -> Tuple[float, float]:
    cluster_strength = 70.0
    volume_score = normalize_volume(record.volume, args.volume_reference) or 0
    intent = record.enrichment.get("intent_vector", {}).get(
        "query_type", "informational")
    int_score = intent_score_for(intent, "main")
    gap_severity = 50.0
    geo_score = record.scopes.get("geo_opportunity", {}).get("score", 0)
    diff_score = (100 - record.difficulty) if record.difficulty is not None \
        else 50

    score = (0.30 * cluster_strength + 0.20 * volume_score + 0.15 * int_score
             + 0.15 * gap_severity + 0.10 * geo_score + 0.10 * diff_score)
    return round(score, 1), 0.80


def compute_aeo_composite(record: KeywordRecord, args: argparse.Namespace
                          ) -> Tuple[float, float]:
    brand_score = 100.0 if record.enrichment.get("branded") else 30.0
    cannibalization_score = 0.0
    geo_score = record.scopes.get("geo_opportunity", {}).get("score", 0)
    aio_score = record.scopes.get("aio_eligibility", {}).get("score", 0)
    volume_score = normalize_volume(record.volume, args.volume_reference) or 0

    score = (0.30 * brand_score + 0.25 * cannibalization_score
             + 0.20 * geo_score + 0.15 * aio_score + 0.10 * volume_score)
    return round(score, 1), 0.80


def score_record(record: KeywordRecord, args: argparse.Namespace) -> None:
    """Compute all four composites for a single record."""
    main, conf_main = compute_main_composite(record, args)
    qw, conf_qw = compute_quick_win_composite(record, args)
    strategic, conf_str = compute_strategic_composite(record, args)
    aeo, conf_aeo = compute_aeo_composite(record, args)

    record.scores = {
        "main": {"score": main, "confidence": conf_main},
        "quick_win": {"score": qw, "confidence": conf_qw},
        "strategic": {"score": strategic, "confidence": conf_str},
        "aeo_defensive": {"score": aeo, "confidence": conf_aeo},
    }


# =====================================================================
# Main pipeline
# =====================================================================

def expand_inputs(input_args: List[str]) -> List[Path]:
    """Resolve input arguments to a flat list of CSV paths."""
    out: List[Path] = []
    for arg in input_args:
        p = Path(arg)
        if p.is_dir():
            out.extend(sorted(p.glob("*.csv")))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f"Input not found: {arg}")
    if not out:
        raise ValueError("No CSV files found in inputs")
    return out


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_label(label: str) -> str:
    if not label:
        return ""
    s = re.sub(r"[^a-z0-9-]", "-", label.lower())
    return re.sub(r"-+", "-", s).strip("-")


def run_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    """Run the full seven-stage pipeline and return canonical state."""
    input_paths = expand_inputs(args.inputs)
    override_mapping: Optional[Dict[str, str]] = None
    if args.mapping:
        with open(args.mapping, encoding="utf-8") as f:
            override_mapping = json.load(f)

    brand_list = [b.strip() for b in args.brand_list.split(",")
                  if b.strip()]

    all_records: List[KeywordRecord] = []
    input_manifest = []

    for path in input_paths:
        tool, rows = load_csv(path, override_mapping)
        file_hash = hash_file(path)
        manifest_entry = {
            "path": str(path),
            "rows": len(rows),
            "source": tool,
            "sha256": file_hash,
        }
        input_manifest.append(manifest_entry)

        file_records: List[KeywordRecord] = []
        for row_num, row in enumerate(rows, start=2):
            rec = map_row_to_canonical(tool, row, path, row_num,
                                       override_mapping)
            if rec is not None:
                file_records.append(rec)
        normalize_difficulty_column(file_records, path)
        all_records.extend(file_records)

    logger.info("Stage 1-2 done: %d canonical records from %d files",
                len(all_records), len(input_paths))

    for r in all_records:
        enrich_record(r, brand_list)
    logger.info("Stage 3 done: enrichment applied to %d records",
                len(all_records))

    clusters = assign_clusters(all_records, args.cluster_overlap_min)
    logger.info("Cluster assignment: %d clusters formed", len(clusters))

    for r in all_records:
        run_per_keyword_scopes(r, args, args.client_domain)
    logger.info("Stage 4 done: per-keyword scopes applied")

    for r in all_records:
        score_record(r, args)
    logger.info("Stage 5 done: composite scores computed")

    canonical = {
        "run_metadata": {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "label": sanitize_label(args.label),
            "methodology_version": METHODOLOGY_VERSION,
            "skill_version": SKILL_VERSION,
        },
        "input_manifest": {
            "files": input_manifest,
            "client_domain": args.client_domain,
            "brand_list": brand_list,
        },
        "parameters": vars(args),
        "corpus_summary": build_corpus_summary(all_records),
        "keywords": [serialize_record(r) for r in all_records],
        "clusters": clusters,
        "gaps": compute_gaps(all_records, args, clusters),
    }
    return canonical


def serialize_record(r: KeywordRecord) -> Dict[str, Any]:
    """Serialize a KeywordRecord for JSON output."""
    return {
        "keyword": r.keyword,
        "keyword_original": r.keyword_original,
        "language": r.language,
        "language_confidence": r.language_confidence,
        "country": r.country,
        "source": r.source,
        "source_file": r.source_file,
        "source_row": r.source_row,
        "metrics": {
            "volume": r.volume,
            "difficulty": r.difficulty,
            "cpc": r.cpc,
            "position": r.position,
            "serp_features": r.serp_features,
            "traffic_potential": r.traffic_potential,
            "clicks": r.clicks,
            "impressions": r.impressions,
            "ctr": r.ctr,
        },
        "enrichment": r.enrichment,
        "scopes": r.scopes,
        "scores": r.scores,
    }


# Demand Opportunity Score weights. Each term is normalized to [0, 1] and the
# weights sum to 1.0, so the score lands on a 0-100 scale. The blend rewards a
# corpus that combines high-quality opportunities with reachable near-term work
# and AI-search surface, rather than raw volume alone.
DOS_WEIGHT_MAIN_QUALITY = 0.30    # overall quality of the opportunity set
DOS_WEIGHT_QUICK_WIN = 0.25       # immediate, reachable wins
DOS_WEIGHT_STRIKING = 0.20        # near-term lift on existing positions
DOS_WEIGHT_AIO = 0.15             # AI Overview surface
DOS_WEIGHT_GEO = 0.10             # generative citation upside

_STRIKING_LABELS = ("top_page_climb", "second_page_break", "third_page_lift")


def compute_demand_opportunity_score(records: List[KeywordRecord],
                                     aio_share: float, geo_share: float
                                     ) -> float:
    """Single 0-100 headline score for the corpus.

    Blends overall opportunity quality, immediate quick-win density,
    striking-distance density, and AI-search surface. Returns a value the
    report and executive summary can lead with so the corpus has one number
    a decision-maker can remember.
    """
    total = max(1, len(records))
    mean_main = sum(
        r.scores.get("main", {}).get("score", 0) for r in records
    ) / total
    mean_main_norm = max(0.0, min(1.0, mean_main / 100.0))
    quick_win_density = sum(
        1 for r in records
        if r.scopes.get("quick_wins", {}).get("label") == "quick_win"
    ) / total
    striking_density = sum(
        1 for r in records
        if r.scopes.get("striking_distance", {}).get("label")
        in _STRIKING_LABELS
    ) / total

    score = 100.0 * (
        DOS_WEIGHT_MAIN_QUALITY * mean_main_norm
        + DOS_WEIGHT_QUICK_WIN * quick_win_density
        + DOS_WEIGHT_STRIKING * striking_density
        + DOS_WEIGHT_AIO * max(0.0, min(1.0, aio_share))
        + DOS_WEIGHT_GEO * max(0.0, min(1.0, geo_share))
    )
    return round(score, 1)


def build_corpus_summary(records: List[KeywordRecord]) -> Dict[str, Any]:
    """Compute corpus-level summary statistics."""
    from collections import Counter
    by_source = Counter(r.source for r in records)
    by_language = Counter(r.language or "unknown" for r in records)
    by_intent = Counter(
        r.enrichment.get("intent_vector", {}).get("query_type", "unknown")
        for r in records
    )
    aio_share = sum(1 for r in records
                    if r.scopes.get("aio_eligibility", {}).get("label")
                    in ("confirmed", "eligible")) / max(1, len(records))
    geo_share = sum(1 for r in records
                    if r.scopes.get("geo_opportunity", {}).get("label")
                    in ("dual", "geo_only")) / max(1, len(records))

    return {
        "total_keywords": len(records),
        "by_source": dict(by_source),
        "by_language": dict(by_language),
        "by_intent": dict(by_intent),
        "aio_eligibility_share": round(aio_share, 3),
        "geo_opportunity_share": round(geo_share, 3),
        "demand_opportunity_score": compute_demand_opportunity_score(
            records, aio_share, geo_share),
    }


def compute_gaps(records: List[KeywordRecord], args: argparse.Namespace,
                 clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Stage 6: lightweight gap analysis."""
    keyword_gap = []
    content_gap_intents = set()
    aeo_geo_gap = []

    for r in records:
        is_competitor_only = (r.competitor_url and args.client_domain
                              and args.client_domain not in (
                                  r.competitor_url or ""))
        if is_competitor_only and (r.position is None or r.position > 100):
            keyword_gap.append(r.keyword)

        if r.scopes.get("aio_eligibility", {}).get("label") in (
                "confirmed", "eligible"):
            if r.position is None or r.position > 10:
                aeo_geo_gap.append(r.keyword)

        intent = r.enrichment.get("intent_vector", {}).get("query_type")
        if intent:
            content_gap_intents.add(intent)

    return {
        "keyword_gap": {"count": len(keyword_gap),
                         "samples": keyword_gap[:20]},
        "content_gap": {"intents_present": sorted(content_gap_intents)},
        "aeo_geo_gap": {"count": len(aeo_geo_gap),
                          "samples": aeo_geo_gap[:20]},
    }


def write_canonical(canonical: Dict[str, Any], output_dir: Path) -> Path:
    """Write canonical JSON to output_dir/analysis.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = output_dir / "_metadata"
    metadata_dir.mkdir(exist_ok=True)

    json_path = output_dir / "analysis.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)

    config_path = metadata_dir / "run_config.json"
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(canonical["parameters"], f, indent=2, ensure_ascii=False)

    manifest_path = metadata_dir / "input_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(canonical["input_manifest"], f, indent=2,
                  ensure_ascii=False)

    version_path = metadata_dir / "methodology_version.txt"
    version_path.write_text(METHODOLOGY_VERSION + "\n", encoding="utf-8")

    logger.info("Canonical JSON written to %s", json_path)
    return json_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else (
        logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)

    try:
        if args.show_mapping:
            paths = expand_inputs(args.inputs)
            for path in paths:
                tool, rows = load_csv(path)
                mapping = TOOL_MAPPINGS.get(tool, {})
                print(f"\n{path.name} (detected: {tool})")
                for raw, canonical in sorted(mapping.items()):
                    print(f"  {raw:30s} -> {canonical}")
            return 0

        canonical = run_pipeline(args)
        output_dir = Path(args.output)
        write_canonical(canonical, output_dir)

        if not args.json_only:
            report_script = Path(__file__).resolve().parent / "report.py"
            if report_script.exists():
                json_path_arg = output_dir / "analysis.json"
                cmd = [sys.executable, str(report_script),
                       "--input", str(json_path_arg),
                       "--output-dir", str(output_dir)]
                result = subprocess.run(cmd, shell=False, check=False,
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning("report.py exited with code %d: %s",
                                   result.returncode, result.stderr.strip())
            else:
                logger.warning("report.py not found; JSON written, "
                               "artifacts skipped")

        print(f"\nAnalysis complete. Output: {output_dir}")
        print(f"Total keywords: {canonical['corpus_summary']['total_keywords']}")
        print(f"Clusters: {len(canonical['clusters'])}")
        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 2
    except ValueError as e:
        logger.error("Validation error: %s", e)
        return 3
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
