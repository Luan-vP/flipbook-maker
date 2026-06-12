from __future__ import annotations


def mm_to_px(mm: float, dpi: int) -> int:
    """Convert millimetres to whole pixels at the given DPI."""
    return int(round(mm * dpi / 25.4))
