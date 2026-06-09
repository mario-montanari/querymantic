#!/usr/bin/env python3
"""Regression tests added after the full audit.

They lock the fixes that closed the audit findings: the OOXML core-date pinning that
makes the xlsx byte-deterministic (verified without an Office backend, by exercising
the port directly), the HTML escaping of hostile labels, and the input-validation
error paths that several modules gained (missing run timestamp, an STL period below a
cycle, missing measured clicks, an unknown module, malformed brand input).
"""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"


# --- determinism: the OOXML core-date pinning (backend-free) -----------------


def _zip_with_core(modified: str, created: str) -> bytes:
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="x" xmlns:dcterms="y" xmlns:xsi="z">'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>'
        "</cp:coreProperties>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("docProps/core.xml", core)
        z.writestr("[Content_Types].xml", "<Types/>")
    return buffer.getvalue()


def test_normalize_zip_pins_core_dates(tmp_path: Path) -> None:
    # openpyxl overwrites the modified date with the wall clock at save; the port must
    # rewrite it to the pinned run timestamp so two renders never differ on the date.
    from querymantic.ports import ooxml

    path = tmp_path / "doc.xlsx"
    path.write_bytes(_zip_with_core("2031-09-09T12:34:56Z", "2031-09-09T12:34:56Z"))
    ts = datetime(2026, 6, 8, 0, 0, 0, tzinfo=timezone.utc)
    ooxml.normalize_zip(path, core_timestamp=ts)
    core = zipfile.ZipFile(io.BytesIO(path.read_bytes())).read("docProps/core.xml")
    text = core.decode("utf-8")
    assert "2026-06-08T00:00:00Z" in text
    assert "2031-09-09T12:34:56Z" not in text


def test_normalize_zip_without_timestamp_leaves_dates(tmp_path: Path) -> None:
    # When no timestamp is passed the port only normalises member metadata, not the
    # core dates, so the call stays backward-compatible.
    from querymantic.ports import ooxml

    path = tmp_path / "doc.xlsx"
    path.write_bytes(_zip_with_core("2031-09-09T12:34:56Z", "2031-09-09T12:34:56Z"))
    ooxml.normalize_zip(path)
    text = zipfile.ZipFile(io.BytesIO(path.read_bytes())).read("docProps/core.xml")
    assert b"2031-09-09T12:34:56Z" in text


# --- HTML escaping of a hostile label ----------------------------------------


def test_html_dashboard_escapes_hostile_label(tmp_path: Path) -> None:
    from modules.output_forge.brand import resolve_brand
    from modules.output_forge.dashboard_html import render_html
    from modules.output_forge.model import build_view
    from querymantic import pipeline

    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp_path / "run.json",
        modules_to_run=("entity_web", "fan_out_radar", "citation_grid", "click_ceiling"),
        generated_at=FIXED_TIMESTAMP,
    )
    view = build_view(state)
    hostile = "<script>alert(1)</script>"
    view["corpus"]["intent_split"][0]["intent"] = hostile
    if view["top_clusters"]:
        view["top_clusters"][0]["head"] = hostile
    html = render_html(view, resolve_brand(None)).decode("utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# --- input-validation error paths --------------------------------------------


def test_demand_pulse_rejects_stl_period_below_two() -> None:
    from modules.demand_pulse import ModuleError, _config

    with pytest.raises(ModuleError):
        _config({"stl_period": 1})


def test_demand_pulse_rejects_zero_momentum_window() -> None:
    from modules.demand_pulse import ModuleError, _config

    with pytest.raises(ModuleError):
        _config({"momentum_window": 0})


def test_live_wire_rejects_missing_clicks() -> None:
    from modules.live_wire import LiveWireError, _parse_search_console

    block = {"rows": [{"query": "running shoes", "impressions": 100}]}
    with pytest.raises(LiveWireError):
        _parse_search_console(block, Path("capture.json"))


def test_live_wire_keeps_a_real_zero() -> None:
    # A measured zero must survive, unlike a missing field, which raises above.
    from modules.live_wire import _parse_search_console

    block = {"rows": [{"query": "x", "clicks": 0, "impressions": 0}]}
    parsed = _parse_search_console(block, Path("capture.json"))
    assert parsed["rows"][0]["clicks"] == 0.0


def test_fan_out_requires_generated_at() -> None:
    from modules.fan_out_radar import ModuleError, _reference_year

    with pytest.raises(ModuleError):
        _reference_year({"querymantic": {"generated_at": ""}})


def test_reference_year_reads_the_stamp() -> None:
    from modules.fan_out_radar import _reference_year

    assert _reference_year({"querymantic": {"generated_at": FIXED_TIMESTAMP}}) == 2026


def test_pipeline_rejects_unknown_module(tmp_path: Path) -> None:
    from querymantic.pipeline import PipelineError, run_pipeline

    with pytest.raises(PipelineError):
        run_pipeline(
            PLUGIN_ROOT,
            [SAMPLES],
            tmp_path / "run.json",
            modules_to_run=("no_such_module",),
            generated_at=FIXED_TIMESTAMP,
        )


def test_load_brand_rejects_bad_json(tmp_path: Path) -> None:
    from modules.output_forge.brand import BrandError, load_brand

    bad = tmp_path / "brand.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(BrandError):
        load_brand(bad)


def test_brand_rejects_bad_hex() -> None:
    from modules.output_forge.brand import BrandError, resolve_brand

    with pytest.raises(BrandError):
        resolve_brand({"name": "Acme", "colors": {"primary": '"/><script>'}})


def test_brand_resolution_is_idempotent() -> None:
    from modules.output_forge.brand import resolve_brand

    once = resolve_brand({"name": "Acme", "colors": {"primary": "#ABCDEF"}})
    twice = resolve_brand(once)
    assert once == twice


# --- loader error paths ------------------------------------------------------


def test_load_series_rejects_missing_file(tmp_path: Path) -> None:
    from modules.demand_pulse import DemandPulseError, load_series

    with pytest.raises(DemandPulseError):
        load_series(tmp_path / "no_such_series.csv")


def test_load_ctr_table_rejects_missing_file(tmp_path: Path) -> None:
    from modules.click_ceiling import ModuleError, load_ctr_table

    with pytest.raises(ModuleError):
        load_ctr_table(tmp_path / "no_such_table.json")


def test_load_gazetteer_rejects_missing_file(tmp_path: Path) -> None:
    from modules.language_layer import LanguageLayerError, load_gazetteer

    with pytest.raises(LanguageLayerError):
        load_gazetteer(tmp_path / "no_such_gazetteer.json")
