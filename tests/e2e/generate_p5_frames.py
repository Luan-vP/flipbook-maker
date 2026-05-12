"""py5 sketch: render 16 frames of a bouncing/rotating shape.

Run standalone (typically under xvfb-run on headless Linux):

    xvfb-run -a python tests/e2e/generate_p5_frames.py <out_dir>

Writes frame_001.png ... frame_016.png into <out_dir>.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import py5

NUM_FRAMES = 16
FRAME_SIZE = 400
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("frames")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def setup() -> None:
    py5.size(FRAME_SIZE, FRAME_SIZE)
    py5.no_stroke()


def draw() -> None:
    # frame_count is 1-indexed in Processing/py5
    i = py5.frame_count - 1
    t = i / NUM_FRAMES  # 0 .. <1 across the loop

    # Soft warm background that shifts with the loop.
    py5.background(245, 240 - 20 * math.sin(t * math.tau), 225)

    cx = FRAME_SIZE / 2
    cy = FRAME_SIZE / 2
    orbit_r = FRAME_SIZE * 0.30
    angle = t * math.tau

    # Trail of fading shadows so the animation reads as motion in flipbook form.
    for k in range(5):
        a = angle - k * 0.18
        x = cx + orbit_r * math.cos(a)
        y = cy + orbit_r * math.sin(a)
        alpha = 255 * (1 - k / 5) * 0.55
        py5.fill(60, 90, 180, alpha)
        py5.circle(x, y, 70 - k * 8)

    # Solid head of the orbit.
    py5.fill(220, 70, 90)
    py5.circle(
        cx + orbit_r * math.cos(angle),
        cy + orbit_r * math.sin(angle),
        80,
    )

    # Rotating square in the centre to add a second motion cue.
    py5.push_matrix()
    py5.translate(cx, cy)
    py5.rotate(angle * 2)
    py5.fill(30, 30, 40)
    py5.rect_mode(py5.CENTER)
    py5.rect(0, 0, 60, 60)
    py5.pop_matrix()

    py5.save_frame(str(OUT_DIR / f"frame_{py5.frame_count:03d}.png"))

    if py5.frame_count >= NUM_FRAMES:
        py5.exit_sketch()


if __name__ == "__main__":
    py5.run_sketch()
