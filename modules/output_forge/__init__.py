#!/usr/bin/env python3
"""Output Forge: one run-state to a set of branded artifacts.

The last module in the suite. It reads the finished run-state and renders it into
deliverables: a self-contained HTML dashboard (always), and a slide deck, a Word
audit, and an Excel workbook when their optional Office backends are installed. A
white-label ``brand.json`` drives the look and the authorship of all of them.

Like every Querymantic module it is a pure step ``run_state -> run_state'``: its visible
effect is the files it writes to ``out_dir``, but in the run-state it only fills its
own ``output_forge`` slot with a manifest, listing each artifact with its size and
SHA-256, the brand fingerprint, the available backends, and any format skipped for a
missing backend. The manifest carries no absolute path, so the run-state stays
portable, and it is byte-stable across two runs on the same input because every
renderer is deterministic and all timestamps are pinned to the run timestamp.

The four renderers share one normalised view (``model.build_view``), so a figure is
computed once and never disagrees between formats. The view already folds in Live
Wire's observed values where present, so the deliverables show observed beside
expected without recomputing anything.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from querymantic.ports import ooxml

from . import model
from .brand import BrandError, brand_fingerprint, resolve_brand
from .dashboard_html import render_html
from .dashboard_interactive import interactive_available, render_interactive_html

# The formats the module can produce, and the fixed filename for each. Fixed names
# keep the manifest and the on-disk output deterministic. ``interactive_html`` is
# opt-in only (it is never in the default ``formats`` tuple): it mounts interactive
# Plotly charts from the vendored bundle, while ``html`` stays the script-free,
# always-available SVG floor.
FORMATS: dict[str, str] = {
    "html": "dashboard.html",
    "interactive_html": "dashboard.interactive.html",
    "pptx": "deck.pptx",
    "docx": "audit.docx",
    "xlsx": "dashboard.xlsx",
}

# Which optional backend each Office format needs, by its capability key.
_OOXML_FORMATS = {"pptx": "pptx", "docx": "docx", "xlsx": "xlsx"}


class ModuleError(Exception):
    """Raised when Output Forge cannot run against the current run-state."""


class OutputForgeError(Exception):
    """Raised on a bad brand config, an unknown format, or a write failure."""


def _parse_timestamp(value: str) -> datetime:
    """Parse the pinned run timestamp for the Office core properties.

    Falls back to the ZIP epoch rather than the wall clock, so a malformed or empty
    timestamp never makes the output non-deterministic.
    """
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime(1980, 1, 1, tzinfo=timezone.utc)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_ooxml(
    fmt: str, view: dict[str, Any], brand: dict[str, Any], out_path: Path, ts: datetime
) -> None:
    if fmt == "pptx":
        from .deck import render_deck

        render_deck(view, brand, out_path, ts)
    elif fmt == "docx":
        from .audit_docx import render_audit

        render_audit(view, brand, out_path, ts)
    elif fmt == "xlsx":
        from .dashboard_xlsx import render_workbook

        render_workbook(view, brand, out_path, ts)
    # The produced archive is normalised so two runs are byte-identical.
    ooxml.normalize_zip(out_path)


def output_forge(
    state: dict[str, Any],
    out_dir: Path | str | None = None,
    brand: dict[str, Any] | None = None,
    formats: tuple[str, ...] = ("html", "pptx", "docx", "xlsx"),
) -> dict[str, Any]:
    """Render the run-state into artifacts and write the Output Forge manifest.

    ``out_dir`` is where the files are written (created if missing). ``brand`` is a
    resolved brand mapping (see ``brand.resolve_brand``); ``None`` uses the neutral
    default. ``formats`` lists the desired formats; an Office format whose backend is
    absent is skipped and recorded, never an error. HTML is always produced.
    """
    if out_dir is None:
        raise ModuleError("output_forge needs an out_dir to write artifacts into")
    out_path_dir = Path(out_dir)

    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        raise OutputForgeError(
            f"unknown output format(s): {', '.join(sorted(unknown))}"
        )

    engine = state.get("engine")
    if not isinstance(engine, dict) or not engine.get("clusters"):
        raise ModuleError("output_forge needs the engine analysis with clusters")

    try:
        resolved_brand = resolve_brand(brand) if not _is_resolved(brand) else brand
    except BrandError as exc:
        raise OutputForgeError(str(exc)) from exc

    view = model.build_view(state)
    ts = _parse_timestamp(state.get("querymantic", {}).get("generated_at", ""))
    capabilities = {**ooxml.ooxml_capabilities(), "plotly": interactive_available()}

    out_path_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    # Render in a fixed order so the manifest is stable regardless of the caller's.
    for fmt in ("html", "interactive_html", "pptx", "docx", "xlsx"):
        if fmt not in formats:
            continue
        out_file = out_path_dir / FORMATS[fmt]
        if fmt == "html":
            out_file.write_bytes(render_html(view, resolved_brand))
        elif fmt == "interactive_html":
            if not interactive_available():
                skipped.append(
                    {
                        "format": fmt,
                        "reason": "vendored plotly.js bundle not present (vendor/plotly/)",
                    }
                )
                continue
            out_file.write_bytes(render_interactive_html(view, resolved_brand))
        else:
            backend = _OOXML_FORMATS[fmt]
            if not capabilities.get(backend, False):
                skipped.append(
                    {"format": fmt, "reason": f"backend not installed ({backend})"}
                )
                continue
            try:
                _render_ooxml(fmt, view, resolved_brand, out_file, ts)
            except Exception as exc:  # a backend failure must not lose the rest
                skipped.append(
                    {"format": fmt, "reason": f"{type(exc).__name__}: {exc}"}
                )
                continue
        artifacts.append(
            {
                "format": fmt,
                "filename": FORMATS[fmt],
                "bytes": out_file.stat().st_size,
                "sha256": _sha256_of(out_file),
            }
        )

    state["modules"]["output_forge"] = {
        "mode": "render",
        "generated_at": state.get("querymantic", {}).get("generated_at", ""),
        "brand": {
            "name": resolved_brand["name"],
            "fingerprint": brand_fingerprint(resolved_brand),
        },
        "backends": capabilities,
        "formats_requested": sorted(formats),
        "artifacts": artifacts,
        "skipped": skipped,
        "method_note": (
            "Output Forge renders the finished run-state into deliverables and records "
            "each artifact's SHA-256. The HTML dashboard is self-contained and needs no "
            "backend; the Office formats need their optional packages and are skipped, "
            "not failed, when a backend is absent. All timestamps are pinned to the run "
            "timestamp so a re-run on the same input reproduces the same bytes."
        ),
    }
    return state


def _is_resolved(brand: dict[str, Any] | None) -> bool:
    """True when ``brand`` is already a resolved brand mapping (has a colours block)."""
    return (
        isinstance(brand, dict)
        and isinstance(brand.get("colors"), dict)
        and "primary" in brand["colors"]
    )


__all__ = ["output_forge", "ModuleError", "OutputForgeError", "FORMATS"]
