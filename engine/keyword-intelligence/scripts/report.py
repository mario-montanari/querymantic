#!/usr/bin/env python3
"""
report.py - Artifact generator for keyword intelligence analysis.

Reads the canonical JSON state produced by analyze.py and writes the
human-facing output artifacts: a Markdown report for delivery, an enriched
CSV for analyst portability, a TXT executive summary for decision-makers,
and per-cluster content briefs to seed editorial planning. The JSON itself
is already written by analyze.py; this script consumes the canonical state
and produces the human-facing files.

Usage:
    python report.py --input output/run_2026-05-05/analysis.json
    python report.py --input output/run_2026-05-05/analysis.json --top-n 30

For CLI invocation outside the analyze.py pipeline. analyze.py imports
generate_artifacts() directly when not run with --json-only.

Methodology version: 1.0.0
Skill version: 1.0.0
"""

import argparse
import csv
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("keyword_intelligence.report")

REPORT_TOP_N_DEFAULT = 20
EXEC_SUMMARY_LINE_CAP = 80
BRIEFS_TOP_N_DEFAULT = 15

# Editorial format suggested for each dominant intent. Used to seed the
# per-cluster content briefs; the analyst can override per case.
FORMAT_BY_INTENT = {
    "informational": "guide or explainer article",
    "commercial_investigation": "comparison or review page",
    "transactional": "product or category page",
    "navigational": "brand or destination page",
}


# =====================================================================
# CLI
# =====================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="report",
        description="Generate Markdown, CSV, and TXT artifacts from "
                    "the canonical JSON state produced by analyze.py.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True,
                        help="Path to analysis.json")
    parser.add_argument("--output-dir",
                        help="Output directory (defaults to JSON's "
                             "parent directory)")
    parser.add_argument("--top-n", type=int, default=REPORT_TOP_N_DEFAULT,
                        help="Number of rows in top-opportunities tables")
    parser.add_argument("--csv-columns", default="full",
                        choices=["full", "minimal"],
                        help="CSV column preset")
    parser.add_argument("--csv-line-endings",
                        choices=["crlf", "lf"], default="crlf")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


# =====================================================================
# Markdown report
# =====================================================================

def md_table(headers: List[str], rows: List[List[Any]]) -> str:
    """Build a Markdown table."""
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        cells = [str(c) if c is not None else "" for c in row]
        cells = [c.replace("|", "\\|").replace("\n", " ") for c in cells]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def fmt_int(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def fmt_float(value: Any, decimals: int = 2) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def truncate(text: str, max_len: int = 80) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"


def section_header() -> str:
    return "# Keyword intelligence report\n"


def section_engagement_context(canonical: Dict[str, Any]) -> str:
    meta = canonical.get("run_metadata", {})
    manifest = canonical.get("input_manifest", {})
    label = meta.get("label") or "(no label)"
    timestamp = meta.get("timestamp", "")
    client_domain = manifest.get("client_domain") or "(not set)"
    files = manifest.get("files", [])
    sources = ", ".join(sorted({f["source"] for f in files}))
    languages = sorted({
        k.get("language", "unknown")
        for k in canonical.get("keywords", [])
    })
    languages_str = ", ".join(languages) if languages else "n/a"

    return (f"## Engagement context\n\n"
            f"- Engagement label: `{label}`\n"
            f"- Run timestamp: {timestamp}\n"
            f"- Client domain: {client_domain}\n"
            f"- Source tools: {sources}\n"
            f"- Languages observed: {languages_str}\n"
            f"- Methodology version: "
            f"{meta.get('methodology_version', 'n/a')}\n")


def ascii_bar(value: float, max_width: int = 40) -> str:
    n = int(round(value * max_width))
    return "█" * n + "░" * (max_width - n)


def section_corpus_summary(canonical: Dict[str, Any]) -> str:
    summary = canonical.get("corpus_summary", {})
    total = summary.get("total_keywords", 0)
    out = ["## Corpus summary", ""]
    dos = summary.get("demand_opportunity_score")
    if dos is not None:
        out.append(f"**Demand Opportunity Score: {dos:.1f} / 100.** A single "
                   f"headline reading of how much actionable demand the corpus "
                   f"holds, blending opportunity quality, quick-win density, "
                   f"striking-distance lift, and AI-search surface.")
        out.append("")
    out.append(f"Total keywords in canonical corpus: {fmt_int(total)}")
    out.append("")

    by_source = summary.get("by_source", {})
    if by_source:
        out.append("### Distribution by source")
        out.append("")
        max_count = max(by_source.values()) if by_source else 1
        rows = []
        for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
            share = count / max(1, total)
            bar = ascii_bar(count / max_count, 30)
            rows.append([src, fmt_int(count), f"{share:.1%}", bar])
        out.append(md_table(["Source", "Count", "Share", ""], rows))
        out.append("")

    by_lang = summary.get("by_language", {})
    if by_lang:
        out.append("### Distribution by language")
        out.append("")
        rows = []
        for lang, count in sorted(by_lang.items(), key=lambda x: -x[1]):
            share = count / max(1, total)
            rows.append([lang, fmt_int(count), f"{share:.1%}"])
        out.append(md_table(["Language", "Count", "Share"], rows))
        out.append("")

    by_intent = summary.get("by_intent", {})
    if by_intent:
        out.append("### Distribution by intent")
        out.append("")
        rows = []
        for intent, count in sorted(by_intent.items(), key=lambda x: -x[1]):
            share = count / max(1, total)
            rows.append([intent, fmt_int(count), f"{share:.1%}"])
        out.append(md_table(["Intent", "Count", "Share"], rows))
        out.append("")
        top_intent, top_count = max(by_intent.items(), key=lambda x: x[1])
        out.append(
            f"Demand leans {top_intent} at {top_count / max(1, total):.0%} "
            f"of the corpus, which sets the dominant editorial format before "
            f"cluster-level planning begins."
        )
        out.append("")

    aio_share = summary.get("aio_eligibility_share", 0)
    geo_share = summary.get("geo_opportunity_share", 0)
    out.append("### AI search routing summary")
    out.append("")
    out.append(f"- AIO-eligible share of corpus: {aio_share:.1%}")
    out.append(f"- GEO-opportunity share of corpus: {geo_share:.1%}")
    out.append("")
    out.append(
        f"About {aio_share:.0%} of demand can surface inside AI Overviews. "
        f"The GEO-opportunity slice is where generative engines may cite the "
        f"client directly instead of a competitor."
    )
    out.append("")
    return "\n".join(out)


def section_score_distribution(canonical: Dict[str, Any]) -> str:
    keywords = canonical.get("keywords", [])
    if not keywords:
        return ""
    out = ["## Composite scoring distribution", ""]
    composites = ["main", "quick_win", "strategic", "aeo_defensive"]
    for comp in composites:
        scores = sorted([
            k.get("scores", {}).get(comp, {}).get("score", 0)
            for k in keywords
        ])
        if not scores:
            continue
        median = scores[len(scores) // 2]
        p75 = scores[int(len(scores) * 0.75)]
        p90 = scores[int(len(scores) * 0.90)]
        p99 = scores[min(len(scores) - 1, int(len(scores) * 0.99))]
        mean_score = sum(scores) / len(scores)
        out.append(f"### {comp}")
        out.append("")
        out.append(f"- Mean: {mean_score:.1f}")
        out.append(f"- Median: {median:.1f}")
        out.append(f"- P75: {p75:.1f}")
        out.append(f"- P90: {p90:.1f}")
        out.append(f"- P99: {p99:.1f}")
        out.append("")
    return "\n".join(out)


def section_top_opportunities(canonical: Dict[str, Any], top_n: int) -> str:
    keywords = canonical.get("keywords", [])
    out = ["## Top opportunities", ""]

    composites = [
        ("quick_wins", "quick_win", "Quick wins"),
        ("strategic", "strategic", "Strategic priorities"),
        ("aeo_defensive", "aeo_defensive", "Defensive priorities"),
    ]

    for sec_name, comp_key, title in composites:
        sorted_kws = sorted(
            keywords,
            key=lambda k: k.get("scores", {}).get(comp_key, {}).get("score", 0),
            reverse=True,
        )[:top_n]

        if not sorted_kws:
            continue

        out.append(f"### {title}")
        out.append("")
        rows = []
        for kw in sorted_kws:
            score_obj = kw.get("scores", {}).get(comp_key, {})
            metrics = kw.get("metrics", {})
            scopes = kw.get("scopes", {})
            cluster_label = scopes.get("cluster_assignment", {}).get(
                "label", "")
            intent = kw.get("enrichment", {}).get("intent_vector", {}).get(
                "query_type", "")
            rows.append([
                kw.get("keyword_original", kw["keyword"]),
                fmt_int(metrics.get("volume")),
                fmt_int(metrics.get("difficulty")),
                fmt_int(metrics.get("position")),
                intent,
                cluster_label,
                fmt_float(score_obj.get("score"), 1),
                fmt_float(score_obj.get("confidence"), 2),
            ])
        out.append(md_table(
            ["Keyword", "Volume", "Diff.", "Pos.", "Intent",
             "Cluster", "Score", "Conf."],
            rows
        ))
        out.append("")

    return "\n".join(out)


def section_action_distribution(canonical: Dict[str, Any]) -> str:
    keywords = canonical.get("keywords", [])
    if not keywords:
        return ""
    from collections import Counter
    counter = Counter(derive_action_class(k) for k in keywords)
    total = sum(counter.values())
    order = ["create", "update", "restructure", "monitor", "ignore"]
    out = ["## Recommended actions", "",
           "Every keyword carries one action class. The split below shows "
           "where production effort lands before any single page is opened.",
           ""]
    rows = []
    for action in order:
        count = counter.get(action, 0)
        share = count / max(1, total)
        rows.append([action, fmt_int(count), f"{share:.1%}"])
    out.append(md_table(["Action class", "Count", "Share"], rows))
    out.append("")
    return "\n".join(out)


def section_cluster_analysis(canonical: Dict[str, Any], top_n: int = 30
                              ) -> str:
    clusters = canonical.get("clusters", [])
    if not clusters:
        return ""
    sorted_clusters = sorted(
        clusters, key=lambda c: c.get("volume_total", 0), reverse=True
    )[:top_n]
    out = ["## Cluster analysis", "",
           f"Top {len(sorted_clusters)} clusters by total search volume.", ""]
    rows = []
    for c in sorted_clusters:
        rows.append([
            c.get("head", ""),
            c.get("size", 0),
            fmt_int(c.get("volume_total")),
            c.get("dominant_intent", ""),
            fmt_float(c.get("confidence"), 2),
        ])
    out.append(md_table(
        ["Cluster head", "Size", "Total volume", "Dominant intent", "Conf."],
        rows
    ))
    out.append("")
    all_vol = sum(c.get("volume_total", 0) for c in clusters)
    top_vol = sorted_clusters[0].get("volume_total", 0) if sorted_clusters \
        else 0
    if all_vol:
        out.append(
            f"The largest cluster holds {top_vol / all_vol:.0%} of total "
            f"search volume, which shows how concentrated demand is around "
            f"one head term."
        )
        out.append("")
    return "\n".join(out)


def section_gap_analysis(canonical: Dict[str, Any]) -> str:
    gaps = canonical.get("gaps", {})
    out = ["## Gap analysis", ""]

    kw_gap = gaps.get("keyword_gap", {})
    if kw_gap.get("count", 0) > 0:
        out.append("### Keyword gap")
        out.append("")
        out.append(f"Found {kw_gap['count']} keywords where competitors "
                   f"rank but the client domain does not.")
        out.append("")
        if kw_gap.get("samples"):
            out.append("Sample of top gap keywords:")
            out.append("")
            for s in kw_gap["samples"][:10]:
                out.append(f"- {s}")
            out.append("")

    content_gap = gaps.get("content_gap", {})
    if content_gap.get("intents_present"):
        out.append("### Intent presence in corpus")
        out.append("")
        out.append("Intent layers observed in the corpus:")
        out.append("")
        for intent in content_gap["intents_present"]:
            out.append(f"- {intent}")
        out.append("")

    aeo_geo_gap = gaps.get("aeo_geo_gap", {})
    if aeo_geo_gap.get("count", 0) > 0:
        out.append("### AEO/GEO gap")
        out.append("")
        out.append(f"Found {aeo_geo_gap['count']} AIO-eligible keywords "
                   f"where the client does not rank in the top 10.")
        out.append("")
        if aeo_geo_gap.get("samples"):
            out.append("Sample of top AEO/GEO gap keywords:")
            out.append("")
            for s in aeo_geo_gap["samples"][:10]:
                out.append(f"- {s}")
            out.append("")

    return "\n".join(out)


def section_aio_geo_routing(canonical: Dict[str, Any]) -> str:
    keywords = canonical.get("keywords", [])
    if not keywords:
        return ""
    from collections import Counter
    routing_counter = Counter()
    for k in keywords:
        label = k.get("scopes", {}).get("geo_opportunity", {}).get(
            "label", "neither")
        routing_counter[label] += 1

    total = sum(routing_counter.values())
    out = ["## AIO and GEO routing", "",
           "Keywords classified by AI search optimization path:", ""]
    rows = []
    for path in ["dual", "aio_only", "geo_only", "neither"]:
        count = routing_counter.get(path, 0)
        share = count / max(1, total)
        rows.append([path, fmt_int(count), f"{share:.1%}"])
    out.append(md_table(["Routing path", "Count", "Share"], rows))
    out.append("")
    return "\n".join(out)


def section_methodology(canonical: Dict[str, Any]) -> str:
    meta = canonical.get("run_metadata", {})
    params = canonical.get("parameters", {})
    out = ["## Methodology and parameters", ""]
    out.append(f"- Methodology version: "
               f"{meta.get('methodology_version', 'n/a')}")
    out.append(f"- Skill version: {meta.get('skill_version', 'n/a')}")
    out.append("")
    out.append("Key parameters applied in this run:")
    out.append("")
    keys = ["quickwin_volume_min", "quickwin_volume_max",
            "quickwin_difficulty_max", "striking_min", "striking_max",
            "cluster_overlap_min", "aio_eligibility_min",
            "geo_opportunity_min", "volume_reference"]
    rows = [[k, str(params.get(k, "n/a"))] for k in keys]
    out.append(md_table(["Parameter", "Value"], rows))
    out.append("")
    return "\n".join(out)


def build_markdown(canonical: Dict[str, Any], top_n: int) -> str:
    """Compose full Markdown report from canonical state."""
    parts = [
        section_header(),
        section_engagement_context(canonical),
        section_corpus_summary(canonical),
        section_score_distribution(canonical),
        section_top_opportunities(canonical, top_n),
        section_action_distribution(canonical),
        section_cluster_analysis(canonical),
        section_gap_analysis(canonical),
        section_aio_geo_routing(canonical),
        section_methodology(canonical),
    ]
    return "\n".join(p for p in parts if p)


# =====================================================================
# Enriched CSV
# =====================================================================

def csv_columns_full() -> List[str]:
    return [
        "keyword", "keyword_original", "source", "language", "country",
        "volume", "difficulty", "cpc", "position", "serp_features",
        "traffic_potential", "clicks", "impressions", "ctr",
        "intent_query_type", "intent_funnel_stage", "intent_modality",
        "intent_temporal", "cluster_head", "cluster_size",
        "aio_eligibility", "geo_opportunity", "quick_win_flag",
        "striking_distance_flag", "branded_flag", "question_flag",
        "paa_flag", "seasonality_class", "long_tail_flag",
        "score_main", "score_quick_win", "score_strategic",
        "score_aeo_defensive", "confidence_main", "confidence_quick_win",
        "confidence_strategic", "confidence_aeo_defensive",
        "recommended_action_class",
        "source_file", "source_row",
    ]


def csv_columns_minimal() -> List[str]:
    return [
        "keyword", "score_main", "score_quick_win", "score_strategic",
        "score_aeo_defensive", "recommended_action_class",
    ]


def kw_to_csv_row(kw: Dict[str, Any], columns: List[str],
                   clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Map a serialized keyword to a CSV row dict."""
    metrics = kw.get("metrics", {})
    enrich = kw.get("enrichment", {})
    scopes = kw.get("scopes", {})
    scores = kw.get("scores", {})
    intent_vec = enrich.get("intent_vector", {})
    cluster_idx = scopes.get("cluster_assignment", {}).get("cluster_index")
    cluster_size = (clusters[cluster_idx]["size"]
                    if cluster_idx is not None and 0 <= cluster_idx
                    < len(clusters) else 0)

    striking = scopes.get("striking_distance", {}).get("label", "")

    row = {
        "keyword": kw.get("keyword", ""),
        "keyword_original": kw.get("keyword_original", ""),
        "source": kw.get("source", ""),
        "language": kw.get("language", ""),
        "country": kw.get("country", ""),
        "volume": metrics.get("volume", ""),
        "difficulty": metrics.get("difficulty", ""),
        "cpc": metrics.get("cpc", ""),
        "position": metrics.get("position", ""),
        "serp_features": ",".join(metrics.get("serp_features", [])),
        "traffic_potential": metrics.get("traffic_potential", ""),
        "clicks": metrics.get("clicks", ""),
        "impressions": metrics.get("impressions", ""),
        "ctr": metrics.get("ctr", ""),
        "intent_query_type": intent_vec.get("query_type", ""),
        "intent_funnel_stage": intent_vec.get("funnel_stage", ""),
        "intent_modality": intent_vec.get("modality", ""),
        "intent_temporal": intent_vec.get("temporal", ""),
        "cluster_head": scopes.get("cluster_assignment", {}).get("label", ""),
        "cluster_size": cluster_size,
        "aio_eligibility": scopes.get("aio_eligibility", {}).get("label", ""),
        "geo_opportunity": scopes.get("geo_opportunity", {}).get("label", ""),
        "quick_win_flag": "yes" if scopes.get("quick_wins", {}).get(
            "label") == "quick_win" else "",
        "striking_distance_flag": striking if striking != "not_striking"
            else "",
        "branded_flag": "yes" if enrich.get("branded") else "",
        "question_flag": "yes" if enrich.get("question_shape") else "",
        "paa_flag": "yes" if "paa" in metrics.get("serp_features", []) else "",
        "seasonality_class": scopes.get("seasonality", {}).get("label", ""),
        "long_tail_flag": scopes.get("long_tail", {}).get("label", ""),
        "score_main": scores.get("main", {}).get("score", ""),
        "score_quick_win": scores.get("quick_win", {}).get("score", ""),
        "score_strategic": scores.get("strategic", {}).get("score", ""),
        "score_aeo_defensive": scores.get("aeo_defensive", {}).get(
            "score", ""),
        "confidence_main": scores.get("main", {}).get("confidence", ""),
        "confidence_quick_win": scores.get("quick_win", {}).get(
            "confidence", ""),
        "confidence_strategic": scores.get("strategic", {}).get(
            "confidence", ""),
        "confidence_aeo_defensive": scores.get("aeo_defensive", {}).get(
            "confidence", ""),
        "recommended_action_class": derive_action_class(kw),
        "source_file": kw.get("source_file", ""),
        "source_row": kw.get("source_row", ""),
    }
    return {col: row.get(col, "") for col in columns}


def derive_action_class(kw: Dict[str, Any]) -> str:
    """Lightweight action class derivation."""
    scopes = kw.get("scopes", {})
    if scopes.get("quick_wins", {}).get("label") == "quick_win":
        return "create"
    if scopes.get("striking_distance", {}).get("label") in (
            "top_page_climb", "second_page_break"):
        return "update"
    if scopes.get("striking_distance", {}).get("label") == "third_page_lift":
        return "restructure"
    score = kw.get("scores", {}).get("main", {}).get("score", 0)
    if score < 30:
        return "ignore"
    return "monitor"


def write_enriched_csv(canonical: Dict[str, Any], output_path: Path,
                        columns_preset: str = "full",
                        line_endings: str = "crlf") -> None:
    """Write enriched CSV from canonical state."""
    columns = csv_columns_full() if columns_preset == "full" \
        else csv_columns_minimal()
    keywords = canonical.get("keywords", [])
    clusters = canonical.get("clusters", [])

    sorted_kws = sorted(
        keywords,
        key=lambda k: k.get("scores", {}).get("main", {}).get("score", 0),
        reverse=True,
    )

    newline_char = "\r\n" if line_endings == "crlf" else "\n"
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, lineterminator=newline_char,
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for kw in sorted_kws:
            writer.writerow(kw_to_csv_row(kw, columns, clusters))

    logger.info("Enriched CSV written to %s (%d rows, %d columns)",
                output_path, len(sorted_kws), len(columns))


# =====================================================================
# Executive summary
# =====================================================================

def build_executive_summary(canonical: Dict[str, Any]) -> str:
    """Build the one-page executive summary."""
    meta = canonical.get("run_metadata", {})
    summary = canonical.get("corpus_summary", {})
    gaps = canonical.get("gaps", {})
    keywords = canonical.get("keywords", [])
    clusters = canonical.get("clusters", [])

    label = meta.get("label") or "(no label)"
    timestamp = meta.get("timestamp", "")[:10]
    total = summary.get("total_keywords", 0)
    languages = sorted({
        k.get("language", "unknown")
        for k in keywords
    })
    sources = sorted({
        f.get("source", "unknown")
        for f in canonical.get("input_manifest", {}).get("files", [])
    })
    aio_share = summary.get("aio_eligibility_share", 0)
    geo_share = summary.get("geo_opportunity_share", 0)
    quick_wins = sum(
        1 for k in keywords
        if k.get("scopes", {}).get("quick_wins", {}).get("label") == "quick_win"
    )
    striking = sum(
        1 for k in keywords
        if k.get("scopes", {}).get("striking_distance", {}).get("label")
        in ("top_page_climb", "second_page_break", "third_page_lift")
    )
    kw_gap_count = gaps.get("keyword_gap", {}).get("count", 0)
    aeo_gap_count = gaps.get("aeo_geo_gap", {}).get("count", 0)

    confidence_avg = sum(
        k.get("scores", {}).get("main", {}).get("confidence", 0)
        for k in keywords
    ) / max(1, len(keywords))
    if confidence_avg >= 0.75:
        conf_band = "high"
        conf_note = "input completeness and source reliability are good"
    elif confidence_avg >= 0.55:
        conf_band = "mixed"
        conf_note = ("some keywords have partial inputs; sort by confidence "
                     "to separate action targets from research targets")
    else:
        conf_band = "low"
        conf_note = ("the corpus relies heavily on partial inputs; treat "
                     "the recommendations as research priorities")

    dos = summary.get("demand_opportunity_score")

    lines = []
    lines.append("KEYWORD INTELLIGENCE: EXECUTIVE SUMMARY")
    lines.append(f"{label} | {timestamp}")
    lines.append("")
    if dos is not None:
        lines.append(f"Demand Opportunity Score: {dos:.1f} / 100")
        lines.append("")
    lines.append("Scope of analysis")
    lines.append(
        f"Analysed {total:,} keywords across "
        f"{len(languages)} language(s) ({', '.join(languages)}) "
        f"from {len(sources)} source(s) ({', '.join(sources)})."
    )
    lines.append(f"Total clusters formed: {len(clusters)}.")
    lines.append("")

    lines.append("What we found")
    if aio_share:
        lines.append(
            f"- {aio_share:.0%} of the corpus is AIO-eligible (Google AI "
            f"Overviews); {geo_share:.0%} carries GEO opportunity for "
            f"generative engines."
        )
    if kw_gap_count:
        lines.append(
            f"- {kw_gap_count:,} keywords sit in a content gap "
            f"(competitors rank, client does not)."
        )
    if quick_wins:
        lines.append(
            f"- {quick_wins:,} keywords qualify as quick wins under "
            f"current thresholds."
        )
    if striking:
        lines.append(
            f"- {striking:,} keywords are in striking distance "
            f"(positions 4-20 for the client's domain)."
        )
    if aeo_gap_count:
        lines.append(
            f"- {aeo_gap_count:,} AIO-eligible keywords show no client "
            f"presence in the top 10."
        )
    from collections import Counter
    action_counts = Counter(derive_action_class(k) for k in keywords)
    create_n = action_counts.get("create", 0)
    update_n = action_counts.get("update", 0)
    restructure_n = action_counts.get("restructure", 0)
    if create_n or update_n or restructure_n:
        lines.append(
            f"- Action split: {create_n:,} to create, {update_n:,} to "
            f"update, {restructure_n:,} to restructure; the rest sit in "
            f"monitor or ignore."
        )
    lines.append("")

    lines.append("What we recommend")
    top_clusters = sorted(
        clusters, key=lambda c: c.get("volume_total", 0), reverse=True
    )[:3]
    top_cluster_names = [c.get("head", "") for c in top_clusters
                         if c.get("head")]
    qw_keywords = sorted(
        [k for k in keywords
         if k.get("scopes", {}).get("quick_wins", {}).get("label")
         == "quick_win"],
        key=lambda k: k.get("scores", {}).get("quick_win", {}).get("score", 0),
        reverse=True,
    )[:5]
    qw_names = [k.get("keyword_original", k.get("keyword", ""))
                for k in qw_keywords]
    if top_cluster_names:
        lines.append(
            f"- Start with these clusters by demand: "
            f"{', '.join(top_cluster_names)}."
        )
    if qw_names:
        lines.append(
            f"- First quick wins to commission: {', '.join(qw_names)}."
        )
    if quick_wins:
        lines.append(
            f"- Plan a content sprint targeting the top {min(20, quick_wins)} "
            f"quick wins. They are reachable inside one quarter."
        )
    if striking:
        lines.append(
            "- Refresh and tighten the top 10 striking-distance pages "
            "for top-3 lift before pursuing brand-new content."
        )
    if aeo_gap_count or aio_share > 0.10:
        lines.append(
            "- Address the AEO/GEO gap: passage extraction structure, "
            "schema markup, llms.txt publication, and AI crawler access."
        )
    if kw_gap_count:
        lines.append(
            "- Plan cluster-level coverage for the keyword gap. Treat as "
            "architecture work, not as scattered single pages."
        )
    lines.append("")

    lines.append("What we did not analyze")
    lines.append("- Live SERP data (run is offline against a CSV snapshot).")
    lines.append("- Backlink profile (out of scope for this skill).")
    lines.append("- Page-level technical SEO (out of scope; requires "
                 "site crawl).")
    lines.append("")
    lines.append(f"Methodology version: "
                 f"{meta.get('methodology_version', 'n/a')}")
    lines.append(f"Confidence note: overall confidence is {conf_band}; "
                 f"{conf_note}.")

    if len(lines) > EXEC_SUMMARY_LINE_CAP:
        keep_head = lines[:18]
        keep_tail = lines[-10:]
        lines = keep_head + ["", "[Some recommendations omitted to fit "
                              "the one-page cap; full list in report.md]",
                              ""] + keep_tail

    return "\n".join(lines) + "\n"


# =====================================================================
# Content briefs
# =====================================================================

def _kw_volume(kw: Dict[str, Any]) -> int:
    try:
        return int(kw.get("metrics", {}).get("volume") or 0)
    except (TypeError, ValueError):
        return 0


def build_content_briefs(canonical: Dict[str, Any],
                         top_n: int = BRIEFS_TOP_N_DEFAULT) -> str:
    """Per-cluster content brief skeletons, deterministic from canonical state.

    Each brief turns a cluster into the start of an editorial plan: primary
    keyword, secondary keywords, questions to answer, dominant intent,
    suggested format, and recommended action. The skeleton stays reproducible;
    Claude can expand any brief into a full writing brief on request.
    """
    keywords = canonical.get("keywords", [])
    clusters = canonical.get("clusters", [])
    if not clusters:
        return "# Content briefs\n\nNo clusters formed in this run.\n"
    sorted_clusters = sorted(
        clusters, key=lambda c: c.get("volume_total", 0), reverse=True
    )[:top_n]

    from collections import Counter
    out = ["# Content briefs", "",
           f"Top {len(sorted_clusters)} clusters by total search volume, each "
           f"turned into the start of an editorial plan. Expand any brief into "
           f"a full writing brief as needed.", ""]

    for c in sorted_clusters:
        members = [keywords[i] for i in c.get("members", [])
                   if 0 <= i < len(keywords)]
        if not members:
            continue
        members_by_vol = sorted(members, key=_kw_volume, reverse=True)
        primary = members_by_vol[0]
        primary_kw = primary.get("keyword_original", primary.get("keyword", ""))

        # The corpus holds the same keyword once per source, so dedup by the
        # normalized string before listing secondaries and questions.
        seen = {(primary.get("keyword") or "").lower()}
        secondaries = []
        for m in members_by_vol[1:]:
            norm = (m.get("keyword") or "").lower()
            if norm in seen:
                continue
            seen.add(norm)
            secondaries.append(m.get("keyword_original", m.get("keyword", "")))
            if len(secondaries) >= 5:
                break

        q_seen = set()
        questions = []
        for m in members:
            if not m.get("enrichment", {}).get("question_shape"):
                continue
            norm = (m.get("keyword") or "").lower()
            if norm in q_seen:
                continue
            q_seen.add(norm)
            questions.append(m.get("keyword_original", m.get("keyword", "")))
            if len(questions) >= 6:
                break
        intent = c.get("dominant_intent", "")
        fmt = FORMAT_BY_INTENT.get(intent, "article")
        action_counts = Counter(derive_action_class(m) for m in members)
        action = (action_counts.most_common(1)[0][0]
                  if action_counts else "monitor")

        out.append(f"## {c.get('head', primary_kw)}")
        out.append("")
        out.append(f"- Cluster size: {c.get('size', len(members))} keywords, "
                   f"{fmt_int(c.get('volume_total'))} total monthly volume")
        out.append(f"- Dominant intent: {intent}")
        out.append(f"- Suggested format: {fmt}")
        out.append(f"- Recommended action: {action}")
        out.append(f"- Primary keyword: {primary_kw}")
        if secondaries:
            out.append(f"- Secondary keywords: {', '.join(secondaries)}")
        if questions:
            out.append("- Questions to answer: " + "; ".join(questions))
        else:
            out.append("- Questions to answer: none flagged in this corpus")
        out.append("")

    return "\n".join(out)


# =====================================================================
# Top-level orchestration
# =====================================================================

def generate_artifacts(canonical: Dict[str, Any], output_dir: Path,
                       args: argparse.Namespace) -> None:
    """Write Markdown report, enriched CSV, and TXT summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    top_n = getattr(args, "top_n", REPORT_TOP_N_DEFAULT)
    csv_preset = getattr(args, "csv_columns", "full")
    line_endings = getattr(args, "csv_line_endings", "crlf")

    md_text = build_markdown(canonical, top_n)
    md_path = output_dir / "report.md"
    md_path.write_text(md_text, encoding="utf-8")
    logger.info("Markdown report written to %s", md_path)

    csv_path = output_dir / "keywords_enriched.csv"
    write_enriched_csv(canonical, csv_path, csv_preset, line_endings)

    summary_text = build_executive_summary(canonical)
    summary_path = output_dir / "executive_summary.txt"
    summary_path.write_text(summary_text, encoding="utf-8")
    logger.info("Executive summary written to %s", summary_path)

    briefs_text = build_content_briefs(canonical)
    briefs_path = output_dir / "content_briefs.md"
    briefs_path.write_text(briefs_text, encoding="utf-8")
    logger.info("Content briefs written to %s", briefs_path)


def load_canonical(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Canonical JSON not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    try:
        json_path = Path(args.input)
        canonical = load_canonical(json_path)
        output_dir = Path(args.output_dir) if args.output_dir \
            else json_path.parent
        generate_artifacts(canonical, output_dir, args)
        print(f"Artifacts written to {output_dir}")
        return 0
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 2
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return 3
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
