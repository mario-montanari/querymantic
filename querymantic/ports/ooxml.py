#!/usr/bin/env python3
"""OOXML port: Office document backends with a degrading optional dependency.

Output Forge writes four artifacts. The HTML dashboard is pure standard library
and always available; the three Office formats sit behind third-party packages
that are optional by the tiered dependency budget:

- ``.pptx`` via ``python-pptx``
- ``.docx`` via ``python-docx``
- ``.xlsx`` via ``openpyxl``

This port centralises the availability check so a renderer can ask once and skip
its format cleanly when the backend is missing, rather than raising on import.
Callers consult ``ooxml_capabilities()`` first.

It also carries the determinism helper the Office formats need. An OOXML file is a
ZIP archive, and ``zipfile`` stamps each member with the current local time by
default, so two runs of the same content would differ byte for byte. The package
metadata (the core-properties created and modified dates) varies the same way, and a
backend may even overwrite the date the renderer sets (openpyxl stamps ``modified``
with the wall clock at save time). ``normalize_zip`` rewrites a produced archive with
a fixed member timestamp, a stable member order, and the core-properties dates pinned
to the run timestamp, so the whole file is byte-reproducible across runs.

Note on cross-environment reproducibility: byte-equality holds across runs in the
same environment with the same backend versions. A different ``python-pptx`` or
``openpyxl`` version can serialise the same content differently; that is the
package's behaviour, not the port's, and it is recorded as a known limitation.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# The earliest timestamp the ZIP format can represent. Using it as the fixed
# member time is the conventional choice for reproducible archives.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# The OOXML core-properties part and the two date elements a backend may stamp. The
# namespace prefix is matched generically (any prefix, or none) so a backend that does
# not use the literal ``dcterms:`` prefix is still pinned rather than silently skipped.
# The backreferences on the prefix and the element name keep the closing tag matched to
# its opening tag, so a created/modified pair can never be crossed.
_CORE_PART = "docProps/core.xml"
_CORE_DATE_RE = re.compile(
    r"(<((?:[\w.-]+:)?)(created|modified)\b[^>]*>)[^<]*(</\2\3>)"
)


class OoxmlError(Exception):
    """Raised when an OOXML archive cannot be normalised deterministically."""


def _w3cdtf(ts: datetime) -> str:
    """Format a datetime as the W3CDTF string OOXML core properties use (UTC, ``Z``)."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pin_core_dates(data: bytes, ts: datetime) -> bytes:
    """Rewrite the created/modified dates in a ``core.xml`` payload to ``ts``.

    Some backends (openpyxl overwrites ``modified`` with the wall clock at save time)
    ignore the date the renderer sets, which would make the archive non-reproducible.
    Pinning the element text here covers every backend uniformly.

    Raises ``OoxmlError`` if the core-properties part carries no date element to pin:
    a silent no-op would let a wall-clock date survive and quietly break determinism,
    which is exactly the failure this pinning exists to prevent.
    """
    stamp = _w3cdtf(ts)
    pinned, count = _CORE_DATE_RE.subn(rf"\g<1>{stamp}\g<4>", data.decode("utf-8"))
    if count == 0:
        raise OoxmlError(
            "core.xml has no created/modified date to pin; the wall clock would "
            "survive and break byte-reproducibility"
        )
    return pinned.encode("utf-8")


def _present(module_name: str) -> bool:
    """Return True if an optional backend imports, without keeping it loaded."""
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


def ooxml_capabilities() -> dict[str, bool]:
    """Return which Office backends are importable in this environment.

    Keys are the Output Forge format names; the HTML dashboard is not listed here
    because it needs no optional backend and is always produced.
    """
    return {
        "pptx": _present("pptx"),
        "docx": _present("docx"),
        "xlsx": _present("openpyxl"),
    }


def normalize_zip(path: Path, core_timestamp: datetime | None = None) -> None:
    """Rewrite an OOXML archive in place with deterministic member metadata.

    Each member keeps its name, content, compression type, and external
    attributes, but its modification time is pinned to the ZIP epoch and the
    members are written in sorted name order. When ``core_timestamp`` is given, the
    created and modified dates inside ``docProps/core.xml`` are pinned to it as well,
    so a backend that stamps the wall clock (openpyxl does this for ``modified``)
    cannot make the file vary between runs. Together this makes the output
    byte-reproducible across two runs on the same input in the same environment.

    The function reads the whole archive into memory, which is appropriate for the
    report-sized documents Output Forge produces.
    """
    with zipfile.ZipFile(path, "r") as src:
        members = [(info, src.read(info.filename)) for info in src.infolist()]

    members.sort(key=lambda item: item[0].filename)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as dst:
        for info, data in members:
            if core_timestamp is not None and info.filename == _CORE_PART:
                data = _pin_core_dates(data, core_timestamp)
            pinned = zipfile.ZipInfo(filename=info.filename, date_time=_ZIP_EPOCH)
            pinned.compress_type = info.compress_type
            pinned.external_attr = info.external_attr
            pinned.internal_attr = info.internal_attr
            pinned.create_system = 0  # MS-DOS, fixed so the host OS does not leak in
            dst.writestr(pinned, data)

    path.write_bytes(buffer.getvalue())
