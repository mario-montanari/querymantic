#!/usr/bin/env python3
"""
compare.py - Run-over-run comparison for keyword intelligence.

Reads two canonical JSON states produced by analyze.py (an earlier baseline
and a later run) and reports what changed between them: the Demand Opportunity
Score and corpus shares, quick wins captured or newly surfaced, composite score
movement, position movement, gaps opened or closed, and keywords added or
dropped.

The skill is deterministic: the same inputs produce the same scoring. That
property is what makes a run-over-run delta meaningful. When two runs share the
same methodology version, every difference reported here reflects a change in
the data, not noise in the method.

Usage:
    python compare.py \\
        --baseline output/q1/analysis.json \\
        --current  output/q2/analysis.json \\
        --output-dir output/q1_vs_q2/ \\
        --format both

For the full parameter list, run: python compare.py --help

Methodology version: 1.0.0
Skill version: 1.0.0
"""

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("keyword_intelligence.compare")

DEFAULT_TOP_N = 15

# Composite scores carried by every keyword record. Order is the reading order
# used in the report: general performance, then the three engagement lenses.
COMPOSITES = ("main", "quick_win", "strategic", "aeo_defensive")

# Striking-distance labels that mean "ranking but not yet at the top". A quick
# win that lands in the top three has left this band: that is a capture.
STRIKING_LABELS = ("top_page_climb", "second_page_break", "third_page_lift")

# AIO eligibility labels that put a keyword on the AI-search surface.
AIO_PRESENT_LABELS = ("confirmed", "eligible")

# A position at or above this rank counts as captured: the keyword broke into
# the top of the SERP, the outcome a quick win is chasing.
CAPTURE_POSITION_MAX = 3


# =====================================================================
# CLI
# =====================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare",
        description="Compare two analysis.json states produced by analyze.py "
                    "and report run-over-run movement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Quarter-over-quarter comparison, both artifacts:
    python compare.py --baseline q1/analysis.json --current q2/analysis.json \\
        --output-dir q1_vs_q2/

  JSON only, more rows in the movement tables:
    python compare.py --baseline a.json --current b.json \\
        --format json --top-n 30

  Multilingual corpus (disambiguate the same string across languages):
    python compare.py --baseline a.json --current b.json --match-key keyword-lang
""",
    )
    parser.add_argument("--baseline", required=True,
                        help="Path to the earlier analysis.json")
    parser.add_argument("--current", required=True,
                        help="Path to the later analysis.json")
    parser.add_argument("--output-dir",
                        help="Output directory for comparison artifacts "
                             "(defaults to the current run's parent directory)")
    parser.add_argument("--format", choices=["text", "json", "both"],
                        default="both",
                        help="Which artifacts to write: comparison.md (text), "
                             "comparison.json (json), or both")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                        help="Number of rows in the movement tables")
    parser.add_argument("--match-key", choices=["keyword", "keyword-lang"],
                        default="keyword",
                        help="How to match a keyword across the two runs. "
                             "'keyword' matches on the normalized string; "
                             "'keyword-lang' adds the detected language to "
                             "disambiguate multilingual corpora")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


# =====================================================================
# Loading and indexing
# =====================================================================

def load_canonical(path: Path) -> Dict[str, Any]:
    """Load and shallow-validate a canonical analysis.json."""
    if not path.exists():
        raise FileNotFoundError(f"Canonical JSON not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "keywords" not in data \
            or "corpus_summary" not in data:
        raise ValueError(
            f"{path} is not a keyword-intelligence analysis.json "
            "(missing 'keywords' or 'corpus_summary')")
    return data


def key_for(record: Dict[str, Any], match_key: str) -> str:
    """Build the matching key for a keyword record."""
    keyword = record.get("keyword", "")
    if match_key == "keyword-lang":
        lang = record.get("language") or "unknown"
        # ␟ is the visible Unit Separator glyph; it cannot occur inside a
        # keyword, so it is a safe field delimiter for the composite key.
        return f"{keyword}␟{lang}"
    return keyword


def _volume(record: Dict[str, Any]) -> int:
    vol = record.get("metrics", {}).get("volume")
    return vol if isinstance(vol, (int, float)) else 0


def _more_representative(candidate: Dict[str, Any],
                         incumbent: Dict[str, Any]) -> bool:
    """Decide whether candidate should represent a key over the incumbent.

    The same keyword often appears from several sources (Semrush, Ahrefs, GSC).
    To compare like with like, each key keeps one representative record. The
    rule is deterministic: higher volume wins; ties break on source name, then
    source row. Volume is stable within a given export, so the representative
    does not flip between runs unless the underlying data changed.
    """
    cand_vol, inc_vol = _volume(candidate), _volume(incumbent)
    if cand_vol != inc_vol:
        return cand_vol > inc_vol
    cand_src = candidate.get("source", "")
    inc_src = incumbent.get("source", "")
    if cand_src != inc_src:
        return cand_src < inc_src
    return (candidate.get("source_row", 0) or 0) < \
           (incumbent.get("source_row", 0) or 0)


def index_keywords(canonical: Dict[str, Any], match_key: str
                   ) -> Tuple[Dict[str, Dict[str, Any]], int]:
    """Index keyword records by match key, keeping one representative each.

    Returns the index and the number of duplicate records collapsed.
    """
    index: Dict[str, Dict[str, Any]] = {}
    collisions = 0
    for record in canonical.get("keywords", []):
        key = key_for(record, match_key)
        if key not in index:
            index[key] = record
        else:
            collisions += 1
            if _more_representative(record, index[key]):
                index[key] = record
    return index, collisions


# =====================================================================
# Field accessors
# =====================================================================

def score_of(record: Dict[str, Any], composite: str) -> Optional[float]:
    val = record.get("scores", {}).get(composite, {}).get("score")
    return float(val) if isinstance(val, (int, float)) else None


def confidence_of(record: Dict[str, Any], composite: str) -> Optional[float]:
    val = record.get("scores", {}).get(composite, {}).get("confidence")
    return float(val) if isinstance(val, (int, float)) else None


def position_of(record: Dict[str, Any]) -> Optional[float]:
    val = record.get("metrics", {}).get("position")
    return float(val) if isinstance(val, (int, float)) else None


def scope_label(record: Dict[str, Any], scope: str) -> Optional[str]:
    return record.get("scopes", {}).get(scope, {}).get("label")


def is_quick_win(record: Dict[str, Any]) -> bool:
    return scope_label(record, "quick_wins") == "quick_win"


def is_aio_present(record: Dict[str, Any]) -> bool:
    return scope_label(record, "aio_eligibility") in AIO_PRESENT_LABELS


# =====================================================================
# Comparison stages
# =====================================================================

def compare_corpus(baseline: Dict[str, Any], current: Dict[str, Any]
                   ) -> Dict[str, Any]:
    """Corpus-level headline deltas."""
    b = baseline.get("corpus_summary", {})
    c = current.get("corpus_summary", {})

    def delta(field: str) -> Dict[str, Any]:
        bv = b.get(field)
        cv = c.get(field)
        d = None
        if isinstance(bv, (int, float)) and isinstance(cv, (int, float)):
            d = round(cv - bv, 3)
        return {"baseline": bv, "current": cv, "delta": d}

    intents = sorted(set(b.get("by_intent", {})) | set(c.get("by_intent", {})))
    intent_shift = {
        intent: {
            "baseline": b.get("by_intent", {}).get(intent, 0),
            "current": c.get("by_intent", {}).get(intent, 0),
            "delta": c.get("by_intent", {}).get(intent, 0)
                     - b.get("by_intent", {}).get(intent, 0),
        }
        for intent in intents
    }

    return {
        "demand_opportunity_score": delta("demand_opportunity_score"),
        "total_keywords": delta("total_keywords"),
        "aio_eligibility_share": delta("aio_eligibility_share"),
        "geo_opportunity_share": delta("geo_opportunity_share"),
        "intent_shift": intent_shift,
    }


def _classify_resolution(base_rec: Dict[str, Any],
                         cur_rec: Optional[Dict[str, Any]]) -> str:
    """Classify why a baseline quick win is no longer a quick win.

    captured     : now ranks in the top three (the win was realized).
    still_climbing: position improved but not yet top three.
    regressed    : position got worse.
    reclassified : position not comparable; the label changed for another
                   reason (volume, difficulty, or threshold change).
    left_corpus  : the keyword is absent from the current run.
    """
    if cur_rec is None:
        return "left_corpus"
    base_pos = position_of(base_rec)
    cur_pos = position_of(cur_rec)
    if cur_pos is not None and cur_pos <= CAPTURE_POSITION_MAX:
        return "captured"
    if base_pos is not None and cur_pos is not None:
        if cur_pos < base_pos:
            return "still_climbing"
        if cur_pos > base_pos:
            return "regressed"
    return "reclassified"


def compare_quick_wins(base_idx: Dict[str, Dict[str, Any]],
                       cur_idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Quick-win movement between runs."""
    newly: List[str] = []
    still: List[str] = []
    resolved: Dict[str, List[str]] = {
        "captured": [], "still_climbing": [], "regressed": [],
        "reclassified": [], "left_corpus": [],
    }

    for key, cur_rec in cur_idx.items():
        if is_quick_win(cur_rec) and not (
                key in base_idx and is_quick_win(base_idx[key])):
            newly.append(cur_rec.get("keyword", key))

    for key, base_rec in base_idx.items():
        if not is_quick_win(base_rec):
            continue
        cur_rec = cur_idx.get(key)
        if cur_rec is not None and is_quick_win(cur_rec):
            still.append(base_rec.get("keyword", key))
        else:
            reason = _classify_resolution(base_rec, cur_rec)
            resolved[reason].append(base_rec.get("keyword", key))

    return {
        "newly_quick_win": {"count": len(newly), "keywords": sorted(newly)},
        "still_quick_win": {"count": len(still), "keywords": sorted(still)},
        "resolved": {
            reason: {"count": len(kws), "keywords": sorted(kws)}
            for reason, kws in resolved.items()
        },
    }


def compare_scores(base_idx: Dict[str, Dict[str, Any]],
                   cur_idx: Dict[str, Dict[str, Any]],
                   top_n: int) -> Dict[str, Any]:
    """Composite score movement for keywords present in both runs."""
    shared = [k for k in cur_idx if k in base_idx]

    per_composite: Dict[str, Any] = {}
    for composite in COMPOSITES:
        deltas: List[float] = []
        for key in shared:
            bs = score_of(base_idx[key], composite)
            cs = score_of(cur_idx[key], composite)
            if bs is not None and cs is not None:
                deltas.append(cs - bs)
        mean_delta = round(sum(deltas) / len(deltas), 2) if deltas else None
        per_composite[composite] = {
            "mean_delta": mean_delta,
            "keywords_compared": len(deltas),
        }

    # Per-keyword main-composite movement, the default ranking lens.
    movements: List[Dict[str, Any]] = []
    for key in shared:
        bs = score_of(base_idx[key], "main")
        cs = score_of(cur_idx[key], "main")
        if bs is None or cs is None:
            continue
        movements.append({
            "keyword": cur_idx[key].get("keyword", key),
            "baseline": bs,
            "current": cs,
            "delta": round(cs - bs, 1),
        })
    # Secondary sort on keyword keeps the order reproducible regardless of how
    # the records happened to be ordered in the input JSON.
    risers = sorted(movements, key=lambda m: (-m["delta"], m["keyword"]))
    fallers = sorted(movements, key=lambda m: (m["delta"], m["keyword"]))

    # Mean main-composite confidence movement.
    conf_deltas: List[float] = []
    for key in shared:
        bc = confidence_of(base_idx[key], "main")
        cc = confidence_of(cur_idx[key], "main")
        if bc is not None and cc is not None:
            conf_deltas.append(cc - bc)
    mean_conf_delta = round(sum(conf_deltas) / len(conf_deltas), 3) \
        if conf_deltas else None

    return {
        "keywords_in_both": len(shared),
        "mean_delta_by_composite": per_composite,
        "mean_main_confidence_delta": mean_conf_delta,
        "top_risers": [m for m in risers if m["delta"] > 0][:top_n],
        "top_fallers": [m for m in fallers if m["delta"] < 0][:top_n],
    }


def compare_positions(base_idx: Dict[str, Dict[str, Any]],
                      cur_idx: Dict[str, Dict[str, Any]],
                      top_n: int) -> Dict[str, Any]:
    """Position movement for keywords with a position in both runs."""
    moves: List[Dict[str, Any]] = []
    for key, cur_rec in cur_idx.items():
        base_rec = base_idx.get(key)
        if base_rec is None:
            continue
        bp = position_of(base_rec)
        cp = position_of(cur_rec)
        if bp is None or cp is None:
            continue
        # Positive improvement means the rank number went down (climbed up).
        moves.append({
            "keyword": cur_rec.get("keyword", key),
            "baseline_position": round(bp, 1),
            "current_position": round(cp, 1),
            "improvement": round(bp - cp, 1),
        })
    climbers = [m for m in sorted(
        moves, key=lambda m: (-m["improvement"], m["keyword"]))
        if m["improvement"] > 0]
    decliners = [m for m in sorted(
        moves, key=lambda m: (m["improvement"], m["keyword"]))
        if m["improvement"] < 0]
    return {
        "keywords_with_position_in_both": len(moves),
        "top_climbers": climbers[:top_n],
        "top_decliners": decliners[:top_n],
    }


def _gap_samples(canonical: Dict[str, Any], gap: str) -> List[str]:
    return list(canonical.get("gaps", {}).get(gap, {}).get("samples", []))


def _gap_count(canonical: Dict[str, Any], gap: str) -> Optional[int]:
    return canonical.get("gaps", {}).get(gap, {}).get("count")


def compare_gaps(baseline: Dict[str, Any], current: Dict[str, Any]
                 ) -> Dict[str, Any]:
    """Gaps opened and closed between runs.

    Gap sample lists are capped by analyze.py, so opened/closed lists are drawn
    from the samples while counts come from the full tally. When a gap count is
    larger than its sample list, the lists are partial and flagged as such.
    """
    result: Dict[str, Any] = {}
    for gap in ("keyword_gap", "aeo_geo_gap"):
        base_samples = set(_gap_samples(baseline, gap))
        cur_samples = set(_gap_samples(current, gap))
        base_count = _gap_count(baseline, gap)
        cur_count = _gap_count(current, gap)
        count_delta = None
        if isinstance(base_count, int) and isinstance(cur_count, int):
            count_delta = cur_count - base_count
        result[gap] = {
            "baseline_count": base_count,
            "current_count": cur_count,
            "count_delta": count_delta,
            "closed_samples": sorted(base_samples - cur_samples),
            "opened_samples": sorted(cur_samples - base_samples),
            "samples_partial": bool(
                (isinstance(base_count, int) and base_count > len(base_samples))
                or (isinstance(cur_count, int)
                    and cur_count > len(cur_samples))),
        }

    base_intents = set(
        baseline.get("gaps", {}).get("content_gap", {}).get(
            "intents_present", []))
    cur_intents = set(
        current.get("gaps", {}).get("content_gap", {}).get(
            "intents_present", []))
    result["content_gap_intents"] = {
        "added": sorted(cur_intents - base_intents),
        "removed": sorted(base_intents - cur_intents),
        "present_now": sorted(cur_intents),
    }
    return result


def compare_membership(base_idx: Dict[str, Dict[str, Any]],
                       cur_idx: Dict[str, Dict[str, Any]],
                       top_n: int) -> Dict[str, Any]:
    """Keywords added to and dropped from the corpus."""
    added_keys = [k for k in cur_idx if k not in base_idx]
    dropped_keys = [k for k in base_idx if k not in cur_idx]
    added = sorted(cur_idx[k].get("keyword", k) for k in added_keys)
    dropped = sorted(base_idx[k].get("keyword", k) for k in dropped_keys)
    return {
        "added": {"count": len(added), "samples": added[:top_n]},
        "dropped": {"count": len(dropped), "samples": dropped[:top_n]},
    }


# =====================================================================
# Assembly
# =====================================================================

def _run_descriptor(canonical: Dict[str, Any], path: Path,
                     collisions: int) -> Dict[str, Any]:
    meta = canonical.get("run_metadata", {})
    return {
        "path": str(path),
        "label": meta.get("label") or None,
        "timestamp": meta.get("timestamp"),
        "methodology_version": meta.get("methodology_version"),
        "skill_version": meta.get("skill_version"),
        "total_keywords": canonical.get("corpus_summary", {}).get(
            "total_keywords"),
        "duplicate_records_collapsed": collisions,
    }


def build_comparison(baseline: Dict[str, Any], current: Dict[str, Any],
                     baseline_path: Path, current_path: Path,
                     args: argparse.Namespace) -> Dict[str, Any]:
    """Assemble the full comparison structure."""
    base_idx, base_collisions = index_keywords(baseline, args.match_key)
    cur_idx, cur_collisions = index_keywords(current, args.match_key)

    base_mv = baseline.get("run_metadata", {}).get("methodology_version")
    cur_mv = current.get("run_metadata", {}).get("methodology_version")
    version_warning = None
    if base_mv != cur_mv:
        version_warning = (
            f"Methodology version differs (baseline {base_mv}, current "
            f"{cur_mv}). Scores are computed under different methods and are "
            "not directly comparable. Re-run the baseline under the current "
            "version before trusting the score deltas.")

    return {
        "compare_metadata": {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "match_key": args.match_key,
            "top_n": args.top_n,
            "version_warning": version_warning,
            "baseline": _run_descriptor(baseline, baseline_path,
                                        base_collisions),
            "current": _run_descriptor(current, current_path, cur_collisions),
        },
        "corpus": compare_corpus(baseline, current),
        "quick_wins": compare_quick_wins(base_idx, cur_idx),
        "scores": compare_scores(base_idx, cur_idx, args.top_n),
        "positions": compare_positions(base_idx, cur_idx, args.top_n),
        "gaps": compare_gaps(baseline, current),
        "membership": compare_membership(base_idx, cur_idx, args.top_n),
    }


# =====================================================================
# Rendering
# =====================================================================

def _fmt_delta(value: Optional[float], suffix: str = "") -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value}{suffix}"


def render_markdown(comparison: Dict[str, Any]) -> str:
    meta = comparison["compare_metadata"]
    base = meta["baseline"]
    cur = meta["current"]
    lines: List[str] = []

    lines.append("# Keyword intelligence: run-over-run comparison")
    lines.append("")
    base_label = base["label"] or Path(base["path"]).parent.name
    cur_label = cur["label"] or Path(cur["path"]).parent.name
    lines.append(f"- Baseline: `{base_label}` ({base['total_keywords']} "
                 f"keywords, {base['timestamp']})")
    lines.append(f"- Current: `{cur_label}` ({cur['total_keywords']} "
                 f"keywords, {cur['timestamp']})")
    lines.append(f"- Match key: `{meta['match_key']}`")
    lines.append("")

    if meta["version_warning"]:
        lines.append(f"> Warning: {meta['version_warning']}")
        lines.append("")

    # Headline
    corpus = comparison["corpus"]
    dos = corpus["demand_opportunity_score"]
    lines.append("## Headline")
    lines.append("")
    lines.append(f"Demand Opportunity Score: {dos['baseline']} -> "
                 f"{dos['current']} ({_fmt_delta(dos['delta'])}).")
    aio = corpus["aio_eligibility_share"]
    geo = corpus["geo_opportunity_share"]
    lines.append(f"AIO eligibility share: {aio['baseline']} -> "
                 f"{aio['current']} ({_fmt_delta(aio['delta'])}). "
                 f"GEO opportunity share: {geo['baseline']} -> "
                 f"{geo['current']} ({_fmt_delta(geo['delta'])}).")
    tk = corpus["total_keywords"]
    lines.append(f"Corpus size: {tk['baseline']} -> {tk['current']} "
                 f"({_fmt_delta(tk['delta'])}).")
    lines.append("")

    # Quick wins
    qw = comparison["quick_wins"]
    resolved = qw["resolved"]
    lines.append("## Quick wins")
    lines.append("")
    lines.append(f"- Captured (now top {CAPTURE_POSITION_MAX}): "
                 f"{resolved['captured']['count']}")
    lines.append(f"- Still climbing: {resolved['still_climbing']['count']}")
    lines.append(f"- Still open (quick win in both runs): "
                 f"{qw['still_quick_win']['count']}")
    lines.append(f"- Newly surfaced: {qw['newly_quick_win']['count']}")
    lines.append(f"- Regressed: {resolved['regressed']['count']}  |  "
                 f"Reclassified: {resolved['reclassified']['count']}  |  "
                 f"Left corpus: {resolved['left_corpus']['count']}")
    if resolved["captured"]["keywords"]:
        lines.append("")
        lines.append("Captured this run:")
        for kw in resolved["captured"]["keywords"]:
            lines.append(f"  - {kw}")
    if qw["newly_quick_win"]["keywords"]:
        lines.append("")
        lines.append("Newly surfaced quick wins:")
        for kw in qw["newly_quick_win"]["keywords"]:
            lines.append(f"  - {kw}")
    lines.append("")

    # Score movement
    scores = comparison["scores"]
    lines.append("## Score movement")
    lines.append("")
    lines.append(f"Keywords present in both runs: {scores['keywords_in_both']}. "
                 f"Mean main-composite confidence delta: "
                 f"{_fmt_delta(scores['mean_main_confidence_delta'])}.")
    lines.append("")
    lines.append("Mean composite movement:")
    lines.append("")
    lines.append("| Composite | Mean delta | Keywords compared |")
    lines.append("|---|---|---|")
    for composite in COMPOSITES:
        entry = scores["mean_delta_by_composite"][composite]
        lines.append(f"| {composite} | {_fmt_delta(entry['mean_delta'])} | "
                     f"{entry['keywords_compared']} |")
    lines.append("")
    if scores["top_risers"]:
        lines.append("Top main-composite risers:")
        lines.append("")
        lines.append("| Keyword | Baseline | Current | Delta |")
        lines.append("|---|---|---|---|")
        for m in scores["top_risers"]:
            lines.append(f"| {m['keyword']} | {m['baseline']} | "
                         f"{m['current']} | {_fmt_delta(m['delta'])} |")
        lines.append("")
    if scores["top_fallers"]:
        lines.append("Top main-composite fallers:")
        lines.append("")
        lines.append("| Keyword | Baseline | Current | Delta |")
        lines.append("|---|---|---|---|")
        for m in scores["top_fallers"]:
            lines.append(f"| {m['keyword']} | {m['baseline']} | "
                         f"{m['current']} | {_fmt_delta(m['delta'])} |")
        lines.append("")

    # Position movement
    pos = comparison["positions"]
    lines.append("## Position movement")
    lines.append("")
    lines.append("Keywords with a position in both runs: "
                 f"{pos['keywords_with_position_in_both']}.")
    lines.append("")
    if pos["top_climbers"]:
        lines.append("Top climbers (rank improved):")
        lines.append("")
        lines.append("| Keyword | Baseline | Current | Ranks gained |")
        lines.append("|---|---|---|---|")
        for m in pos["top_climbers"]:
            lines.append(f"| {m['keyword']} | {m['baseline_position']} | "
                         f"{m['current_position']} | "
                         f"{_fmt_delta(m['improvement'])} |")
        lines.append("")
    if pos["top_decliners"]:
        lines.append("Top decliners (rank worsened):")
        lines.append("")
        lines.append("| Keyword | Baseline | Current | Ranks lost |")
        lines.append("|---|---|---|---|")
        for m in pos["top_decliners"]:
            lines.append(f"| {m['keyword']} | {m['baseline_position']} | "
                         f"{m['current_position']} | "
                         f"{_fmt_delta(m['improvement'])} |")
        lines.append("")

    # Gaps
    gaps = comparison["gaps"]
    lines.append("## Gaps opened and closed")
    lines.append("")
    for gap, title in (("keyword_gap", "Keyword gap"),
                       ("aeo_geo_gap", "AEO/GEO gap")):
        g = gaps[gap]
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"Count: {g['baseline_count']} -> {g['current_count']} "
                     f"({_fmt_delta(g['count_delta'])}).")
        if g["samples_partial"]:
            # analyze.py caps gap sample lists, so a set difference on the
            # capped samples would invent spurious opened/closed entries. Show
            # only the count delta, which is computed from the full tally.
            lines.append("Per-item breakdown unavailable: analyze.py caps gap "
                         "samples and at least one run exceeds the cap. The "
                         "count delta is reliable; the item list is not.")
        else:
            if g["closed_samples"]:
                lines.append(f"Closed: {', '.join(g['closed_samples'])}.")
            if g["opened_samples"]:
                lines.append(f"Opened: {', '.join(g['opened_samples'])}.")
        lines.append("")
    cgi = gaps["content_gap_intents"]
    lines.append("### Content-gap intent layers")
    lines.append("")
    lines.append(f"Added: {', '.join(cgi['added']) or 'none'}. "
                 f"Removed: {', '.join(cgi['removed']) or 'none'}.")
    lines.append("")

    # Membership
    mem = comparison["membership"]
    lines.append("## Corpus membership")
    lines.append("")
    lines.append(f"Added: {mem['added']['count']}. "
                 f"Dropped: {mem['dropped']['count']}.")
    if mem["added"]["samples"]:
        lines.append(f"Added (sample): {', '.join(mem['added']['samples'])}.")
    if mem["dropped"]["samples"]:
        lines.append(f"Dropped (sample): "
                     f"{', '.join(mem['dropped']['samples'])}.")
    lines.append("")

    return "\n".join(lines) + "\n"


def render_stdout_summary(comparison: Dict[str, Any]) -> str:
    """One-screen summary printed after a run."""
    corpus = comparison["corpus"]
    dos = corpus["demand_opportunity_score"]
    qw = comparison["quick_wins"]
    gaps = comparison["gaps"]
    lines = [
        f"Demand Opportunity Score: {dos['baseline']} -> {dos['current']} "
        f"({_fmt_delta(dos['delta'])})",
        f"Quick wins captured: {qw['resolved']['captured']['count']}  |  "
        f"newly surfaced: {qw['newly_quick_win']['count']}  |  "
        f"still open: {qw['still_quick_win']['count']}",
        f"Keyword gap: {_fmt_delta(gaps['keyword_gap']['count_delta'])}  |  "
        f"AEO/GEO gap: {_fmt_delta(gaps['aeo_geo_gap']['count_delta'])}",
    ]
    if comparison["compare_metadata"]["version_warning"]:
        lines.insert(0, "WARNING: methodology versions differ; deltas suspect.")
    return "\n".join(lines)


# =====================================================================
# Output
# =====================================================================

def write_artifacts(comparison: Dict[str, Any], output_dir: Path,
                    fmt: str) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    if fmt in ("json", "both"):
        json_path = output_dir / "comparison.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        written.append(json_path)
        logger.info("Comparison JSON written to %s", json_path)
    if fmt in ("text", "both"):
        md_path = output_dir / "comparison.md"
        md_path.write_text(render_markdown(comparison), encoding="utf-8")
        written.append(md_path)
        logger.info("Comparison Markdown written to %s", md_path)
    return written


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        baseline_path = Path(args.baseline)
        current_path = Path(args.current)
        baseline = load_canonical(baseline_path)
        current = load_canonical(current_path)

        comparison = build_comparison(baseline, current, baseline_path,
                                      current_path, args)

        output_dir = Path(args.output_dir) if args.output_dir \
            else current_path.parent
        written = write_artifacts(comparison, output_dir, args.format)

        print(render_stdout_summary(comparison))
        print("")
        print(f"Comparison written to {output_dir} "
              f"({', '.join(p.name for p in written)})")
        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 2
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return 3
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
