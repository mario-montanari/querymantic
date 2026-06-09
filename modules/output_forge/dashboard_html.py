#!/usr/bin/env python3
"""Self-contained HTML dashboard renderer.

This is the always-available output. It needs no third-party package and loads no
external resource: charts are drawn as inline SVG, styles are inlined, and there is
no script tag and no CDN reference, so the file opens the same way on a machine with
no network. That makes it the floor the suite degrades to when the Office backends
are absent, and it is byte-reproducible because every value comes from the
deterministic view and the only timestamp shown is the pinned run timestamp.

A future enhancement may mount interactive Plotly charts from a vendored, pinned
copy of plotly.js; that copy is not bundled yet, so the inline-SVG charts stand on
their own. The methodology reference records this.
"""

from __future__ import annotations

import html
from typing import Any

# Chart geometry, in SVG user units. Fixed so two renders are byte-identical.
_BAR_W = 520
_BAR_H = 22
_BAR_GAP = 8
_LABEL_W = 230
_VALUE_W = 90


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_int(value: Any) -> str:
    return (
        f"{int(value):,}"
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else "n/a"
    )


def _fmt_pct(value: Any, scale: float = 100.0) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value * scale:.1f}%"
    return "n/a"


def _fmt_band(band: Any) -> str:
    if isinstance(band, list) and len(band) == 2:
        return f"{int(band[0]):,} to {int(band[1]):,}"
    return "n/a"


def _bar_chart(rows: list[tuple[str, float, str]], colors: dict[str, str]) -> str:
    """Render a horizontal bar chart as inline SVG.

    ``rows`` is a list of (label, value, value_label). Bars are scaled to the
    largest value; a zero maximum yields empty bars rather than a divide error.
    """
    if not rows:
        return ""
    max_value = max((v for _, v, _ in rows), default=0.0) or 1.0
    height = len(rows) * (_BAR_H + _BAR_GAP) + _BAR_GAP
    width = _LABEL_W + _BAR_W + _VALUE_W
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" width="100%" '
        f'style="max-width:{width}px" preserveAspectRatio="xMinYMin meet">'
    ]
    y = _BAR_GAP
    for label, value, value_label in rows:
        bar_px = int(round(_BAR_W * (max(0.0, value) / max_value)))
        text_y = y + _BAR_H - 6
        parts.append(
            f'<text x="0" y="{text_y}" font-size="13" fill="{colors["text"]}">{_esc(label)}</text>'
        )
        parts.append(
            f'<rect x="{_LABEL_W}" y="{y}" width="{bar_px}" height="{_BAR_H}" '
            f'rx="3" fill="{colors["secondary"]}"></rect>'
        )
        parts.append(
            f'<text x="{_LABEL_W + bar_px + 8}" y="{text_y}" font-size="12" '
            f'fill="{colors["muted"]}">{_esc(value_label)}</text>'
        )
        y += _BAR_H + _BAR_GAP
    parts.append("</svg>")
    return "".join(parts)


def _band_chart(rows: list[tuple[str, int, int]], colors: dict[str, str]) -> str:
    """Render low-to-high bands as inline SVG floating bars on a shared scale."""
    if not rows:
        return ""
    max_value = max((hi for _, _, hi in rows), default=0) or 1
    height = len(rows) * (_BAR_H + _BAR_GAP) + _BAR_GAP
    width = _LABEL_W + _BAR_W + _VALUE_W
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" width="100%" '
        f'style="max-width:{width}px" preserveAspectRatio="xMinYMin meet">'
    ]
    y = _BAR_GAP
    for label, low, high in rows:
        x_low = int(round(_BAR_W * (max(0, low) / max_value)))
        x_high = int(round(_BAR_W * (max(0, high) / max_value)))
        span = max(2, x_high - x_low)
        text_y = y + _BAR_H - 6
        parts.append(
            f'<text x="0" y="{text_y}" font-size="13" fill="{colors["text"]}">{_esc(label)}</text>'
        )
        parts.append(
            f'<rect x="{_LABEL_W}" y="{y}" width="{_BAR_W}" height="{_BAR_H}" '
            f'rx="3" fill="{colors["band"]}" opacity="0.4"></rect>'
        )
        parts.append(
            f'<rect x="{_LABEL_W + x_low}" y="{y}" width="{span}" height="{_BAR_H}" '
            f'rx="3" fill="{colors["accent"]}"></rect>'
        )
        parts.append(
            f'<text x="{_LABEL_W + _BAR_W + 8}" y="{text_y}" font-size="12" '
            f'fill="{colors["muted"]}">{_fmt_int(low)} to {_fmt_int(high)}</text>'
        )
        y += _BAR_H + _BAR_GAP
    parts.append("</svg>")
    return "".join(parts)


def _section(title: str, body: str) -> str:
    return f"<section><h2>{_esc(title)}</h2>{body}</section>"


def _corpus_section(view: dict[str, Any], colors: dict[str, str]) -> str:
    corpus = view["corpus"]
    rows = [
        (r["intent"].replace("_", " "), float(r["count"]), str(r["count"]))
        for r in corpus["intent_split"]
    ]
    cards = "".join(
        f'<div class="card"><div class="num">{_esc(label)}</div><div class="lbl">{_esc(sub)}</div></div>'
        for label, sub in (
            (_fmt_int(corpus["total_keywords"]), "keywords"),
            (_fmt_pct(corpus["aio_eligibility_share"]), "AI Overview eligible"),
            (
                _fmt_pct(corpus["geo_opportunity_share"]),
                "generative-engine opportunity",
            ),
            (str(corpus["demand_opportunity_score"]), "demand opportunity score"),
        )
    )
    return _section(
        "Demand overview",
        f'<div class="cards">{cards}</div>'
        f"<h3>Search intent</h3>{_bar_chart(rows, colors)}",
    )


def _winnable_section(view: dict[str, Any], colors: dict[str, str]) -> str:
    winnable = view.get("winnable")
    if not winnable:
        return ""
    rows = [
        (
            r["intent"].replace("_", " "),
            int(r["winnable_band"][0]),
            int(r["winnable_band"][1]),
        )
        for r in winnable["by_intent"]
    ]
    headline = (
        f'<p class="headline">Portfolio winnable clicks per month: '
        f"<strong>{_fmt_band(winnable.get('portfolio_winnable_band'))}</strong> "
        f"(modelled current {_fmt_int(winnable.get('current_clicks_estimate'))}).</p>"
    )
    if "observed_current_clicks" in winnable:
        headline += (
            f'<p class="observed">Observed current clicks (Live Wire): '
            f"<strong>{_fmt_int(winnable.get('observed_current_clicks'))}</strong>; "
            f"observed winnable band {_fmt_band(winnable.get('observed_winnable_band'))}.</p>"
        )
    return _section("Winnable clicks", headline + _band_chart(rows, colors))


def _readiness_section(view: dict[str, Any], colors: dict[str, str]) -> str:
    readiness = view.get("readiness")
    if not readiness:
        return ""
    rows = [
        (
            c["head"],
            float(c.get("expected_readiness") or 0.0),
            f"{c.get('expected_readiness')}",
        )
        for c in view["top_clusters"]
        if "expected_readiness" in c
    ]
    note = (
        f'<p class="headline">Mean expected readiness: '
        f"<strong>{readiness['mean_expected_readiness']}</strong> out of 100, "
        f"across {readiness['scored_components']} scored components "
        f"({readiness['checklist_only_components']} checklist-only).</p>"
    )
    return _section("AI-citation readiness (expected)", note + _bar_chart(rows, colors))


def _clusters_table(view: dict[str, Any]) -> str:
    has_obs = any("observed_current_clicks" in c for c in view["clusters"])
    head_cells = [
        "Cluster",
        "Size",
        "Volume",
        "Intent",
        "Authority",
        "Cover@tau",
        "Readiness",
        "Winnable clicks",
    ]
    if has_obs:
        head_cells.append("Observed clicks")
    header = "".join(f"<th>{_esc(h)}</th>" for h in head_cells)
    body_rows = []
    for c in view["top_clusters"]:
        cells = [
            _esc(c["head"]),
            _esc(c.get("size")),
            _fmt_int(c.get("volume_total")),
            _esc(c.get("dominant_intent", "").replace("_", " ")),
            _esc(c.get("topical_authority", "n/a")),
            _esc(c.get("cover_at_tau", "n/a")),
            _esc(c.get("expected_readiness", "n/a")),
            _fmt_band(c.get("winnable_band")),
        ]
        if has_obs:
            cells.append(
                _fmt_int(c["observed_current_clicks"])
                if "observed_current_clicks" in c
                else "n/a"
            )
        body_rows.append(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"
        )
    return _section(
        "Clusters by demand",
        f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>",
    )


def _gaps_section(view: dict[str, Any]) -> str:
    gaps = view.get("gaps") or []
    if not gaps:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(g['entity'])}</td><td>{_fmt_int(g.get('demand_volume'))}</td>"
        f"<td>{_esc(g.get('suggested_cluster_head'))}</td></tr>"
        for g in gaps
    )
    return _section(
        "Entity gaps",
        f"<table><thead><tr><th>Entity</th><th>Demand</th><th>Suggested cluster</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
    )


def _observed_section(view: dict[str, Any]) -> str:
    obs = view.get("observed")
    if not obs:
        return ""
    split = "".join(
        f"<tr><td>{_esc(d['domain'])}</td><td>{_fmt_pct(d['share'], scale=1.0)}</td></tr>"
        for d in obs.get("competitor_split", [])
    )
    surfaces = ", ".join(obs.get("surfaces") or []) or "n/a"
    return _section(
        "Observed citations (Live Wire)",
        f'<p class="headline">Observed client citation share: '
        f"<strong>{_fmt_pct(obs.get('observed_citation_share'), scale=1.0)}</strong> "
        f"on surfaces: {_esc(surfaces)}.</p>"
        f"<table><thead><tr><th>Domain</th><th>Citation share</th></tr></thead>"
        f"<tbody>{split}</tbody></table>",
    )


def _provenance_section(view: dict[str, Any]) -> str:
    notes = view.get("provenance_notes") or []
    if not notes:
        return ""
    items = "".join(f"<li>{_esc(n)}</li>" for n in notes)
    return _section("How to read these figures", f"<ul>{items}</ul>")


def _style(brand: dict[str, Any]) -> str:
    c = brand["colors"]
    return (
        "*{box-sizing:border-box}"
        f"body{{margin:0;font-family:{brand['font_family']};color:{c['text']};"
        f"background:{c['background']};line-height:1.5}}"
        "main{max-width:980px;margin:0 auto;padding:32px 24px}"
        f"header.brand{{border-bottom:4px solid {c['primary']};padding-bottom:16px;margin-bottom:24px}}"
        f"header.brand .name{{font-size:26px;font-weight:700;color:{c['primary']}}}"
        f"header.brand .tagline{{color:{c['muted']};font-size:14px}}"
        f"h2{{color:{c['primary']};font-size:20px;border-bottom:1px solid {c['band']};"
        "padding-bottom:6px;margin-top:36px}"
        f"h3{{color:{c['secondary']};font-size:15px;margin-bottom:6px}}"
        ".cards{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}"
        f".card{{flex:1 1 160px;border:1px solid {c['band']};border-radius:8px;padding:14px}}"
        f".card .num{{font-size:22px;font-weight:700;color:{c['primary']}}}"
        f".card .lbl{{font-size:12px;color:{c['muted']}}}"
        "table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}"
        f"th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid {c['band']}}}"
        f"th{{color:{c['secondary']};font-weight:600}}"
        ".headline{font-size:15px}"
        f".observed{{font-size:14px;color:{c['accent']}}}"
        f"footer{{margin-top:40px;padding-top:16px;border-top:1px solid {c['band']};"
        f"color:{c['muted']};font-size:12px}}"
    )


def render_html(view: dict[str, Any], brand: dict[str, Any]) -> bytes:
    """Render the full dashboard as a self-contained HTML document (UTF-8 bytes)."""
    colors = brand["colors"]
    header = view["header"]
    title = header["label"] or f"{brand['name']} keyword and demand audit"

    body = "".join(
        [
            _corpus_section(view, colors),
            _winnable_section(view, colors),
            _readiness_section(view, colors),
            _clusters_table(view),
            _gaps_section(view),
            _observed_section(view),
            _provenance_section(view),
        ]
    )

    meta = (
        f"<footer><p>{_esc(brand['footer'])}</p>"
        f"<p>{_esc(brand['name'])}"
        + (f" &middot; {_esc(brand['contact'])}" if brand.get("contact") else "")
        + f" &middot; generated {_esc(header['generated_at'])}"
        f" &middot; input hash {_esc(header['input_hash'][:12])}"
        f" &middot; plugin {_esc(header['plugin_version'])}</p></footer>"
    )

    doc = (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)}</title>"
        f"<style>{_style(brand)}</style></head><body><main>"
        f'<header class="brand"><div class="name">{_esc(brand["name"])}</div>'
        f'<div class="tagline">{_esc(title)}</div></header>'
        f"{body}{meta}"
        "</main></body></html>"
    )
    return doc.encode("utf-8")
