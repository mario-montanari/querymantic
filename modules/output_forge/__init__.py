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
from datetime import datetime
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

    Normalises a single trailing ``Z`` (Zulu/UTC) to ``+00:00`` before parsing,
    because ``datetime.fromisoformat`` rejects the ``Z`` suffix before Python 3.11.
    Without this, the same pinned timestamp parsed on Python 3.10 (a supported
    platform) and on 3.11+ would disagree, so the document dates, and therefore the
    rendered bytes, would differ between supported Pythons.

    Parsing is strict and identical across versions. After normalising the one
    trailing Zulu marker, no ``Z`` may remain: a malformed value like ``...ZZ`` is
    rejected on every supported Python, rather than parsing on 3.10 (which is lenient
    about a stray ``Z``) and failing on 3.11+. An unparsable or empty value raises
    rather than falling back silently: a pinned timestamp the run-state could not
    honour must surface, not be replaced by an invented date that would put the wrong
    year on every delivered document.
    """
    text = (value or "").strip()
    if not text:
        raise OutputForgeError(
            "run-state has no 'generated_at' timestamp to pin the documents to"
        )
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    if "z" in text.lower():
        # A second Zulu marker survived the single-suffix normalisation above, so the
        # value is malformed. Reject it here so 3.10 cannot accept what 3.11+ refuses.
        raise OutputForgeError(
            f"'generated_at' is not a valid ISO 8601 timestamp: {value!r}"
        )
    try:
        return datetime.fromisoformat(text)
    except (ValueError, TypeError) as exc:
        raise OutputForgeError(
            f"'generated_at' is not a valid ISO 8601 timestamp: {value!r}"
        ) from exc


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
    # The produced archive is normalised so two runs are byte-identical. Passing the
    # pinned timestamp also re-stamps the core-properties dates, which a backend may
    # otherwise overwrite with the wall clock (openpyxl does this for ``modified``).
    ooxml.normalize_zip(out_path, core_timestamp=ts)


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
        # Always resolve, even when the caller passes a pre-resolved brand. resolve_brand
        # is idempotent, so this costs nothing, and it guarantees every colour is
        # re-validated as strict hex before it reaches a raw SVG/CSS attribute. Trusting
        # a caller-built dict here was the one path by which an unescaped colour could
        # have been injected.
        resolved_brand = resolve_brand(brand)
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
            except (ImportError, ModuleNotFoundError) as exc:
                # The optional backend (or a part of it) is not importable after all:
                # skip this format and keep the rest, the same as an absent backend.
                skipped.append(
                    {
                        "format": fmt,
                        "reason": f"backend not importable ({backend}): {exc}",
                    }
                )
                continue
            except Exception as exc:
                # A genuine rendering error is NOT a missing backend; surfacing it keeps a
                # real defect from hiding as a silent skip with an obscure reason.
                raise OutputForgeError(f"failed to render {fmt}: {exc}") from exc
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


__all__ = ["output_forge", "ModuleError", "OutputForgeError", "FORMATS"]
