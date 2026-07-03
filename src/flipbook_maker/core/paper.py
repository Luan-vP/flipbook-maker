from __future__ import annotations

PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}

A4_MM = PAPER_SIZES_MM["a4"]

# Fixed cell sizes for special "print at actual size" layouts, keyed by a
# short preset name. `filter-tip` is a standard single/King-size rolling-paper
# filter tip card (44 x 68mm) — verify against your actual tip brand before
# relying on it for a precise cut.
FRAME_SIZE_PRESETS_MM: dict[str, tuple[float, float]] = {
    "filter-tip": (44.0, 68.0),
}


def resolve_page_mm(paper: str, landscape: bool = False) -> tuple[float, float]:
    """Return (width_mm, height_mm) for a paper preset, swapped if landscape."""
    w_mm, h_mm = PAPER_SIZES_MM[paper]
    return (h_mm, w_mm) if landscape else (w_mm, h_mm)


def grid_for_frame_size(
    page_mm: tuple[float, float], margin_mm: float, frame_mm: tuple[float, float]
) -> tuple[int, int]:
    """Max (cols, rows) of frame_mm-sized cells that fit on page_mm with margin_mm."""
    usable_w = page_mm[0] - 2 * margin_mm
    usable_h = page_mm[1] - 2 * margin_mm
    cols = max(1, int(usable_w // frame_mm[0]))
    rows = max(1, int(usable_h // frame_mm[1]))
    return cols, rows
