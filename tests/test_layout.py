from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from flipbook_maker.layout import LayoutConfig, render_sheets, save_pages, save_pdf


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


def test_cut_marks_pixels(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (255, 255, 255))
    config = LayoutConfig(cols=1, rows=1, dpi=72, cut_marks=True)
    pages = render_sheets([frame], config)
    page = pages[0]

    margin = config.margin_px()
    # Top-left corner of the single cell; ticks extend left and up
    cx, cy = margin, margin
    # One pixel inward from the corner along the horizontal tick
    assert page.getpixel((cx - 1, cy))[:3] == (0, 0, 0)
    # One pixel inward along the vertical tick
    assert page.getpixel((cx, cy - 1))[:3] == (0, 0, 0)


def test_cell_outline_pixels(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (255, 255, 255))
    config = LayoutConfig(cols=1, rows=1, dpi=72, cell_outline=True)
    pages = render_sheets([frame], config)
    page = pages[0]

    margin = config.margin_px()
    cell_w, cell_h = config.cell_px()
    cx, cy = margin, margin
    # Mid-point of top edge
    assert page.getpixel((cx + cell_w // 2, cy))[:3] == (0, 0, 0)
    # Mid-point of left edge
    assert page.getpixel((cx, cy + cell_h // 2))[:3] == (0, 0, 0)


def test_no_decorations_regression(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (200, 100, 50))
    config_old = LayoutConfig(cols=1, rows=1, dpi=72)
    config_new = LayoutConfig(cols=1, rows=1, dpi=72, cut_marks=False, cell_outline=False)
    pages_old = render_sheets([frame], config_old)
    pages_new = render_sheets([frame], config_new)
    assert pages_old[0].tobytes() == pages_new[0].tobytes()


# Landscape config: cell is wider than tall — exercises pillarbox/cover/stretch
_WIDE_CONFIG = dict(cols=1, rows=1, dpi=72, margin_mm=0.0, page_size_mm=(200.0, 100.0))
_FRAME_COLOR = (200, 50, 50)
_BG_COLOR = (255, 255, 255)


def _wide_frame(path: Path) -> Path:
    """400x400 square frame saved to path."""
    Image.new("RGB", (400, 400), _FRAME_COLOR).save(path)
    return path


def test_fit_contain_pillarbox(tmp_path: Path) -> None:
    """Square frame into wide cell: pillarbox (background) on the left, frame on the right."""
    frame = _wide_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_WIDE_CONFIG, fit="contain")
    page = render_sheets([frame], config)[0]

    cw, ch = config.cell_px()
    margin = config.margin_px()

    left_pixel = page.getpixel((margin, margin + ch // 2))[:3]
    assert left_pixel == _BG_COLOR, f"expected pillarbox (bg) on left, got {left_pixel}"

    right_pixel = page.getpixel((margin + cw - 1, margin + ch // 2))[:3]
    assert right_pixel == _FRAME_COLOR, f"expected frame on right, got {right_pixel}"


def test_fit_cover_no_border(tmp_path: Path) -> None:
    """Square frame into wide cell: frame fills entire cell, no background border on any side."""
    frame = _wide_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_WIDE_CONFIG, fit="cover")
    page = render_sheets([frame], config)[0]

    cw, ch = config.cell_px()
    margin = config.margin_px()

    left_pixel = page.getpixel((margin, margin + ch // 2))[:3]
    assert left_pixel != _BG_COLOR, f"expected no pillarbox on left, got background: {left_pixel}"

    right_pixel = page.getpixel((margin + cw - 1, margin + ch // 2))[:3]
    assert right_pixel == _FRAME_COLOR, f"expected frame on right, got {right_pixel}"

    top_pixel = page.getpixel((margin + cw // 2, margin))[:3]
    assert top_pixel != _BG_COLOR, f"expected no letterbox on top, got background: {top_pixel}"

    bottom_pixel = page.getpixel((margin + cw // 2, margin + ch - 1))[:3]
    assert (
        bottom_pixel != _BG_COLOR
    ), f"expected no letterbox on bottom, got background: {bottom_pixel}"


def test_fit_stretch_fills_cell(tmp_path: Path) -> None:
    """Stretch mode: frame fully covers every corner of the cell."""
    frame = _wide_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_WIDE_CONFIG, fit="stretch")
    page = render_sheets([frame], config)[0]

    cw, ch = config.cell_px()
    margin = config.margin_px()

    corners = [
        (margin, margin),
        (margin + cw - 1, margin),
        (margin, margin + ch - 1),
        (margin + cw - 1, margin + ch - 1),
    ]
    for x, y in corners:
        pixel = page.getpixel((x, y))[:3]
        assert pixel == _FRAME_COLOR, f"expected frame at corner ({x},{y}), got {pixel}"


@pytest.mark.parametrize("fit", ["contain", "cover", "stretch"])
def test_right_wall_invariant(tmp_path: Path, fit: str) -> None:
    """Right edge of the cell always shows the frame, not the background, for all fit modes."""
    frame = _wide_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_WIDE_CONFIG, fit=fit)
    page = render_sheets([frame], config)[0]

    cw, ch = config.cell_px()
    margin = config.margin_px()
    x_right = margin + cw - 1
    y_mid = margin + ch // 2

    pixel = page.getpixel((x_right, y_mid))[:3]
    assert pixel == _FRAME_COLOR, f"right-wall invariant failed for fit={fit!r}: got {pixel}"


def test_save_pages_pdf(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (0, 128, 0))
    pages = render_sheets([frame], LayoutConfig(cols=1, rows=1))
    out = tmp_path / "out.pdf"
    save_pages(pages, out, fmt="pdf")
    assert out.exists() and out.stat().st_size > 0


def test_save_pages_png_directory(tmp_path: Path) -> None:
    frames = []
    config = LayoutConfig(cols=2, rows=4)
    per_page = config.cols * config.rows
    for i in range(per_page * 2):
        p = tmp_path / f"frame_{i:03d}.png"
        _make_frame(p, (i * 5 % 255, 0, 0))
        frames.append(p)

    pages = render_sheets(frames, config)
    out_dir = tmp_path / "pngs"
    save_pages(pages, out_dir, fmt="png", dpi=300)

    expected_files = [out_dir / f"page_{i:03d}.png" for i in range(1, len(pages) + 1)]
    for f in expected_files:
        assert f.exists(), f"{f} not found"
        img = Image.open(f)
        assert img.size == config.page_px()


def test_save_pages_png_prefix(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (200, 100, 50))
    config = LayoutConfig(cols=1, rows=1)
    pages = render_sheets([frame], config)

    out = tmp_path / "output" / "mybook.png"
    save_pages(pages, out, fmt="png", dpi=300)

    result = tmp_path / "output" / "mybook_001.png"
    assert result.exists()
    img = Image.open(result)
    assert img.size == config.page_px()


def test_save_pages_png_dpi_metadata(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (0, 0, 255))
    pages = render_sheets([frame], LayoutConfig(cols=1, rows=1))
    out_dir = tmp_path / "pngs"
    save_pages(pages, out_dir, fmt="png", dpi=300)

    img = Image.open(out_dir / "page_001.png")
    dpi = img.info.get("dpi")
    assert dpi is not None and round(dpi[0]) == 300 and round(dpi[1]) == 300


def test_save_pages_unknown_format(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_frame(frame, (0, 0, 0))
    pages = render_sheets([frame], LayoutConfig(cols=1, rows=1))
    import pytest
    with pytest.raises(ValueError, match="unknown format"):
        save_pages(pages, tmp_path / "out", fmt="jpeg")


def _make_portrait_frame(path: Path, color: tuple[int, int, int]) -> None:
    """Tall frame (100x400) so contain-fit leaves a real left bind strip in A4-portrait cells."""
    Image.new("RGB", (100, 400), color).save(path)


def test_frame_numbers_renders_in_bind_strip(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_portrait_frame(frame, (200, 200, 200))
    config = LayoutConfig(cols=1, rows=1, dpi=72, background="white", frame_numbers=True)
    pages = render_sheets([frame], config)
    page = pages[0]
    margin = config.margin_px()
    _, cell_h = config.cell_px()
    band_half = max(cell_h // 4, 20)
    mid_y = margin + cell_h // 2
    found_non_white = any(
        page.getpixel((x, y)) != (255, 255, 255)
        for x in range(margin, margin + 30)
        for y in range(mid_y - band_half, mid_y + band_half)
    )
    assert found_non_white, "expected frame number pixels in the bind strip but found none"


_BIND_CONFIG = dict(
    cols=1, rows=1, dpi=72, margin_mm=0.0, page_size_mm=(100.0, 200.0), background="white"
)
_BIND_FRAME_COLOR = (255, 0, 0)


def _bind_frame(path: Path) -> Path:
    """400x400 square frame; in a (100x200mm) cell with a 10mm strip, width == usable area."""
    Image.new("RGB", (400, 400), _BIND_FRAME_COLOR).save(path)
    return path


def test_bind_strip_exact_width(tmp_path: Path) -> None:
    """1:1 frame with bind_strip_mm=10 is rendered narrower than cell width by exactly 10 mm."""
    frame = _bind_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_BIND_CONFIG, bind_strip_mm=10.0, fit="contain")
    page = render_sheets([frame], config)[0]

    cell_w, cell_h = config.cell_px()
    bind_px = config.bind_strip_px()
    mid_y = cell_h // 2

    # Strip region is background (white)
    assert page.getpixel((bind_px - 1, mid_y))[:3] != _BIND_FRAME_COLOR, \
        "expected strip (not frame) at left of cell"

    # Frame starts exactly at bind_strip_px from cell left
    assert page.getpixel((bind_px, mid_y))[:3] == _BIND_FRAME_COLOR, \
        f"expected frame to start at x={bind_px}"

    # Right-wall invariant
    assert page.getpixel((cell_w - 1, mid_y))[:3] == _BIND_FRAME_COLOR, \
        "right-wall invariant failed with bind strip"


@pytest.mark.parametrize("fit", ["contain", "cover", "stretch"])
def test_right_wall_invariant_with_bind_strip(tmp_path: Path, fit: str) -> None:
    """Right-wall invariant holds for all fit modes when bind_strip_mm is set."""
    frame = _bind_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_BIND_CONFIG, bind_strip_mm=10.0, fit=fit)
    page = render_sheets([frame], config)[0]

    cell_w, cell_h = config.cell_px()
    pixel = page.getpixel((cell_w - 1, cell_h // 2))[:3]
    assert pixel == _BIND_FRAME_COLOR, f"right-wall invariant failed for fit={fit!r}: got {pixel}"


def test_bind_strip_zero_unchanged(tmp_path: Path) -> None:
    """bind_strip_mm=0 (default) produces identical output to not specifying it."""
    frame = _bind_frame(tmp_path / "frame.png")
    config_default = LayoutConfig(**_WIDE_CONFIG, fit="contain")
    config_zero = LayoutConfig(**_WIDE_CONFIG, fit="contain", bind_strip_mm=0.0)
    pages_default = render_sheets([frame], config_default)
    pages_zero = render_sheets([frame], config_zero)
    assert pages_default[0].tobytes() == pages_zero[0].tobytes()


def test_bind_strip_color_fills_strip(tmp_path: Path) -> None:
    """When bind_strip_color is set, the strip region is painted with that color."""
    frame = _bind_frame(tmp_path / "frame.png")
    strip_color_hex = "#ffff00"
    strip_color_rgb = (255, 255, 0)
    config = LayoutConfig(
        **_BIND_CONFIG, bind_strip_mm=10.0, bind_strip_color=strip_color_hex, fit="contain"
    )
    page = render_sheets([frame], config)[0]

    bind_px = config.bind_strip_px()
    cell_h = config.cell_px()[1]
    mid_y = cell_h // 2

    actual = page.getpixel((bind_px // 2, mid_y))[:3]
    assert actual == strip_color_rgb, f"expected strip color {strip_color_rgb}, got {actual}"


def test_bind_strip_no_color_shows_background(tmp_path: Path) -> None:
    """When bind_strip_color is None, the strip shows the page background."""
    frame = _bind_frame(tmp_path / "frame.png")
    config = LayoutConfig(**_BIND_CONFIG, bind_strip_mm=10.0, bind_strip_color=None, fit="contain")
    page = render_sheets([frame], config)[0]

    bind_px = config.bind_strip_px()
    cell_h = config.cell_px()[1]
    mid_y = cell_h // 2

    assert page.getpixel((bind_px // 2, mid_y))[:3] == (255, 255, 255), \
        "expected white background in strip when bind_strip_color is None"


def test_frame_numbers_off_leaves_bind_strip_white(tmp_path: Path) -> None:
    frame = tmp_path / "f.png"
    _make_portrait_frame(frame, (200, 200, 200))
    config = LayoutConfig(cols=1, rows=1, dpi=72, background="white", frame_numbers=False)
    pages = render_sheets([frame], config)
    page = pages[0]
    margin = config.margin_px()
    _, cell_h = config.cell_px()
    mid_y = margin + cell_h // 2
    band_half = max(cell_h // 4, 20)
    found_non_white = any(
        page.getpixel((x, y)) != (255, 255, 255)
        for x in range(margin, margin + 30)
        for y in range(mid_y - band_half, mid_y + band_half)
    )
    assert not found_non_white, "bind strip should be untouched when frame_numbers=False"
