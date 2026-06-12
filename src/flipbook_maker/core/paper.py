from __future__ import annotations

PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}

A4_MM = PAPER_SIZES_MM["a4"]


def resolve_page_mm(paper: str, landscape: bool = False) -> tuple[float, float]:
    """Return (width_mm, height_mm) for a paper preset, swapped if landscape."""
    w_mm, h_mm = PAPER_SIZES_MM[paper]
    return (h_mm, w_mm) if landscape else (w_mm, h_mm)
