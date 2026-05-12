from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from flipbook_maker.cli import main
from flipbook_maker.layout import PAPER_SIZES_MM, LayoutConfig, render_sheets


def _make_frame(path: Path, color: tuple[int, int, int] = (128, 128, 128)) -> None:
    Image.new("RGB", (400, 200), color).save(path)


@pytest.mark.parametrize("paper", list(PAPER_SIZES_MM.keys()))
@pytest.mark.parametrize("orientation", ["--portrait", "--landscape"])
def test_paper_preset_and_orientation(tmp_path: Path, paper: str, orientation: str) -> None:
    frame = tmp_path / "frame_001.png"
    _make_frame(frame)
    out = tmp_path / "out.pdf"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(tmp_path), "-o", str(out), "--cols", "1", "--rows", "1",
         "--paper", paper, orientation],
    )

    assert result.exit_code == 0, result.output
    assert out.exists() and out.stat().st_size > 0


def test_default_paper_is_a4_portrait(tmp_path: Path) -> None:
    frame = tmp_path / "frame_001.png"
    _make_frame(frame)
    out = tmp_path / "out.pdf"

    runner = CliRunner()
    result = runner.invoke(main, [str(tmp_path), "-o", str(out), "--cols", "1", "--rows", "1"])

    assert result.exit_code == 0, result.output
    assert out.exists()


def test_landscape_swaps_dimensions(tmp_path: Path) -> None:
    w, h = PAPER_SIZES_MM["a4"]
    portrait_config = LayoutConfig(page_size_mm=(w, h), cols=1, rows=1, dpi=72)
    landscape_config = LayoutConfig(page_size_mm=(h, w), cols=1, rows=1, dpi=72)

    pw, ph = portrait_config.page_px()
    lw, lh = landscape_config.page_px()

    assert pw < ph
    assert lw > lh


def test_preview_pixel_match(tmp_path: Path) -> None:
    """--preview 1 on 32 frames at 2x8 produces a PNG matching sheet 1 of full render."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    frames = []
    for i in range(32):
        p = frames_dir / f"frame_{i:03d}.png"
        _make_frame(p, (i * 7 % 255, i * 13 % 255, i * 19 % 255))
        frames.append(p)

    config = LayoutConfig(cols=2, rows=8)
    pages = render_sheets(frames, config)
    expected = pages[0]

    out_png = tmp_path / "output.png"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(frames_dir), "-o", str(out_png), "--cols", "2", "--rows", "8", "--preview", "1"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert out_png.exists()

    actual = Image.open(out_png)
    assert list(expected.getdata()) == list(actual.getdata())


def test_preview_out_of_range(tmp_path: Path) -> None:
    """--preview 3 on 16 frames (2 pages) raises a clear error."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    for i in range(16):
        _make_frame(frames_dir / f"frame_{i:03d}.png", (0, 0, 0))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(frames_dir), "--cols", "2", "--rows", "8", "--preview", "3"],
    )
    assert result.exit_code != 0
    assert "out of range" in result.output


def test_preview_default_output_name(tmp_path: Path) -> None:
    """When no -o is given, --preview writes to preview.png in cwd."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    _make_frame(frames_dir / "frame_000.png", (100, 100, 100))

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(main, [str(frames_dir), "--preview", "1"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert Path(td, "preview.png").exists()
