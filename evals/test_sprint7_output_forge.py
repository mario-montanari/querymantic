#!/usr/bin/env python3
"""Sprint 7 tests: the Output Forge module.

Covers the brand resolver and its hex validation, the shared view (including Live
Wire's observed values folded in), the self-contained HTML dashboard (no external
resource, deterministic bytes), the manifest contract, capability-aware handling of
the Office formats (rendered when a backend is present, skipped with a reason when
absent), the archive-normalisation determinism helper, and end-to-end determinism of
the output_forge slot across two runs.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from modules.live_wire import load_capture  # noqa: E402
from modules.output_forge import OutputForgeError, output_forge  # noqa: E402
from modules.output_forge.brand import (
    BrandError,
    brand_fingerprint,
    load_brand,
    resolve_brand,
)  # noqa: E402
from modules.output_forge.dashboard_html import render_html  # noqa: E402
from modules.output_forge.model import build_view  # noqa: E402
from spektr_core import pipeline, run_state  # noqa: E402
from spektr_core.ports import ooxml  # noqa: E402

SAMPLES = PLUGIN_ROOT / "assets" / "samples"
SAMPLE_CAPTURE = PLUGIN_ROOT / "assets" / "livewire" / "sample_capture.json"
BRAND_FILE = PLUGIN_ROOT / "forge" / "templates" / "brand.json"
FIXED_TIMESTAMP = "2026-06-08T00:00:00+00:00"
OFFLINE_STACK = ("entity_web", "fan_out_radar", "citation_grid", "click_ceiling")


def _run(tmp: Path, modules: tuple[str, ...], with_capture: bool = False) -> dict:
    kwargs: dict = {}
    if "output_forge" in modules:
        kwargs["output_forge"] = {
            "out_dir": tmp / "forge",
            "brand": load_brand(BRAND_FILE),
        }
    if "live_wire" in modules and with_capture:
        kwargs["live_wire"] = {"capture": load_capture(SAMPLE_CAPTURE)}
    return pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp / "run.json",
        modules_to_run=modules,
        generated_at=FIXED_TIMESTAMP,
        module_kwargs=kwargs,
    )


# --- brand ------------------------------------------------------------------


def test_brand_defaults_and_merge() -> None:
    default = resolve_brand(None)
    assert default["name"] == "Spektr"
    assert default["colors"]["primary"].startswith("#")
    merged = resolve_brand({"name": "Acme SEO", "colors": {"primary": "#102030"}})
    assert merged["name"] == "Acme SEO"
    assert merged["colors"]["primary"] == "#102030"
    # Author falls back to the brand name when not given.
    assert merged["author"] == "Acme SEO"
    # An untouched colour keeps its default.
    assert merged["colors"]["accent"] == default["colors"]["accent"]


def test_brand_rejects_bad_hex() -> None:
    with pytest.raises(BrandError):
        resolve_brand({"colors": {"primary": "navy"}})


def test_brand_fingerprint_is_stable() -> None:
    a = brand_fingerprint(resolve_brand({"name": "X"}))
    b = brand_fingerprint(resolve_brand({"name": "X"}))
    assert a == b and len(a) == 12


# --- the shared view --------------------------------------------------------


def test_view_has_sections(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    view = build_view(state)
    assert view["corpus"]["total_keywords"] == 170
    assert view["clusters"], "clusters should be present"
    assert view["winnable"] is not None
    assert view["readiness"] is not None
    assert view["gaps"], "entity gaps should be present"
    # Clusters are ordered by demand, descending.
    vols = [c.get("volume_total") or 0 for c in view["clusters"]]
    assert vols == sorted(vols, reverse=True)
    # No observed block without Live Wire.
    assert view["observed"] is None


def test_view_folds_in_observed(tmp_path: Path) -> None:
    state = _run(
        tmp_path, OFFLINE_STACK + ("live_wire", "output_forge"), with_capture=True
    )
    view = build_view(state)
    assert view["observed"] is not None
    assert view["observed"]["observed_citation_share"] > 0
    # At least one cluster carries an observed value beside the expected one.
    assert any("observed_current_clicks" in c for c in view["clusters"])
    assert "observed_current_clicks" in (view["winnable"] or {})


# --- the HTML dashboard -----------------------------------------------------


def test_html_is_self_contained(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    html = render_html(build_view(state), resolve_brand(None)).decode("utf-8")
    assert html.startswith("<!DOCTYPE html>")
    # No external resource of any kind.
    for needle in ("http://", "https://", "<script", "cdn", "src="):
        assert needle not in html.lower(), f"unexpected external reference: {needle}"
    # Charts are inline SVG.
    assert "<svg" in html
    # Key sections render.
    for section in ("Demand overview", "Winnable clicks", "Clusters by demand"):
        assert section in html


def test_html_is_deterministic(tmp_path: Path) -> None:
    state = _run(tmp_path, OFFLINE_STACK)
    view = build_view(state)
    brand = resolve_brand(None)
    assert render_html(view, brand) == render_html(view, brand)


# --- the manifest and degradation -------------------------------------------


def test_output_forge_contract(tmp_path: Path) -> None:
    _run(tmp_path, OFFLINE_STACK + ("output_forge",))
    loaded = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(loaded)
    assert loaded["spektr"]["modules_run"][-1] == "output_forge"

    forge = loaded["modules"]["output_forge"]
    assert forge["mode"] == "render"
    assert forge["generated_at"] == FIXED_TIMESTAMP
    assert set(forge["backends"]) == {"pptx", "docx", "xlsx"}
    assert forge["brand"]["name"] == "Spektr"
    assert len(forge["brand"]["fingerprint"]) == 12

    produced = {a["format"] for a in forge["artifacts"]}
    skipped = {s["format"] for s in forge["skipped"]}
    # HTML is always produced and carries a digest.
    assert "html" in produced
    html_art = next(a for a in forge["artifacts"] if a["format"] == "html")
    assert len(html_art["sha256"]) == 64 and html_art["bytes"] > 0
    # The dashboard file actually exists on disk.
    assert (tmp_path / "forge" / "dashboard.html").is_file()
    # Each Office format is either produced (backend present) or skipped (absent).
    caps = forge["backends"]
    for fmt, backend in (("pptx", "pptx"), ("docx", "docx"), ("xlsx", "xlsx")):
        if caps[backend]:
            assert fmt in produced
        else:
            assert fmt in skipped


def test_output_forge_rejects_unknown_format(tmp_path: Path) -> None:
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp_path / "run.json",
        modules_to_run=(),
        generated_at=FIXED_TIMESTAMP,
    )
    with pytest.raises(OutputForgeError):
        output_forge(state, out_dir=tmp_path / "forge", formats=("html", "pdf"))


def test_html_only_skips_nothing(tmp_path: Path) -> None:
    state = pipeline.run_pipeline(
        PLUGIN_ROOT,
        [SAMPLES],
        tmp_path / "run.json",
        modules_to_run=(),
        generated_at=FIXED_TIMESTAMP,
    )
    output_forge(state, out_dir=tmp_path / "forge", formats=("html",))
    forge = state["modules"]["output_forge"]
    assert forge["skipped"] == []
    assert [a["format"] for a in forge["artifacts"]] == ["html"]


# --- the archive-normalisation determinism helper ---------------------------


def test_normalize_zip_makes_archives_byte_identical(tmp_path: Path) -> None:
    def make(path: Path, order: list[str]) -> None:
        with zipfile.ZipFile(path, "w") as z:
            for name in order:
                info = zipfile.ZipInfo(name, date_time=(2021, 5, 5, 5, 5, 5))
                z.writestr(info, b"content-of-" + name.encode())

    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    make(a, ["b.xml", "a.xml", "c.xml"])
    make(b, ["c.xml", "a.xml", "b.xml"])
    assert a.read_bytes() != b.read_bytes()  # member order and time differ
    ooxml.normalize_zip(a)
    ooxml.normalize_zip(b)
    assert a.read_bytes() == b.read_bytes()


def test_ooxml_capabilities_shape() -> None:
    caps = ooxml.ooxml_capabilities()
    assert set(caps) == {"pptx", "docx", "xlsx"}
    assert all(isinstance(v, bool) for v in caps.values())


# --- end-to-end determinism -------------------------------------------------


def test_forge_renders_from_existing_run(tmp_path: Path) -> None:
    # The `forge` subcommand path: a saved run is loaded, rendered, marked, re-saved.
    _run(tmp_path, OFFLINE_STACK)
    loaded = run_state.load_run_state(tmp_path / "run.json")
    assert "output_forge" not in loaded["spektr"]["modules_run"]
    output_forge(loaded, out_dir=tmp_path / "forge", brand=load_brand(BRAND_FILE))
    run_state.mark_module_run(loaded, "output_forge")
    run_state.save_run_state(loaded, tmp_path / "run.json")
    again = run_state.load_run_state(tmp_path / "run.json")
    run_state.validate_run_state(again)
    assert "output_forge" in again["spektr"]["modules_run"]
    assert (tmp_path / "forge" / "dashboard.html").is_file()


def test_output_forge_deterministic(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", OFFLINE_STACK + ("output_forge",))
    b = _run(tmp_path / "b", OFFLINE_STACK + ("output_forge",))
    # The whole manifest is byte-stable, including every artifact digest.
    assert a["modules"]["output_forge"] == b["modules"]["output_forge"]
    # And the HTML file bytes match.
    assert (tmp_path / "a" / "forge" / "dashboard.html").read_bytes() == (
        tmp_path / "b" / "forge" / "dashboard.html"
    ).read_bytes()
