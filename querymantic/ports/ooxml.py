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
metadata (the core-properties created and modified dates) varies the same way.
``normalize_zip`` rewrites a produced archive with a fixed member timestamp and a
stable member order, so that once the generators pin the core-properties dates to
the run timestamp, the whole file is byte-reproducible across runs.

Note on cross-environment reproducibility: byte-equality holds across runs in the
same environment with the same backend versions. A different ``python-pptx`` or
``openpyxl`` version can serialise the same content differently; that is the
package's behaviour, not the port's, and it is recorded as a known limitation.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

# The earliest timestamp the ZIP format can represent. Using it as the fixed
# member time is the conventional choice for reproducible archives.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


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


def normalize_zip(path: Path) -> None:
    """Rewrite an OOXML archive in place with deterministic member metadata.

    Each member keeps its name, content, compression type, and external
    attributes, but its modification time is pinned to the ZIP epoch and the
    members are written in sorted name order. Combined with the generators pinning
    the core-properties dates, this makes the output byte-reproducible across two
    runs on the same input in the same environment.

    The function reads the whole archive into memory, which is appropriate for the
    report-sized documents Output Forge produces.
    """
    with zipfile.ZipFile(path, "r") as src:
        members = [(info, src.read(info.filename)) for info in src.infolist()]

    members.sort(key=lambda item: item[0].filename)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as dst:
        for info, data in members:
            pinned = zipfile.ZipInfo(filename=info.filename, date_time=_ZIP_EPOCH)
            pinned.compress_type = info.compress_type
            pinned.external_attr = info.external_attr
            pinned.internal_attr = info.internal_attr
            pinned.create_system = 0  # MS-DOS, fixed so the host OS does not leak in
            dst.writestr(pinned, data)

    path.write_bytes(buffer.getvalue())
