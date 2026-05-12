from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageColor, ImageDraw, ImageFont

PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}

A4_MM = PAPER_SIZES_MM["a4"]

FitMode = Literal["contain", "cover", "stretch"]


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
    cut_marks: bool = False
    cell_outline: bool = False
    fit: FitMode = "contain"
    frame_numbers: bool = False
    frame_number_color: str = "black"
    frame_number_offset_mm: float = 2.0

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


def _place_in_cell(cell: Image.Image, frame: Image.Image, fit: FitMode = "contain") -> None:
    cw, ch = cell.size
    fw, fh = frame.size

    if fit == "contain":
        scale = min(cw / fw, ch / fh)
        new = (max(1, int(fw * scale)), max(1, int(fh * scale)))
        resized = frame.resize(new, Image.LANCZOS)
        x = cw - new[0]
        y = (ch - new[1]) // 2
        if resized.mode == "RGBA":
            cell.paste(resized, (x, y), resized)
        else:
            cell.paste(resized, (x, y))

    elif fit == "cover":
        scale = max(cw / fw, ch / fh)
        crop_w = cw / scale
        crop_h = ch / scale
        left = round(fw - crop_w)
        top = round((fh - crop_h) / 2)
        cropped = frame.crop((left, top, fw, fh - top))
        resized = cropped.resize((cw, ch), Image.LANCZOS)
        if resized.mode == "RGBA":
            cell.paste(resized, (0, 0), resized)
        else:
            cell.paste(resized, (0, 0))

    elif fit == "stretch":
        resized = frame.resize((cw, ch), Image.LANCZOS)
        if resized.mode == "RGBA":
            cell.paste(resized, (0, 0), resized)
        else:
            cell.paste(resized, (0, 0))


def _draw_frame_number(
    page: Image.Image,
    frame_idx: int,
    cell_x: int,
    cell_y: int,
    cell_h: int,
    config: LayoutConfig,
) -> None:
    font = ImageFont.load_default()
    label = str(frame_idx)
    offset_px = _mm_to_px(config.frame_number_offset_mm, config.dpi)
    draw = ImageDraw.Draw(page)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_h = bbox[3] - bbox[1]
    text_x = cell_x + offset_px
    text_y = cell_y + cell_h // 2 - text_h // 2
    draw.text(
        (text_x, text_y),
        label,
        font=font,
        fill=ImageColor.getrgb(config.frame_number_color),
    )


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
                _place_in_cell(cell, frame, config.fit)
            x = margin + col * cell_w
            y = margin + row * cell_h
            page.paste(cell, (x, y), cell)
            if config.frame_numbers:
                _draw_frame_number(page, start + i + 1, x, y, cell_h, config)

        if config.cut_marks or config.cell_outline:
            page_w, page_h = page_size
            draw = ImageDraw.Draw(page)
            tick_len = _mm_to_px(3.0, config.dpi)
            mark_w = max(1, _mm_to_px(0.25, config.dpi))
            outline_w = max(1, _mm_to_px(0.2, config.dpi))

            for row in range(config.rows):
                for col in range(config.cols):
                    cx = margin + col * cell_w
                    cy = margin + row * cell_h

                    if config.cell_outline:
                        draw.rectangle(
                            [(cx, cy), (cx + cell_w, cy + cell_h)],
                            outline=(0, 0, 0),
                            width=outline_w,
                        )

                    if config.cut_marks:
                        corners = [
                            (cx, cy, -1, -1),
                            (cx + cell_w, cy, 1, -1),
                            (cx, cy + cell_h, -1, 1),
                            (cx + cell_w, cy + cell_h, 1, 1),
                        ]
                        for x, y, hd, vd in corners:
                            hx = max(0, min(page_w - 1, x + hd * tick_len))
                            draw.line([(hx, y), (x, y)], fill=(0, 0, 0), width=mark_w)
                            vy = max(0, min(page_h - 1, y + vd * tick_len))
                            draw.line([(x, vy), (x, y)], fill=(0, 0, 0), width=mark_w)

        pages.append(page)
    return pages


def _save_pdf(pages: list[Image.Image], out: Path, dpi: int = 300) -> None:
    if not pages:
        raise ValueError("no pages to save")
    first, rest = pages[0], pages[1:]
    first.save(out, "PDF", resolution=float(dpi), save_all=True, append_images=rest)


def _save_pngs(pages: list[Image.Image], out: Path, dpi: int = 300) -> None:
    if not pages:
        raise ValueError("no pages to save")
    if out.suffix == "" or str(out).endswith("/"):
        directory = out
        stem = "page"
    else:
        directory = out.parent
        stem = out.stem
    directory.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(pages, start=1):
        page.save(directory / f"{stem}_{i:03d}.png", "PNG", dpi=(dpi, dpi))


def save_pages(pages: list[Image.Image], out: Path, fmt: str = "pdf", dpi: int = 300) -> None:
    if fmt == "pdf":
        _save_pdf(pages, out, dpi=dpi)
    elif fmt == "png":
        _save_pngs(pages, out, dpi=dpi)
    else:
        raise ValueError(f"unknown format {fmt!r}; expected 'pdf' or 'png'")


def save_pdf(pages: list[Image.Image], out: Path, dpi: int = 300) -> None:
    _save_pdf(pages, out, dpi=dpi)
