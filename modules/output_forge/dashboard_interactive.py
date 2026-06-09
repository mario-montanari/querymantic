#!/usr/bin/env python3
"""Optional interactive HTML dashboard, a progressive enhancement over the SVG core.

This renderer produces the same dashboard as ``dashboard_html`` but mounts the three
charts as interactive Plotly figures. It is opt-in (``--forge-interactive``) and never
the default: the always-available dashboard stays script-free inline SVG, so its
byte-for-byte determinism proof and its self-containment test are untouched.

The enhancement is genuine and stays offline. Each chart container holds the static
SVG as fallback content, and a pinned, vendored copy of plotly.js (the partial
``plotly-basic`` bundle) is inlined into the page, with no content delivery network
reference, so the file opens the same way on a machine with no network. When scripts
run, Plotly draws into the containers; when they do not, the SVG fallback stands. The
page is byte-reproducible because every figure comes from the deterministic view, the
vendored bundle is a fixed file, and no timestamp or generated identifier is emitted.

The vendored bundle's version and SHA-256 are recorded outside the published files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dashboard_html import (
    _band_chart,
    _bar_chart,
    _clusters_table,
    _esc,
    _fmt_int,
    _fmt_pct,
    _gaps_section,
    _observed_section,
    _provenance_section,
    _section,
    _style,
)

# The vendored Plotly bundle. The basic partial bundle covers bar, scatter, and pie,
# which is all the dashboard's bar and band charts need; the full bundle is not taken.
PLOTLY_VERSION = "3.6.0"
PLOTLY_BUNDLE = "plotly-basic"
_VENDOR_REL = ("vendor", "plotly", f"{PLOTLY_BUNDLE}-{PLOTLY_VERSION}.min.js")


def vendored_plotly_path() -> Path:
    """Absolute path to the vendored plotly.js bundle inside the plugin."""
    return Path(__file__).resolve().parents[2].joinpath(*_VENDOR_REL)


def interactive_available() -> bool:
    """True when the vendored Plotly bundle is present, so the variant can render."""
    return vendored_plotly_path().is_file()


def _load_plotly_js() -> str:
    return vendored_plotly_path().read_text(encoding="utf-8")


def _intent_chart(view: dict[str, Any], colors: dict[str, str]) -> dict[str, Any]:
    rows = view["corpus"]["intent_split"]
    labels = [r["intent"].replace("_", " ") for r in rows]
    counts = [int(r["count"]) for r in rows]
    return {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "y": labels,
                "x": counts,
                "marker": {"color": colors["secondary"]},
                "hovertemplate": "%{y}: %{x} keywords<extra></extra>",
            }
        ],
        "layout": _layout(len(labels), colors, xaxis_title="Keywords"),
    }


def _readiness_chart(view: dict[str, Any], colors: dict[str, str]) -> dict[str, Any]:
    rows = [c for c in view["top_clusters"] if "expected_readiness" in c]
    labels = [str(c["head"]) for c in rows]
    values = [float(c.get("expected_readiness") or 0.0) for c in rows]
    return {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "y": labels,
                "x": values,
                "marker": {"color": colors["secondary"]},
                "hovertemplate": "%{y}: %{x} of 100<extra></extra>",
            }
        ],
        "layout": _layout(
            len(labels), colors, xaxis_title="Expected readiness (0 to 100)"
        ),
    }


def _winnable_chart(view: dict[str, Any], colors: dict[str, str]) -> dict[str, Any]:
    rows = view["winnable"]["by_intent"]
    labels = [r["intent"].replace("_", " ") for r in rows]
    lows = [int(r["winnable_band"][0]) for r in rows]
    spans = [int(r["winnable_band"][1]) - int(r["winnable_band"][0]) for r in rows]
    customdata = [
        [int(r["winnable_band"][0]), int(r["winnable_band"][1])] for r in rows
    ]
    return {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "y": labels,
                "base": lows,
                "x": spans,
                "marker": {"color": colors["accent"]},
                "customdata": customdata,
                "hovertemplate": (
                    "%{y}: %{customdata[0]:,} to %{customdata[1]:,} clicks/mo"
                    "<extra></extra>"
                ),
            }
        ],
        "layout": _layout(len(labels), colors, xaxis_title="Winnable clicks per month"),
    }


def _layout(n_rows: int, colors: dict[str, str], xaxis_title: str) -> dict[str, Any]:
    """A fixed, deterministic layout. Height scales with the row count only."""
    height = max(160, n_rows * 34 + 80)
    return {
        "height": height,
        "margin": {"l": 170, "r": 24, "t": 12, "b": 44},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": colors["text"], "size": 13},
        "showlegend": False,
        "bargap": 0.28,
        "xaxis": {
            "title": {"text": xaxis_title, "font": {"size": 12}},
            "gridcolor": colors["band"],
            "zerolinecolor": colors["band"],
        },
        # First row of the view goes on top, matching the SVG order.
        "yaxis": {"autorange": "reversed", "automargin": True},
    }


def _plot_section(
    title: str,
    plot_id: str,
    fallback_svg: str,
    extra_html: str = "",
) -> str:
    """A section whose chart is a Plotly container with the SVG as fallback."""
    body = (
        extra_html + f'<div class="plot" id="{plot_id}" role="img">{fallback_svg}</div>'
    )
    return _section(title, body)


def _corpus_section(view: dict[str, Any], colors: dict[str, str]) -> str:
    corpus = view["corpus"]
    cards = "".join(
        f'<div class="card"><div class="num">{_esc(label)}</div>'
        f'<div class="lbl">{_esc(sub)}</div></div>'
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
    rows = [
        (r["intent"].replace("_", " "), float(r["count"]), str(r["count"]))
        for r in corpus["intent_split"]
    ]
    return _plot_section(
        "Demand overview",
        "plot-intent",
        _bar_chart(rows, colors),
        extra_html=f'<div class="cards">{cards}</div><h3>Search intent</h3>',
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
        f"<strong>{_band_label(winnable.get('portfolio_winnable_band'))}</strong> "
        f"(modelled current {_fmt_int(winnable.get('current_clicks_estimate'))}).</p>"
    )
    if "observed_current_clicks" in winnable:
        headline += (
            f'<p class="observed">Observed current clicks (Live Wire): '
            f"<strong>{_fmt_int(winnable.get('observed_current_clicks'))}</strong>; "
            f"observed winnable band "
            f"{_band_label(winnable.get('observed_winnable_band'))}.</p>"
        )
    return _plot_section(
        "Winnable clicks",
        "plot-winnable",
        _band_chart(rows, colors),
        extra_html=headline,
    )


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
    return _plot_section(
        "AI-citation readiness (expected)",
        "plot-readiness",
        _bar_chart(rows, colors),
        extra_html=note,
    )


def _band_label(band: Any) -> str:
    if isinstance(band, list) and len(band) == 2:
        return f"{int(band[0]):,} to {int(band[1]):,}"
    return "n/a"


def _plot_data(view: dict[str, Any], colors: dict[str, str]) -> dict[str, Any]:
    """The chart specs Plotly draws, keyed by container id. Only present charts."""
    data: dict[str, Any] = {"plot-intent": _intent_chart(view, colors)}
    if view.get("winnable"):
        data["plot-winnable"] = _winnable_chart(view, colors)
    if view.get("readiness") and any(
        "expected_readiness" in c for c in view["top_clusters"]
    ):
        data["plot-readiness"] = _readiness_chart(view, colors)
    return data


def _json_island(payload: dict[str, Any]) -> str:
    """A JSON data island, with ``<`` escaped so no value can close the script tag."""
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return text.replace("<", "\\u003c")


# The init runs once the page and the inlined Plotly are parsed. It draws each chart
# into its container, replacing the SVG fallback; if Plotly is missing or a draw
# fails, the SVG fallback simply stays, so the page degrades rather than breaks.
_INIT_JS = (
    "(function(){"
    "if(typeof Plotly==='undefined')return;"
    'var el=document.getElementById("querymantic-plotdata");'
    "if(!el)return;"
    "var specs=JSON.parse(el.textContent);"
    "var cfg={displayModeBar:false,responsive:true};"
    "Object.keys(specs).forEach(function(id){"
    "var node=document.getElementById(id);"
    "if(!node)return;"
    "try{node.innerHTML='';Plotly.newPlot(node,specs[id].data,specs[id].layout,cfg);}"
    "catch(e){}"
    "});"
    "})();"
)


def render_interactive_html(view: dict[str, Any], brand: dict[str, Any]) -> bytes:
    """Render the interactive dashboard as a self-contained HTML document (UTF-8).

    Raises ``FileNotFoundError`` if the vendored Plotly bundle is absent; callers
    check ``interactive_available()`` first and skip the format when it is not there.
    """
    plotly_js = _load_plotly_js()
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

    plot_style = (
        ".plot{margin-top:8px;min-height:160px}.plot .js-plotly-plot{width:100%}"
    )
    island = _json_island(_plot_data(view, colors))

    doc = (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)}</title>"
        f"<style>{_style(brand)}{plot_style}</style></head><body><main>"
        f'<header class="brand"><div class="name">{_esc(brand["name"])}</div>'
        f'<div class="tagline">{_esc(title)}</div></header>'
        f"{body}{meta}"
        "</main>"
        f'<script type="application/json" id="querymantic-plotdata">{island}</script>'
        f"<script>{plotly_js}</script>"
        f"<script>{_INIT_JS}</script>"
        "</body></html>"
    )
    return doc.encode("utf-8")


__all__ = [
    "render_interactive_html",
    "interactive_available",
    "vendored_plotly_path",
    "PLOTLY_VERSION",
    "PLOTLY_BUNDLE",
]
