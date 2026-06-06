#!/usr/bin/env python3
"""Put a tarot reading on the back of a one-page zine for double-sided printing.

Takes a one-page front (JPG/PNG or single-page PDF) and emits a 2-page PDF:
page 1 is the front as-is, page 2 is a 3-card Past/Present/Future tarot reading
sized and oriented to match. Print it double-sided and the reading lands on the
back, ready to fold.

The back is drawn with the same seed logic as `flipbook-tarot`, so
`--seed <n>` reproduces a specific reading (e.g. one revealed in chat via the
tarot-reading skill).

Runs in the project environment (needs `flipbook_maker` + Pillow):

    uv run python skills/tarot-duplex/duplex.py front.jpg
    uv run python skills/tarot-duplex/duplex.py front.jpg --seed 42 -o zine.pdf
    uv run --extra pdf python skills/tarot-duplex/duplex.py front.pdf --flip short

PDF fronts need the `pdf` extra (`uv sync --extra pdf`); JPG/PNG fronts need nothing extra.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from flipbook_maker import render_tarot_reading, save_pages

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


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


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Put a tarot reading on the back of a one-page zine, "
        "as a 2-page PDF for double-sided printing.",
    )
    ap.add_argument("front", type=Path, help="One-page front: JPG/PNG or single-page PDF.")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output PDF path (default: <front>_duplex.pdf).")
    ap.add_argument("--seed", type=int, default=None,
                    help="Seed for the tarot draw — reproducible, matches flipbook-tarot --seed.")
    ap.add_argument("--flip", choices=["long", "short"], default="long",
                    help="Duplex binding edge. 'short' rotates the back 180° so it prints "
                         "upright on short-edge flip. Default: long (no rotation).")
    ap.add_argument("--dpi", type=int, default=300,
                    help="Raster DPI for the output pages. Default: 300.")
    args = ap.parse_args()

    if not args.front.exists():
        sys.exit(f"front not found: {args.front}")

    front = load_front(args.front, args.dpi)
    w, h = front.size
    landscape = w >= h

    # Draw the reading in the front's orientation, then match its exact pixel
    # size so the two pages register cleanly when printed duplex.
    back = render_tarot_reading(seed=args.seed, dpi=args.dpi, landscape=landscape)[0]
    if back.size != (w, h):
        back = back.resize((w, h), Image.LANCZOS)
    if args.flip == "short":
        back = back.rotate(180)

    out = args.output or args.front.with_name(args.front.stem + "_duplex.pdf")
    save_pages([front, back], out, fmt="pdf", dpi=args.dpi)

    seed_note = f", seed {args.seed}" if args.seed is not None else ""
    print(f"wrote 2-page duplex PDF → {out}  "
          f"(front: {args.front.name}; back: tarot reading{seed_note}, {args.flip}-edge flip)")


if __name__ == "__main__":
    main()
