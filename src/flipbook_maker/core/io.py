from __future__ import annotations

from pathlib import Path

from PIL import Image


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
