from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor

PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}

A4_MM = PAPER_SIZES_MM["a4"]


def _mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / 25.4))


@dataclass(frozen=True)
class LayoutConfig:
    cols: int = 2
    rows: int = 8
    dpi: int = 300
    margin_mm: float = 5.0
    background: str | Path = "white"
    page_size_mm: tuple[float, float] = A4_MM

    def page_px(self) -> tuple[int, int]:
        return _mm_to_px(self.page_size_mm[0], self.dpi), _mm_to_px(self.page_size_mm[1], self.dpi)

    def margin_px(self) -> int:
        return _mm_to_px(self.margin_mm, self.dpi)

    def cell_px(self) -> tuple[int, int]:
        w, h = self.page_px()
        m = self.margin_px()
        return (w - 2 * m) // self.cols, (h - 2 * m) // self.rows


def _load_background(spec: str | Path, size: tuple[int, int]) -> Image.Image:
    spec_path = Path(spec) if not isinstance(spec, Path) else spec
    if spec_path.exists() and spec_path.is_file():
        bg = Image.open(spec_path).convert("RGB")
        return bg.resize(size, Image.LANCZOS)
    try:
        rgb = ImageColor.getrgb(str(spec))
    except ValueError as e:
        msg = f"background must be a color name/hex or an image path, got: {spec!r}"
        raise ValueError(msg) from e
    return Image.new("RGB", size, rgb)


def _place_in_cell(cell: Image.Image, frame: Image.Image) -> None:
    cw, ch = cell.size
    fw, fh = frame.size
    scale = min(cw / fw, ch / fh)
    new = (max(1, int(fw * scale)), max(1, int(fh * scale)))
    resized = frame.resize(new, Image.LANCZOS)
    x = cw - new[0]
    y = (ch - new[1]) // 2
    if resized.mode == "RGBA":
        cell.paste(resized, (x, y), resized)
    else:
        cell.paste(resized, (x, y))


def render_sheets(frames: list[Path], config: LayoutConfig) -> list[Image.Image]:
    page_size = config.page_px()
    cell_w, cell_h = config.cell_px()
    margin = config.margin_px()
    per_page = config.cols * config.rows

    pages: list[Image.Image] = []
    for start in range(0, len(frames), per_page):
        batch = frames[start : start + per_page]
        page = _load_background(config.background, page_size)
        for i, frame_path in enumerate(batch):
            row, col = divmod(i, config.cols)
            cell = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
            with Image.open(frame_path) as raw:
                frame = raw.convert("RGBA")
                _place_in_cell(cell, frame)
            x = margin + col * cell_w
            y = margin + row * cell_h
            page.paste(cell, (x, y), cell)
        pages.append(page)
    return pages


def save_pdf(pages: list[Image.Image], out: Path) -> None:
    if not pages:
        raise ValueError("no pages to save")
    first, rest = pages[0], pages[1:]
    first.save(out, "PDF", resolution=300.0, save_all=True, append_images=rest)
