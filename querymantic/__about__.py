"""Single source of truth for the product identity.

Every user-facing place that names the product (the Output Forge brand defaults,
report headers, document authorship) reads from here, so the display name and
tagline change in one file. Structural identifiers that cannot live in a Python
constant (the plugin name in ``.claude-plugin/plugin.json``, the import package
name, the future PyPI distribution name) each have their own single canonical
home and are not duplicated here.
"""

from __future__ import annotations

PRODUCT_NAME = "Querymantic"
TAGLINE = "Offline keyword and demand intelligence"
__version__ = "0.2.0"
