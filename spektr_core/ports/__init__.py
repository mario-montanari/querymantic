"""Ports: thin adapters to optional third-party libraries.

A port wraps one optional dependency behind a small interface and degrades when
the library is absent, so the suite never hard-fails on a missing optional
package. The tiered dependency budget keeps the core and the vendored engine
stdlib-only; ports are where optional libraries enter.

Planned ports (added in the sprint that first needs them):

- ``ooxml``: python-pptx, python-docx, openpyxl for Output Forge.
- ``stats``: statsmodels STL for Demand Pulse, degrading to a stdlib trend test.
- ``graph``: networkx for Entity Web, degrading to a stdlib graph.
"""

from __future__ import annotations

__all__: list[str] = []
