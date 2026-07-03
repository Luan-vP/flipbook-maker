"""Shared print substrate: units, paper geometry, and PDF/PNG output.

These helpers are renderer-agnostic — both the flipbook and tarot namespaces
build on them, and they are what an eventual standalone zine-utils library
would carry.
"""
from __future__ import annotations

from flipbook_maker.core.io import save_pages, save_pdf
from flipbook_maker.core.paper import (
    A4_MM,
    FRAME_SIZE_PRESETS_MM,
    PAPER_SIZES_MM,
    grid_for_frame_size,
    resolve_page_mm,
)
from flipbook_maker.core.units import mm_to_px

__all__ = [
    "mm_to_px",
    "PAPER_SIZES_MM",
    "FRAME_SIZE_PRESETS_MM",
    "A4_MM",
    "resolve_page_mm",
    "grid_for_frame_size",
    "save_pages",
    "save_pdf",
]
