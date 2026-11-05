"""Attack autopsy — delegates to the canonical engine implementation.

core/autopsy.py is the source of truth (vendored to
elcaro_engine/autopsy.py); this shim keeps `from . import autopsy`
working for guard/tools without duplicating the logic.
"""

from .elcaro_engine.autopsy import summarize

__all__ = ["summarize"]
