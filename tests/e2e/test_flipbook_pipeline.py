"""End-to-end test: render 16 frames with py5, run them through the flipbook
pipeline, and commit the resulting single-sheet PDF under ``qa/`` as a QA
artifact.

The py5 sketch needs an OpenGL display, which on headless Linux is provided
by Xvfb. The test skips cleanly when py5 or Xvfb are unavailable so the rest
of the test suite stays runnable on minimal environments.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from flipbook_maker.flipbook.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
SKETCH = Path(__file__).with_name("generate_p5_frames.py")
QA_DIR = REPO_ROOT / "qa"
QA_PDF = QA_DIR / "flipbook.pdf"

NUM_FRAMES = 16


def _py5_available() -> bool:
    return importlib.util.find_spec("py5") is not None


def _needs_xvfb() -> bool:
    # On Linux without a $DISPLAY py5 cannot run; we shell out via xvfb-run.
    return sys.platform.startswith("linux")


def _run_sketch(out_dir: Path) -> None:
    cmd = [sys.executable, str(SKETCH), str(out_dir)]
    if _needs_xvfb():
        xvfb = shutil.which("xvfb-run")
        if xvfb is None:
            pytest.skip("xvfb-run not available; needed to run py5 headlessly")
        cmd = [xvfb, "-a", *cmd]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        pytest.fail(
            f"py5 sketch failed (exit {proc.returncode}):\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


@pytest.mark.skipif(not _py5_available(), reason="py5 not installed")
def test_p5_animation_to_single_sheet_flipbook(tmp_path: Path) -> None:
    """Render 16 py5 frames and lay them out as a single A4 flipbook sheet."""
    frames_dir = tmp_path / "frames"
    _run_sketch(frames_dir)

    frames = sorted(frames_dir.glob("frame_*.png"))
    assert len(frames) == NUM_FRAMES, f"expected {NUM_FRAMES} frames, got {len(frames)}"

    QA_DIR.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            str(frames_dir),
            "-o", str(QA_PDF),
            "--cols", "2",
            "--rows", "8",
            "--paper", "a4",
            "--portrait",
            "--frame-numbers",
            "--cut-marks",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert QA_PDF.exists() and QA_PDF.stat().st_size > 0

    # A 16-frame run at 2x8 must fit on a single sheet.
    assert "wrote 1 page(s) covering 16 frame(s)" in result.output

    # Sanity-check the file is actually a PDF.
    assert QA_PDF.read_bytes()[:4] == b"%PDF"
