#!/usr/bin/env python3
"""Put a tarot reading on the back of a one-page zine for double-sided printing.

Takes a one-page front (JPG/PNG or single-page PDF) and emits a 2-page PDF
normalized to a real paper size (A4 by default): page 1 is the front fitted to
the page, page 2 is a 3-card Past/Present/Future reading. Print it double-sided
and the reading lands on the back, ready to fold.

The back can be laid out two ways:
  * default      — the reading's own landscape 4x2 t-fold zine
  * --grid CxR   — an upright C-column x R-row grid that matches a front whose
                   own panels are a plain grid (e.g. --grid 2x4), so the tarot
                   panels sit behind the front panels when printed duplex.

The back is drawn with the same seed logic as `flipbook-tarot`, so `--seed <n>`
reproduces a specific reading (e.g. one revealed via the tarot-reading skill).

Runs in the project environment (needs `flipbook_maker` + Pillow):

    uv run python skills/tarot-duplex/duplex.py front.jpg
    uv run python skills/tarot-duplex/duplex.py front.jpg --grid 2x4 --seed 42
    uv run --extra pdf python skills/tarot-duplex/duplex.py front.pdf --flip short

PDF fronts need the `pdf` extra (`uv sync --extra pdf`); image fronts need nothing extra.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw

from flipbook_maker import render_tarot_reading, save_pages

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PAPER_MM = {"a4": (210.0, 297.0), "a3": (297.0, 420.0),
            "letter": (215.9, 279.4), "legal": (215.9, 355.6)}


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / 25.4))


def load_front(path: Path, dpi: int) -> Image.Image:
    """Load the front page as an RGB image (first page only, for PDFs)."""
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return Image.open(path).convert("RGB")
    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium
        except ImportError:
            sys.exit(
                "PDF fronts need pypdfium2. Install it with `uv sync --extra pdf` "
                "(or `pip install pypdfium2`), or pass a JPG/PNG front instead."
            )
        pdf = pdfium.PdfDocument(str(path))
        bitmap = pdf[0].render(scale=dpi / 72.0)  # PDF user units are 1/72 inch
        return bitmap.to_pil().convert("RGB")
    sys.exit(f"unsupported front type: {ext!r} (use JPG/PNG or a single-page PDF)")


def fit_onto(img: Image.Image, size: tuple[int, int], bg: str) -> Image.Image:
    """Letterbox img onto a bg page of the given size, preserving aspect (no crop)."""
    page_w, page_h = size
    canvas = Image.new("RGB", size, ImageColor.getrgb(bg))
    scale = min(page_w / img.width, page_h / img.height)
    new = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resized = img.resize(new, Image.LANCZOS)
    canvas.paste(resized, ((page_w - new[0]) // 2, (page_h - new[1]) // 2))
    return canvas


def render_grid_back(seed: int | None, dpi: int, size: tuple[int, int], cols: int, rows: int,
                     margin_mm: float, bg: str, fg: str) -> Image.Image:
    """Render the 3-card reading as an upright cols x rows grid on one page."""
    from flipbook_maker.tarot import TAROT_DECK, TarotCard, _render_card_panel

    past, present, future = random.Random(seed).sample(TAROT_DECK, 3)
    # Order so a 2-column grid pairs each position label beside its card per row,
    # with the cover/footer on the last row.
    panels: list[TarotCard] = [
        TarotCard("Past", "What has shaped this moment"), past,
        TarotCard("Present", "Where you stand now"), present,
        TarotCard("Future", "Where the current path leads"), future,
        TarotCard("Tarot", "A three-card reading"),
        TarotCard("Tarot", "drawn for the reverse"),
    ]

    page_w, page_h = size
    margin = mm_to_px(margin_mm, dpi)
    cell_w = (page_w - 2 * margin) // cols
    cell_h = (page_h - 2 * margin) // rows
    page = Image.new("RGB", size, ImageColor.getrgb(bg))
    draw = ImageDraw.Draw(page)
    outline_w = max(1, mm_to_px(0.2, dpi))

    for i, card in enumerate(panels[: cols * rows]):
        r, c = divmod(i, cols)
        x, y = margin + c * cell_w, margin + r * cell_h
        page.paste(_render_card_panel(card, cell_w, cell_h, dpi, bg, fg), (x, y))
        draw.rectangle([(x, y), (x + cell_w, y + cell_h)],
                       outline=ImageColor.getrgb(fg), width=outline_w)
    return page


def parse_grid(spec: str | None) -> tuple[int, int] | None:
    if spec is None:
        return None
    try:
        cols, rows = (int(n) for n in spec.lower().split("x"))
        if cols < 1 or rows < 1:
            raise ValueError
        return cols, rows
    except ValueError:
        sys.exit(f"--grid must look like COLSxROWS (e.g. 2x4), got {spec!r}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Put a tarot reading on the back of a one-page zine, "
        "as a 2-page PDF for double-sided printing.",
    )
    ap.add_argument("front", type=Path, help="One-page front: JPG/PNG or single-page PDF.")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output PDF path (default: <front>_duplex.pdf).")
    ap.add_argument("--paper", choices=list(PAPER_MM), default="a4",
                    help="Output paper size. Default: a4.")
    ap.add_argument("--grid", type=str, default=None, metavar="CxR",
                    help="Lay the back out as an upright C-col x R-row grid to match a "
                         "front that is itself a plain grid (e.g. 2x4). Default: the "
                         "reading's own 4x2 t-fold zine.")
    ap.add_argument("--seed", type=int, default=None,
                    help="Seed for the tarot draw — reproducible, matches flipbook-tarot --seed.")
    ap.add_argument("--flip", choices=["long", "short"], default="long",
                    help="Duplex binding edge. 'short' rotates the back 180° so it prints "
                         "upright on short-edge flip. Default: long (no rotation).")
    ap.add_argument("--dpi", type=int, default=300,
                    help="Output raster DPI. Default: 300.")
    ap.add_argument("--dark", action="store_true",
                    help="Render the back white-on-black. Default is black-on-white "
                         "(print-friendly, saves ink and matches a white front).")
    args = ap.parse_args()

    if not args.front.exists():
        sys.exit(f"front not found: {args.front}")
    grid = parse_grid(args.grid)
    bg, fg = ("black", "white") if args.dark else ("white", "black")

    front_img = load_front(args.front, args.dpi)
    landscape = front_img.width >= front_img.height
    w_mm, h_mm = PAPER_MM[args.paper]
    if landscape:
        w_mm, h_mm = h_mm, w_mm
    size = (mm_to_px(w_mm, args.dpi), mm_to_px(h_mm, args.dpi))

    front = fit_onto(front_img, size, bg="white")
    if grid is not None:
        back = render_grid_back(args.seed, args.dpi, size, grid[0], grid[1],
                                margin_mm=5.0, bg=bg, fg=fg)
    else:
        back = render_tarot_reading(seed=args.seed, dpi=args.dpi, landscape=landscape,
                                    background=bg, foreground=fg)[0]
        if back.size != size:
            back = back.resize(size, Image.LANCZOS)
    if args.flip == "short":
        back = back.rotate(180)

    out = args.output or args.front.with_name(args.front.stem + "_duplex.pdf")
    save_pages([front, back], out, fmt="pdf", dpi=args.dpi)

    layout = f"{grid[0]}x{grid[1]} grid" if grid else "t-fold zine"
    seed_note = f", seed {args.seed}" if args.seed is not None else ""
    print(f"wrote 2-page duplex PDF → {out}  "
          f"(front: {args.front.name} on {args.paper.upper()}; "
          f"back: tarot {layout}{seed_note}, {args.flip}-edge flip)")


if __name__ == "__main__":
    main()
