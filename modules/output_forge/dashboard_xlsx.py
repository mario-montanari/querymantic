#!/usr/bin/env python3
"""Excel dashboard renderer (.xlsx) behind openpyxl.

Turns the report view into a workbook an analyst can sort and filter: an Overview
sheet with the headline figures, a Clusters sheet with every per-cluster metric, a
Gaps sheet, and a Winnable sheet split by intent. The document properties and dates
are pinned to the run timestamp so the file is byte-stable across runs once the port
normalises the archive.

This path needs ``openpyxl`` (an optional backend). The caller checks
``ooxml_capabilities()`` and skips this format cleanly when the package is absent.
The rendering is exercised in continuous integration; locally the suite degrades to
the HTML dashboard.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _hex(color: str) -> str:
    return color.lstrip("#").upper()


def _header_row(ws, headers: list[str], brand: dict[str, Any]) -> None:
    from openpyxl.styles import Font, PatternFill

    fill = PatternFill("solid", fgColor=_hex(brand["colors"]["primary"]))
    font = Font(bold=True, color="FFFFFF")
    ws.append(headers)
    for cell in ws[ws.max_row]:
        cell.fill = fill
        cell.font = font


def render_workbook(view: dict[str, Any], brand: dict[str, Any], out_path: Path, timestamp: datetime) -> None:
    """Render the Excel dashboard to ``out_path``. Requires openpyxl."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    header = view["header"]
    title_text = header["label"] or f"{brand['name']} keyword and demand audit"
    wb = Workbook()

    # Overview sheet.
    ws = wb.active
    ws.title = "Overview"
    ws["A1"] = title_text
    ws["A1"].font = Font(bold=True, size=14, color=_hex(brand["colors"]["primary"]))
    ws["A2"] = f"{brand['name']} | {brand['tagline']}"
    corpus = view["corpus"]
    ws.append([])
    _header_row(ws, ["Metric", "Value"], brand)
    for label, value in (
        ("Keywords analysed", corpus["total_keywords"]),
        ("AI Overview eligibility share", corpus["aio_eligibility_share"]),
        ("Generative-engine opportunity share", corpus["geo_opportunity_share"]),
        ("Demand opportunity score", corpus["demand_opportunity_score"]),
    ):
        ws.append([label, value])
    ws.append([])
    _header_row(ws, ["Search intent", "Keywords"], brand)
    for row in corpus["intent_split"]:
        ws.append([row["intent"].replace("_", " "), row["count"]])

    # Clusters sheet.
    cs = wb.create_sheet("Clusters")
    cols = [
        "Cluster", "Size", "Volume", "Intent", "Topical authority", "Cover@tau",
        "Expected readiness", "Expected share", "Winnable low", "Winnable high",
    ]
    has_obs = any("observed_current_clicks" in c for c in view["clusters"])
    if has_obs:
        cols += ["Observed clicks", "Observed citation share"]
    _header_row(cs, cols, brand)
    for c in view["clusters"]:
        band = c.get("winnable_band") or [None, None]
        row = [
            c["head"], c.get("size"), c.get("volume_total"),
            str(c.get("dominant_intent", "")).replace("_", " "),
            c.get("topical_authority"), c.get("cover_at_tau"),
            c.get("expected_readiness"), c.get("expected_share"),
            band[0], band[1],
        ]
        if has_obs:
            row += [c.get("observed_current_clicks"), c.get("observed_citation_share")]
        cs.append(row)
    cs.freeze_panes = "A2"

    # Winnable sheet.
    winnable = view.get("winnable")
    if winnable:
        ws2 = wb.create_sheet("Winnable")
        _header_row(ws2, ["Intent", "Winnable low", "Winnable high"], brand)
        for r in winnable["by_intent"]:
            ws2.append([r["intent"].replace("_", " "), r["winnable_band"][0], r["winnable_band"][1]])
        ws2.append([])
        band = winnable.get("portfolio_winnable_band") or [None, None]
        ws2.append(["Portfolio", band[0], band[1]])

    # Gaps sheet.
    gaps = view.get("gaps") or []
    if gaps:
        gs = wb.create_sheet("Gaps")
        _header_row(gs, ["Entity", "Demand", "Suggested cluster"], brand)
        for g in gaps:
            gs.append([g["entity"], g.get("demand_volume"), g.get("suggested_cluster_head")])

    props = wb.properties
    props.creator = brand["author"]
    props.title = title_text
    props.created = timestamp
    props.modified = timestamp

    wb.save(str(out_path))
