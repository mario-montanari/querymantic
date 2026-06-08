#!/usr/bin/env python3
"""
audit.py - Pre-flight validation and corpus sanity checks.

Runs structural and content validation on CSV inputs before they enter
the analyze.py pipeline. Produces an audit report flagging issues that
would cause the pipeline to fail or produce misleading output. Useful
as a dry-run before committing to a full analysis on a large corpus.

Usage:
    python audit.py --inputs file1.csv file2.csv
    python audit.py --inputs input/ --client-domain example.com
    python audit.py --inputs input/ --json > audit_report.json

Exit codes:
    0 - audit passed, no critical issues
    1 - critical issues found (analyze.py would fail)
    2 - warnings found (analyze.py would run but with risk)
    3 - configuration error (paths, parameters)

Methodology version: 1.0.0
Skill version: 1.0.0
"""

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("keyword_intelligence.audit")

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"


# =====================================================================
# Audit findings dataclass
# =====================================================================

@dataclass
class Finding:
    """A single audit finding."""
    severity: str
    category: str
    message: str
    file_path: Optional[str] = None
    row_number: Optional[int] = None
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AuditReport:
    """Aggregated audit results across all inputs."""
    timestamp: str
    inputs_audited: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == CRITICAL)

    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == WARNING)

    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == INFO)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "inputs_audited": self.inputs_audited,
            "summary": {
                **self.summary,
                "critical": self.critical_count(),
                "warning": self.warning_count(),
                "info": self.info_count(),
                "total_findings": len(self.findings),
            },
            "findings": [f.to_dict() for f in self.findings],
        }


# =====================================================================
# CLI
# =====================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit",
        description="Pre-flight validation and corpus sanity checks "
                    "for keyword CSV inputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--inputs", nargs="+", required=True,
                        help="CSV files or directories to audit")
    parser.add_argument("--client-domain", default="",
                        help="Client domain (validates URL fields)")
    parser.add_argument("--brand-list", default="",
                        help="Comma-separated brand list to validate")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON report instead of human-readable")
    parser.add_argument("--max-file-size-mb", type=int, default=500,
                        help="Maximum allowed CSV file size")
    parser.add_argument("--max-keyword-length", type=int, default=200,
                        help="Maximum allowed keyword string length")
    parser.add_argument("--single-source-warn", type=float, default=0.90,
                        help="Warn if >this fraction of corpus from "
                             "one source (0-1)")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as critical")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


# =====================================================================
# File-level audits
# =====================================================================

def audit_file_existence(path: Path, report: AuditReport) -> bool:
    """Check the file exists and is readable."""
    if not path.exists():
        report.add(Finding(
            severity=CRITICAL,
            category="file_missing",
            message=f"Input file does not exist: {path}",
            file_path=str(path),
            suggested_fix="Verify the path and try again.",
        ))
        return False
    if not path.is_file():
        report.add(Finding(
            severity=CRITICAL,
            category="not_a_file",
            message=f"Path is not a regular file: {path}",
            file_path=str(path),
        ))
        return False
    return True


def audit_file_size(path: Path, max_mb: int, report: AuditReport) -> bool:
    """Check the file is within the size limit."""
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes == 0:
        report.add(Finding(
            severity=CRITICAL,
            category="empty_file",
            message=f"File is empty: {path}",
            file_path=str(path),
            suggested_fix="Re-export from the source tool.",
        ))
        return False
    if size_mb > max_mb:
        report.add(Finding(
            severity=CRITICAL,
            category="oversized_file",
            message=(f"File is {size_mb:.1f} MB, exceeds limit "
                     f"of {max_mb} MB: {path}"),
            file_path=str(path),
            suggested_fix=(f"Split the file or pre-filter to under {max_mb} MB."),
        ))
        return False
    if size_mb > max_mb * 0.8:
        report.add(Finding(
            severity=WARNING,
            category="large_file",
            message=(f"File is {size_mb:.1f} MB, approaching limit "
                     f"of {max_mb} MB: {path.name}"),
            file_path=str(path),
        ))
    return True


def detect_encoding_for_audit(path: Path) -> Optional[str]:
    """Detect encoding; return None if cannot be detected."""
    try:
        with path.open("rb") as f:
            head = f.read(4096)
    except OSError:
        return None
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
        return None


def audit_encoding(path: Path, report: AuditReport) -> Optional[str]:
    """Audit encoding and warn on Latin-1, fail on UTF-16 without BOM."""
    encoding = detect_encoding_for_audit(path)
    if encoding is None:
        report.add(Finding(
            severity=CRITICAL,
            category="encoding_undetected",
            message=f"Cannot detect encoding for {path.name}",
            file_path=str(path),
            suggested_fix=("Re-export the CSV with UTF-8 encoding "
                           "(any modern tool supports this)."),
        ))
        return None
    if encoding == "utf-16":
        report.add(Finding(
            severity=WARNING,
            category="utf16_encoding",
            message=(f"File {path.name} is UTF-16 encoded; some downstream "
                     f"consumers expect UTF-8."),
            file_path=str(path),
            suggested_fix="Re-export as UTF-8 if possible.",
        ))
    elif encoding == "latin-1":
        report.add(Finding(
            severity=INFO,
            category="latin1_encoding",
            message=(f"File {path.name} is Latin-1 encoded; will be "
                     f"decoded by the pipeline but UTF-8 is preferred."),
            file_path=str(path),
        ))
    return encoding


def detect_separator_for_audit(path: Path, encoding: str
                                ) -> Tuple[Optional[str], int]:
    """Detect separator and return (separator, consistency_score)."""
    candidates = [",", ";", "\t", "|"]
    best = None
    best_score = -1
    try:
        with path.open(encoding=encoding) as f:
            head_lines = [f.readline() for _ in range(10)]
    except (OSError, UnicodeDecodeError):
        return None, 0
    head_lines = [ln for ln in head_lines if ln.strip()]
    if not head_lines:
        return None, 0
    for sep in candidates:
        counts = [ln.count(sep) for ln in head_lines]
        if not counts or counts[0] == 0:
            continue
        consistency = sum(1 for c in counts if c == counts[0])
        if consistency > best_score:
            best_score = consistency
            best = sep
    return best, best_score


def audit_separator(path: Path, encoding: str,
                     report: AuditReport) -> Optional[str]:
    """Audit CSV separator detection and consistency."""
    sep, score = detect_separator_for_audit(path, encoding)
    if sep is None:
        report.add(Finding(
            severity=CRITICAL,
            category="separator_undetected",
            message=f"Cannot detect a consistent separator in {path.name}",
            file_path=str(path),
            suggested_fix=("Verify the file is a valid CSV with a single "
                           "separator type (comma, semicolon, tab, or pipe)."),
        ))
        return None
    if score < 8:
        report.add(Finding(
            severity=WARNING,
            category="separator_inconsistent",
            message=(f"Separator {sep!r} detected in {path.name} but "
                     f"consistency score is low ({score}/10 lines)."),
            file_path=str(path),
            suggested_fix="Inspect the file for mixed separators.",
        ))
    return sep


def audit_header_and_keyword_column(path: Path, encoding: str, sep: str,
                                      report: AuditReport) -> bool:
    """Verify the file has a header and a recognizable keyword column."""
    try:
        with path.open(encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            try:
                headers = next(reader)
            except StopIteration:
                report.add(Finding(
                    severity=CRITICAL,
                    category="no_header",
                    message=f"File {path.name} has no header row",
                    file_path=str(path),
                ))
                return False
    except (OSError, UnicodeDecodeError) as e:
        report.add(Finding(
            severity=CRITICAL,
            category="read_failure",
            message=f"Cannot read {path.name}: {e}",
            file_path=str(path),
        ))
        return False

    if not headers or all(not h.strip() for h in headers):
        report.add(Finding(
            severity=CRITICAL,
            category="empty_header",
            message=f"File {path.name} has empty header row",
            file_path=str(path),
        ))
        return False

    keyword_synonyms = {"keyword", "query", "top queries"}
    headers_lower = {h.strip().lower() for h in headers}
    if not (headers_lower & keyword_synonyms):
        report.add(Finding(
            severity=CRITICAL,
            category="no_keyword_column",
            message=(f"File {path.name} has no recognizable keyword "
                     f"column. Headers: {headers[:8]}..."),
            file_path=str(path),
            suggested_fix=("Rename a column to 'keyword' or 'query', or "
                           "supply a --mapping JSON to analyze.py."),
        ))
        return False

    return True


# =====================================================================
# Row-level audits
# =====================================================================

def audit_rows(path: Path, encoding: str, sep: str,
               max_keyword_length: int, report: AuditReport
               ) -> Dict[str, Any]:
    """Walk the rows and accumulate sanity stats and findings."""
    stats = {
        "total_rows": 0,
        "empty_keyword_rows": 0,
        "long_keyword_rows": 0,
        "duplicate_keyword_count": 0,
        "negative_volume_rows": 0,
        "out_of_range_difficulty_rows": 0,
        "out_of_range_position_rows": 0,
        "inconsistent_column_count_rows": 0,
        "expected_column_count": 0,
    }

    try:
        with path.open(encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            try:
                headers = next(reader)
            except StopIteration:
                return stats
            stats["expected_column_count"] = len(headers)

            keyword_col_idx = -1
            for i, h in enumerate(headers):
                if h.strip().lower() in {"keyword", "query", "top queries"}:
                    keyword_col_idx = i
                    break

            volume_col_idx = -1
            difficulty_col_idx = -1
            position_col_idx = -1
            for i, h in enumerate(headers):
                hl = h.strip().lower()
                if hl in {"volume", "search volume", "monthly volume"}:
                    volume_col_idx = i
                elif hl in {"difficulty", "kd", "kd%", "keyword difficulty",
                            "seo difficulty", "sd"}:
                    difficulty_col_idx = i
                elif hl in {"position", "current position", "pos."}:
                    position_col_idx = i

            seen_keywords: Counter = Counter()

            for row_num, row in enumerate(reader, start=2):
                stats["total_rows"] += 1

                if len(row) != stats["expected_column_count"]:
                    stats["inconsistent_column_count_rows"] += 1
                    if stats["inconsistent_column_count_rows"] <= 5:
                        report.add(Finding(
                            severity=WARNING,
                            category="row_column_mismatch",
                            message=(f"Row has {len(row)} columns, expected "
                                     f"{stats['expected_column_count']}"),
                            file_path=str(path),
                            row_number=row_num,
                        ))
                    continue

                if keyword_col_idx >= 0 and len(row) > keyword_col_idx:
                    kw = row[keyword_col_idx].strip()
                    if not kw:
                        stats["empty_keyword_rows"] += 1
                    elif len(kw) > max_keyword_length:
                        stats["long_keyword_rows"] += 1
                        if stats["long_keyword_rows"] <= 3:
                            report.add(Finding(
                                severity=WARNING,
                                category="keyword_too_long",
                                message=(f"Keyword exceeds {max_keyword_length} "
                                         f"chars: {kw[:80]}..."),
                                file_path=str(path),
                                row_number=row_num,
                            ))
                    else:
                        seen_keywords[kw.lower()] += 1

                if volume_col_idx >= 0 and len(row) > volume_col_idx:
                    raw = row[volume_col_idx].strip()
                    if raw:
                        try:
                            v = int(raw.replace(",", "").replace(".", ""))
                            if v < 0:
                                stats["negative_volume_rows"] += 1
                        except ValueError:
                            pass

                if difficulty_col_idx >= 0 and len(row) > difficulty_col_idx:
                    raw = row[difficulty_col_idx].strip().rstrip("%")
                    if raw:
                        try:
                            d = float(raw.replace(",", "."))
                            if d < 0 or d > 100:
                                stats["out_of_range_difficulty_rows"] += 1
                        except ValueError:
                            pass

                if position_col_idx >= 0 and len(row) > position_col_idx:
                    raw = row[position_col_idx].strip()
                    if raw:
                        try:
                            p = float(raw.replace(",", "."))
                            if p < 1 or p > 100:
                                stats["out_of_range_position_rows"] += 1
                        except ValueError:
                            pass

            duplicates = sum(c - 1 for c in seen_keywords.values() if c > 1)
            stats["duplicate_keyword_count"] = duplicates

    except (OSError, UnicodeDecodeError) as e:
        report.add(Finding(
            severity=CRITICAL,
            category="row_read_failure",
            message=f"Failed to walk rows in {path.name}: {e}",
            file_path=str(path),
        ))

    return stats


def emit_row_findings(path: Path, stats: Dict[str, Any],
                       report: AuditReport) -> None:
    """Emit findings derived from row-level statistics."""
    if stats["total_rows"] == 0:
        report.add(Finding(
            severity=CRITICAL,
            category="no_data_rows",
            message=f"File {path.name} has zero data rows",
            file_path=str(path),
            suggested_fix="Re-export with at least one row of data.",
        ))
        return

    if stats["empty_keyword_rows"]:
        share = stats["empty_keyword_rows"] / stats["total_rows"]
        sev = WARNING if share < 0.1 else CRITICAL
        report.add(Finding(
            severity=sev,
            category="empty_keywords",
            message=(f"{stats['empty_keyword_rows']:,} rows "
                     f"({share:.1%}) have empty keyword field"),
            file_path=str(path),
            suggested_fix=("Pre-filter empty rows or re-export with the "
                           "tool's empty-row filter enabled."),
        ))

    if stats["duplicate_keyword_count"]:
        share = stats["duplicate_keyword_count"] / stats["total_rows"]
        if share > 0.05:
            report.add(Finding(
                severity=WARNING,
                category="many_duplicates",
                message=(f"{stats['duplicate_keyword_count']:,} duplicate "
                         f"keywords within file ({share:.1%})"),
                file_path=str(path),
                suggested_fix=("Inspect for accidental re-imports; the "
                               "pipeline preserves duplicates as multi-source "
                               "but in-file duplicates may indicate export "
                               "artifacts."),
            ))

    if stats["negative_volume_rows"]:
        report.add(Finding(
            severity=WARNING,
            category="negative_volume",
            message=(f"{stats['negative_volume_rows']:,} rows have "
                     f"negative volume values"),
            file_path=str(path),
        ))

    if stats["out_of_range_difficulty_rows"]:
        report.add(Finding(
            severity=WARNING,
            category="out_of_range_difficulty",
            message=(f"{stats['out_of_range_difficulty_rows']:,} rows "
                     f"have difficulty outside 0-100 range"),
            file_path=str(path),
        ))

    if stats["out_of_range_position_rows"]:
        report.add(Finding(
            severity=INFO,
            category="out_of_range_position",
            message=(f"{stats['out_of_range_position_rows']:,} rows "
                     f"have position outside 1-100 range (will be "
                     f"treated as null by the pipeline)"),
            file_path=str(path),
        ))

    if stats["inconsistent_column_count_rows"]:
        share = (stats["inconsistent_column_count_rows"]
                 / stats["total_rows"])
        sev = WARNING if share < 0.05 else CRITICAL
        report.add(Finding(
            severity=sev,
            category="inconsistent_column_count",
            message=(f"{stats['inconsistent_column_count_rows']:,} rows "
                     f"have inconsistent column counts ({share:.1%})"),
            file_path=str(path),
            suggested_fix=("Re-export from the source tool. Mixed column "
                           "counts often indicate manual editing."),
        ))


# =====================================================================
# Corpus-level audits
# =====================================================================

def audit_corpus_concentration(per_file_stats: List[Dict[str, Any]],
                                threshold: float,
                                report: AuditReport) -> None:
    """Check whether one source dominates the corpus."""
    if len(per_file_stats) < 2:
        return
    by_source: Counter = Counter()
    for s in per_file_stats:
        by_source[s["tool"]] += s["stats"]["total_rows"]
    total = sum(by_source.values())
    if total == 0:
        return
    for source, count in by_source.items():
        share = count / total
        if share > threshold:
            report.add(Finding(
                severity=WARNING,
                category="single_source_dominance",
                message=(f"Source '{source}' contributes {share:.1%} of "
                         f"the corpus, exceeding the {threshold:.0%} "
                         f"warning threshold."),
                suggested_fix=("Diversify sources to reduce sampling bias "
                               "(internal data + commercial tool + "
                               "competitor intelligence is a good baseline)."),
            ))


def audit_brand_list(brand_list_str: str, report: AuditReport) -> None:
    """Validate the brand list format."""
    if not brand_list_str:
        return
    brands = [b.strip() for b in brand_list_str.split(",") if b.strip()]
    if not brands:
        report.add(Finding(
            severity=WARNING,
            category="empty_brand_list",
            message="Brand list parameter provided but parsed to empty list",
            suggested_fix="Use comma-separated values: 'brand1,brand2'",
        ))
        return
    for b in brands:
        if len(b) < 2:
            report.add(Finding(
                severity=WARNING,
                category="short_brand",
                message=(f"Brand variation '{b}' is shorter than 2 chars; "
                         f"may produce false-positive matches."),
                suggested_fix=("Provide at least 2 characters per brand "
                               "variation."),
            ))


def audit_client_domain(client_domain: str, report: AuditReport) -> None:
    """Validate the client domain format."""
    if not client_domain:
        return
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", client_domain.lower()):
        report.add(Finding(
            severity=WARNING,
            category="malformed_domain",
            message=(f"Client domain '{client_domain}' does not match "
                     f"a typical domain pattern."),
            suggested_fix=("Use a bare domain like 'example.com' (no "
                           "scheme, no path)."),
        ))


# =====================================================================
# Top-level orchestration
# =====================================================================

def expand_inputs(input_args: List[str]) -> List[Path]:
    out: List[Path] = []
    for arg in input_args:
        p = Path(arg)
        if p.is_dir():
            out.extend(sorted(p.glob("*.csv")))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f"Input not found: {arg}")
    return out


def detect_tool_label(path: Path, encoding: str, sep: str) -> str:
    """Best-effort tool detection for the audit report."""
    try:
        with path.open(encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            headers = [h.strip().lower() for h in next(reader)]
    except (OSError, UnicodeDecodeError, StopIteration):
        return "unknown"
    header_set = set(headers)
    signatures = [
        ("semrush", {"keyword difficulty", "serp features by keyword"}),
        ("semrush", {"kd%", "parent topic"}),
        ("ahrefs", {"kd", "traffic potential (tp)"}),
        ("ahrefs", {"current position", "intents"}),
        ("gsc", {"top queries", "impressions"}),
        ("gsc", {"query", "ctr", "impressions"}),
        ("moz", {"monthly volume", "organic ctr"}),
        ("ubersuggest", {"seo difficulty"}),
    ]
    for name, sig in signatures:
        if sig.issubset(header_set):
            return name
    if "keyword" in header_set or "query" in header_set:
        return "generic"
    return "unknown"


def run_audit(args: argparse.Namespace) -> AuditReport:
    """Run all audit passes and return the AuditReport."""
    import datetime as dt
    report = AuditReport(
        timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    audit_brand_list(args.brand_list, report)
    audit_client_domain(args.client_domain, report)

    try:
        input_paths = expand_inputs(args.inputs)
    except FileNotFoundError as e:
        report.add(Finding(
            severity=CRITICAL,
            category="path_not_found",
            message=str(e),
        ))
        return report

    if not input_paths:
        report.add(Finding(
            severity=CRITICAL,
            category="no_inputs",
            message="No CSV files found in --inputs paths",
            suggested_fix="Verify the inputs directory contains .csv files.",
        ))
        return report

    report.inputs_audited = [str(p) for p in input_paths]
    per_file_stats: List[Dict[str, Any]] = []

    for path in input_paths:
        if not audit_file_existence(path, report):
            continue
        if not audit_file_size(path, args.max_file_size_mb, report):
            continue
        encoding = audit_encoding(path, report)
        if encoding is None:
            continue
        sep = audit_separator(path, encoding, report)
        if sep is None:
            continue
        if not audit_header_and_keyword_column(path, encoding, sep, report):
            continue
        tool_label = detect_tool_label(path, encoding, sep)
        stats = audit_rows(path, encoding, sep, args.max_keyword_length,
                           report)
        emit_row_findings(path, stats, report)
        per_file_stats.append({
            "path": str(path),
            "tool": tool_label,
            "encoding": encoding,
            "separator": sep,
            "stats": stats,
        })

    audit_corpus_concentration(per_file_stats, args.single_source_warn,
                                report)

    report.summary = {
        "files_audited": len(input_paths),
        "files_passed": len(per_file_stats),
        "total_rows": sum(s["stats"]["total_rows"]
                          for s in per_file_stats),
        "per_file": per_file_stats,
    }
    return report


# =====================================================================
# Output rendering
# =====================================================================

def render_human_report(report: AuditReport) -> str:
    """Render the audit report as human-readable text."""
    out = []
    out.append("=" * 60)
    out.append("KEYWORD INTELLIGENCE: PRE-FLIGHT AUDIT REPORT")
    out.append("=" * 60)
    out.append(f"Run timestamp:    {report.timestamp}")
    out.append(f"Files audited:    {len(report.inputs_audited)}")
    out.append(f"Critical issues:  {report.critical_count()}")
    out.append(f"Warnings:         {report.warning_count()}")
    out.append(f"Info notes:       {report.info_count()}")
    out.append(f"Total rows seen:  "
               f"{report.summary.get('total_rows', 0):,}")
    out.append("")

    by_severity: Dict[str, List[Finding]] = defaultdict(list)
    for f in report.findings:
        by_severity[f.severity].append(f)

    for severity in (CRITICAL, WARNING, INFO):
        items = by_severity.get(severity, [])
        if not items:
            continue
        label = severity.upper()
        out.append(f"--- {label} ({len(items)}) ---")
        for f in items:
            location = ""
            if f.file_path:
                location = f" [{Path(f.file_path).name}"
                if f.row_number:
                    location += f":{f.row_number}"
                location += "]"
            out.append(f"  [{f.category}]{location}")
            out.append(f"    {f.message}")
            if f.suggested_fix:
                out.append(f"    Fix: {f.suggested_fix}")
            out.append("")
        out.append("")

    if report.summary.get("per_file"):
        out.append("--- PER-FILE STATS ---")
        for entry in report.summary["per_file"]:
            out.append(f"  {Path(entry['path']).name}")
            out.append(f"    Tool detected:   {entry['tool']}")
            out.append(f"    Encoding:        {entry['encoding']}")
            out.append(f"    Separator:       {entry['separator']!r}")
            stats = entry["stats"]
            out.append(f"    Rows:            {stats['total_rows']:,}")
            if stats.get("duplicate_keyword_count"):
                out.append(f"    Duplicates:      "
                           f"{stats['duplicate_keyword_count']:,}")
            out.append("")

    out.append("=" * 60)
    if report.critical_count() > 0:
        out.append("VERDICT: critical issues found. Pipeline will fail.")
    elif report.warning_count() > 0:
        out.append("VERDICT: warnings present. Pipeline will run.")
    else:
        out.append("VERDICT: audit passed. Pipeline ready.")
    out.append("=" * 60)
    return "\n".join(out)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    try:
        report = run_audit(args)

        if args.json:
            print(json.dumps(report.to_dict(), indent=2,
                              ensure_ascii=False))
        else:
            print(render_human_report(report))

        if report.critical_count() > 0:
            return 1
        if args.strict and report.warning_count() > 0:
            return 1
        if report.warning_count() > 0:
            return 2
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
