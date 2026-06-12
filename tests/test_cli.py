from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from flipbook_maker import PAPER_SIZES_MM, LayoutConfig, render_sheets
from flipbook_maker.flipbook.cli import _natural_key, main


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


def test_natural_key_sorts_correctly() -> None:
    paths = [Path(name) for name in ["frame_10.png", "frame_2.png", "frame_1.png"]]
    result = sorted(paths, key=_natural_key)
    assert [p.name for p in result] == ["frame_1.png", "frame_2.png", "frame_10.png"]


def test_cli_natural_sort_smoke(tmp_path: Path) -> None:
    for i in range(1, 13):
        _make_frame(tmp_path / f"frame_{i}.png")
    out = tmp_path / "out.pdf"
    result = CliRunner().invoke(
        main, [str(tmp_path), "-o", str(out), "--cols", "2", "--rows", "6"]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_order_file_happy_path(tmp_path: Path) -> None:
    for i in range(1, 4):
        _make_frame(tmp_path / f"frame_{i}.png")
    order_file = tmp_path / "order.txt"
    order_file.write_text(
        f"{tmp_path / 'frame_3.png'}\nframe_1.png\nframe_2.png\n# a comment\n\n"
    )
    out = tmp_path / "out.pdf"
    result = CliRunner().invoke(
        main, [str(tmp_path), "-o", str(out), "--order-file", str(order_file),
               "--cols", "1", "--rows", "3"]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_order_file_missing_frame_raises(tmp_path: Path) -> None:
    _make_frame(tmp_path / "frame_1.png")
    order_file = tmp_path / "order.txt"
    order_file.write_text("frame_1.png\nmissing_frame.png\n")
    out = tmp_path / "out.pdf"
    result = CliRunner().invoke(
        main, [str(tmp_path), "-o", str(out), "--order-file", str(order_file)]
    )
    assert result.exit_code != 0
    assert "missing_frame.png" in result.output


def test_from_video_no_ffmpeg(tmp_path: Path) -> None:
    """--from-video raises a clear error when ffmpeg is not on PATH."""
    video = tmp_path / "test.mp4"
    video.touch()

    with patch("flipbook_maker.flipbook.cli.shutil.which", return_value=None):
        result = CliRunner().invoke(
            main,
            ["--from-video", str(video), "-o", str(tmp_path / "out.pdf")],
        )
    assert result.exit_code != 0
    assert "ffmpeg" in result.output


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_from_video(tmp_path: Path) -> None:
    """--from-video extracts frames via ffmpeg and produces a PDF."""
    video = tmp_path / "test.mp4"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "color=c=blue:size=320x240:rate=12",
         "-t", "2", str(video)],
        check=True, capture_output=True,
    )
    out = tmp_path / "out.pdf"
    result = CliRunner().invoke(
        main,
        ["--from-video", str(video), "--fps", "12", "-o", str(out),
         "--cols", "2", "--rows", "8"],
    )
    assert result.exit_code == 0, result.output
    assert out.exists() and out.stat().st_size > 0
