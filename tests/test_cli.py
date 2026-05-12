from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from flipbook_maker.cli import main
from flipbook_maker.layout import PAPER_SIZES_MM


def _make_frame(path: Path) -> None:
    Image.new("RGB", (100, 60), (128, 128, 128)).save(path)


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
    from flipbook_maker.layout import LayoutConfig

    w, h = PAPER_SIZES_MM["a4"]
    portrait_config = LayoutConfig(page_size_mm=(w, h), cols=1, rows=1, dpi=72)
    landscape_config = LayoutConfig(page_size_mm=(h, w), cols=1, rows=1, dpi=72)

    pw, ph = portrait_config.page_px()
    lw, lh = landscape_config.page_px()

    assert pw < ph
    assert lw > lh
