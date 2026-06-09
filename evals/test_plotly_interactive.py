#!/usr/bin/env python3
"""Tests for the optional interactive Plotly dashboard.

Covers that the variant renders from the vendored, pinned plotly.js bundle, that it
inlines the library with no external load (so it stays offline), that it keeps the
static SVG as a fallback, that it is byte-deterministic, and that Output Forge treats
it as an opt-in format: it appears only when requested, is recorded in the manifest
with its SHA-256, and is skipped with a reason when the vendored bundle is absent.

The default ``html`` dashboard is unaffected and its script-free contract is verified
in test_sprint7_output_forge.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.output_forge import output_forge  # noqa: E402
from modules.output_forge.brand import load_brand, resolve_brand  # noqa: E402
from modules.output_forge.dashboard_interactive import (  # noqa: E402
    PLOTLY_VERSION,
    interactive_available,
    render_interactive_html,
    vendored_plotly_path,
)
from modules.output_forge.model import build_view  # noqa: E402
from querymantic import pipeline  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
BRAND_FILE = PLUGIN_ROOT / "forge" / "templates" / "brand.json"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"
OFFLINE_STACK = ("entity_web", "fan_out_radar", "citation_grid", "click_ceiling")


def _run(tmp: Path, modules: tuple[str, ...]) -> dict:
    kwargs: dict = {}
    if "output_forge" in modules:
        kwargs["output_forge"] = {
            "out_dir": tmp / "forge",
            "brand": load_brand(BRAND_FILE),
        }
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs=kwargs,
    )


# --- the vendored bundle ----------------------------------------------------


def test_vendored_bundle_is_present() -> None:
    assert interactive_available()
    path = vendored_plotly_path()
    assert path.is_file()
    assert PLOTLY_VERSION in path.name
    # A real bundle, not a stub: over a hundred kilobytes of minified JavaScript.
    assert path.stat().st_size > 100_000


# --- the rendered document --------------------------------------------------


def test_interactive_html_inlines_plotly_offline(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    html = render_interactive_html(build_view(state), resolve_brand(None)).decode(
        "utf-8"
    )
    assert html.startswith("<!DOCTYPE html>")
    # The library is present and inlined, not loaded from anywhere.
    assert "Plotly" in html and "newPlot" in html
    for needle in ("<script src", "<link ", 'src="http'):
        assert needle not in html, f"unexpected external load: {needle}"
    # The data island and the three chart containers are emitted.
    assert 'id="querymantic-plotdata"' in html
    for plot_id in ("plot-intent", "plot-winnable", "plot-readiness"):
        assert f'id="{plot_id}"' in html
    # The static SVG stays as the fallback inside each container.
    assert "<svg" in html


def test_interactive_html_is_deterministic(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    view = build_view(state)
    brand = resolve_brand(None)
    assert render_interactive_html(view, brand) == render_interactive_html(view, brand)


def test_json_island_escapes_hostile_input() -> None:
    # Directly feed the escape a payload that tries to close the script tag.
    from modules.output_forge.dashboard_interactive import _json_island

    out = _json_island({"label": "</script><script>alert(1)</script>"})
    assert "<" not in out
    assert "\\u003c" in out


def test_data_island_cannot_close_the_script_tag(tmp_path: Path) -> None:
    # Inject a hostile chart label into the view and confirm no "<" survives in the
    # island, so a keyword containing "</script>" cannot break out of it.
    state = _run(tmp_path, OFFLINE_STACK)
    view = build_view(state)
    hostile = "</script><script>alert(1)</script>"
    assert view["corpus"]["intent_split"], "sample must have intent rows to inject into"
    view["corpus"]["intent_split"][0]["intent"] = hostile
    if view["top_clusters"]:
        view["top_clusters"][0]["head"] = hostile
    html = render_interactive_html(view, resolve_brand(None)).decode("utf-8")
    island = html.split('id="querymantic-plotdata">', 1)[1].split("</script>", 1)[0]
    assert "<" not in island
    assert "\\u003c" in island


# --- Output Forge wiring ----------------------------------------------------


def test_interactive_is_opt_in_only(tmp_path: Path) -> None:
    # The default formats do not include the interactive dashboard.
    state = _run(tmp_path, OFFLINE_STACK + ("output_forge",))
    forge = state["modules"]["output_forge"]
    produced = {a["format"] for a in forge["artifacts"]}
    assert "html" in produced
    assert "interactive_html" not in produced


def test_interactive_renders_when_requested(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    brand = load_brand(BRAND_FILE)
    out_dir = tmp_path / "out"
    output_forge(
        state, out_dir=out_dir, brand=brand, formats=("html", "interactive_html")
    )
    forge = state["modules"]["output_forge"]
    arts = {a["format"]: a for a in forge["artifacts"]}
    assert "interactive_html" in arts
    art = arts["interactive_html"]
    assert art["filename"] == "dashboard.interactive.html"
    assert len(art["sha256"]) == 64 and art["bytes"] > 0
    assert (out_dir / "dashboard.interactive.html").is_file()
    assert forge["backends"].get("plotly") is True


def test_interactive_skipped_when_bundle_absent(tmp_path: Path, monkeypatch) -> None:
    # Simulate a checkout without the vendored bundle: the format is skipped, not
    # failed, and the always-available HTML still renders.
    # The package re-exports the output_forge function under the same dotted name,
    # so reach the module object through sys.modules to patch the global the
    # renderer reads.
    forge_module = sys.modules["modules.output_forge"]
    monkeypatch.setattr(forge_module, "interactive_available", lambda: False)
    state = _run(tmp_path, OFFLINE_STACK)
    brand = load_brand(BRAND_FILE)
    out_dir = tmp_path / "out"
    output_forge(
        state, out_dir=out_dir, brand=brand, formats=("html", "interactive_html")
    )
    forge = state["modules"]["output_forge"]
    produced = {a["format"] for a in forge["artifacts"]}
    skipped = {s["format"] for s in forge["skipped"]}
    assert "html" in produced
    assert "interactive_html" in skipped
    assert forge["backends"].get("plotly") is False
    assert not (out_dir / "dashboard.interactive.html").exists()
