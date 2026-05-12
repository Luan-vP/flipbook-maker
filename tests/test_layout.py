from __future__ import annotations

from pathlib import Path

from PIL import Image

from flipbook_maker.layout import LayoutConfig, render_sheets, save_pdf


def _make_frame(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (400, 200), color).save(path)


def test_render_sheets_default_grid(tmp_path: Path) -> None:
    frames = []
    for i in range(20):
        p = tmp_path / f"frame_{i:03d}.png"
        _make_frame(p, (i * 10 % 255, 0, 0))
        frames.append(p)

    config = LayoutConfig()
    pages = render_sheets(frames, config)

    assert len(pages) == 2
    assert pages[0].size == config.page_px()


def test_render_sheets_solid_background(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (255, 255, 255))
    pages = render_sheets([frame], LayoutConfig(background="#112233"))
    assert pages[0].getpixel((0, 0)) == (0x11, 0x22, 0x33)


def test_render_sheets_image_background(tmp_path: Path) -> None:
    bg = tmp_path / "bg.png"
    Image.new("RGB", (50, 50), (10, 20, 30)).save(bg)
    frame = tmp_path / "f.png"
    _make_frame(frame, (200, 200, 200))
    pages = render_sheets([frame], LayoutConfig(background=bg))
    assert pages[0].getpixel((0, 0)) == (10, 20, 30)


def test_save_pdf_writes_file(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (0, 128, 0))
    pages = render_sheets([frame], LayoutConfig(cols=1, rows=1))
    out = tmp_path / "out.pdf"
    save_pdf(pages, out)
    assert out.exists() and out.stat().st_size > 0
