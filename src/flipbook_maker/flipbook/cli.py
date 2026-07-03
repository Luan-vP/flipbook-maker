from __future__ import annotations

import contextlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from flipbook_maker.core.io import save_pages
from flipbook_maker.core.paper import (
    FRAME_SIZE_PRESETS_MM,
    PAPER_SIZES_MM,
    grid_for_frame_size,
)
from flipbook_maker.flipbook.layout import LayoutConfig, render_sheets


def _default_output(ctx: click.Context, param: click.Parameter, value: Path | None) -> Path:
    if value is not None:
        return value
    if ctx.params.get("preview") is not None:
        return Path("preview.png")
    fmt = ctx.params.get("fmt", "pdf")
    return Path("flipbook.pdf") if fmt == "pdf" else Path("pages/")


def _natural_key(path: Path) -> list:
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _load_order_file(order_file: Path, frames_dir: Path) -> list[Path]:
    lines = order_file.read_text().splitlines()
    frames = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line)
        if not p.is_absolute():
            p = frames_dir / p
        if not p.exists():
            raise click.ClickException(f"frame not found: {p} (listed in order file)")
        frames.append(p)
    return frames


@click.command()
@click.pass_context
@click.argument("frames_dir", required=False,
                type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--from-video", "video_path",
              type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
              help="Extract frames from this video via ffmpeg instead of reading FRAMES_DIR.")
@click.option("--fps", type=int, default=12, show_default=True,
              help="Frames per second to extract when using --from-video.")
@click.option("--preview", type=int, default=None, metavar="N", is_eager=True,
              help="Render only sheet N (1-indexed) as a PNG and exit. PDF is not produced.")
@click.option("--format", "fmt", type=click.Choice(["pdf", "png"]), default="pdf",
              show_default=True, is_eager=True, help="Output format.")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              callback=_default_output, is_eager=False,
              help="Output path (PDF file or PNG dir/prefix). Defaults to flipbook.pdf or pages/.")
@click.option("--cols", type=int, default=2, show_default=True, help="Columns per sheet.")
@click.option("--rows", type=int, default=8, show_default=True, help="Rows per sheet.")
@click.option("--frame-size", type=click.Choice(list(FRAME_SIZE_PRESETS_MM.keys())),
              default=None,
              help="Fixed cell-size preset (e.g. filter-tip = 44x68mm). "
                   "Overrides --cols/--rows by fitting as many cells of this "
                   "size as possible onto the page.")
@click.option("--frame-w-mm", type=float, default=None,
              help="Custom fixed cell width in mm (use with --frame-h-mm instead of --frame-size).")
@click.option("--frame-h-mm", type=float, default=None,
              help="Custom fixed cell height in mm (use with --frame-w-mm instead of --frame-size).")
@click.option("--dpi", type=int, default=300, show_default=True, help="Output DPI.")
@click.option("--margin-mm", type=float, default=5.0, show_default=True, help="Sheet margin in mm.")
@click.option("--background", type=str, default="white", show_default=True,
              help="Background color (name/hex) OR path to a texture image.")
@click.option("--glob", "glob_pattern", type=str, default="*.png", show_default=True,
              help="Glob pattern for frame files within frames_dir.")
@click.option("--paper", type=click.Choice(list(PAPER_SIZES_MM.keys())), default="a4",
              show_default=True, help="Paper size preset.")
@click.option("--landscape/--portrait", default=False, show_default=True,
              help="Page orientation.")
@click.option("--cut-marks", is_flag=True, default=False,
              help="Draw cut-mark ticks at the corners of every cell.")
@click.option("--cell-outline", is_flag=True, default=False,
              help="Draw a thin hairline rectangle around every cell.")
@click.option("--fit", type=click.Choice(["contain", "cover", "stretch"]), default="contain",
              show_default=True, help="How frames are scaled into each cell.")
@click.option("--fill", type=click.Choice(["row", "column"]), default="row", show_default=True,
              help="Cell fill order: 'row' left-to-right then down, "
                   "'column' top-to-bottom then across.")
@click.option("--order-file", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Newline-delimited list of frame paths (absolute or relative to frames_dir).")
@click.option("--frame-numbers", is_flag=True, default=False,
              help="Print 1-based frame index in the bind strip of each cell.")
@click.option("--frame-number-color", type=str, default="black", show_default=True,
              help="Color for frame numbers (name or hex). Use 'white' on dark backgrounds.")
@click.option("--frame-number-offset-mm", type=float, default=2.0, show_default=True,
              help="Horizontal offset (mm) from cell's left edge for the frame number.")
@click.option("--bind-mm", "bind_strip_mm", type=float, default=0.0, show_default=True,
              help="Reserve a fixed bind strip of this width (mm) on the left of each cell.")
@click.option("--bind-color", "bind_strip_color", type=str, default=None,
              help="Fill the bind strip with this color (name or hex). Omit for page background.")
def main(ctx: click.Context, frames_dir: Path | None, video_path: Path | None, fps: int,
         preview: int | None, fmt: str, output: Path,
         cols: int, rows: int, frame_size: str | None, frame_w_mm: float | None,
         frame_h_mm: float | None, dpi: int, margin_mm: float, background: str, glob_pattern: str,
         paper: str, landscape: bool, cut_marks: bool, cell_outline: bool, fit: str,
         fill: str,
         order_file: Path | None, frame_numbers: bool, frame_number_color: str,
         frame_number_offset_mm: float, bind_strip_mm: float,
         bind_strip_color: str | None) -> None:
    """Format flipbook frames into a printable PDF or PNG pages.

    FRAMES_DIR is the source directory of PNG frames. Omit when using --from-video.
    """
    with contextlib.ExitStack() as stack:
        if video_path is not None:
            if frames_dir is not None:
                raise click.UsageError("FRAMES_DIR and --from-video are mutually exclusive")
            if order_file is not None:
                raise click.UsageError("--order-file and --from-video are mutually exclusive")
            if shutil.which("ffmpeg") is None:
                raise click.ClickException(
                    "ffmpeg not found on PATH; install it to use --from-video"
                )
            tmpdir = stack.enter_context(tempfile.TemporaryDirectory())
            tmp_path = Path(tmpdir)
            proc = subprocess.run(
                ["ffmpeg", "-y", "-i", str(video_path), "-vf", f"fps={fps}",
                 str(tmp_path / "frame_%04d.png")],
                capture_output=True,
            )
            if proc.returncode != 0:
                raise click.ClickException(
                    f"ffmpeg failed (exit {proc.returncode}):\n{proc.stderr.decode()}"
                )
            frames = sorted(tmp_path.glob("*.png"), key=_natural_key)
            if not frames:
                raise click.ClickException("ffmpeg produced no frames from the video")
        elif frames_dir is None:
            raise click.UsageError("provide FRAMES_DIR or use --from-video <path>")
        elif order_file is not None:
            if ctx.get_parameter_source("glob_pattern") == click.core.ParameterSource.COMMANDLINE:
                click.echo("warning: --glob is ignored when --order-file is provided", err=True)
            frames = _load_order_file(order_file, frames_dir)
            if not frames:
                raise click.ClickException(f"no frames listed in {order_file}")
        else:
            frames = sorted(frames_dir.glob(glob_pattern), key=_natural_key)
            if not frames:
                raise click.ClickException(f"no frames matched {glob_pattern!r} in {frames_dir}")

        if frame_size is not None and (frame_w_mm is not None or frame_h_mm is not None):
            raise click.UsageError("--frame-size and --frame-w-mm/--frame-h-mm are mutually exclusive")
        if (frame_w_mm is None) != (frame_h_mm is None):
            raise click.UsageError("--frame-w-mm and --frame-h-mm must be given together")

        w, h = PAPER_SIZES_MM[paper]
        page_size_mm = (h, w) if landscape else (w, h)

        frame_mm = FRAME_SIZE_PRESETS_MM[frame_size] if frame_size is not None else None
        if frame_w_mm is not None:
            frame_mm = (frame_w_mm, frame_h_mm)
        if frame_mm is not None:
            cols, rows = grid_for_frame_size(page_size_mm, margin_mm, frame_mm)

        config = LayoutConfig(
            cols=cols, rows=rows, dpi=dpi, margin_mm=margin_mm, background=background,
            page_size_mm=page_size_mm,
            cut_marks=cut_marks, cell_outline=cell_outline,
            fit=fit,
            fill=fill,
            frame_numbers=frame_numbers,
            frame_number_color=frame_number_color,
            frame_number_offset_mm=frame_number_offset_mm,
            bind_strip_mm=bind_strip_mm,
            bind_strip_color=bind_strip_color,
        )
        pages = render_sheets(frames, config)

        if preview is not None:
            if preview < 1 or preview > len(pages):
                raise click.ClickException(
                    f"--preview {preview} out of range: {len(pages)} sheet(s) available"
                )
            page = pages[preview - 1]
            if output == Path("-"):
                page.save(sys.stdout.buffer, format="PNG")
            else:
                page.save(output, format="PNG", dpi=(dpi, dpi))
                click.echo(f"preview sheet {preview}/{len(pages)} → {output}")
            return

        save_pages(pages, output, fmt=fmt, dpi=config.dpi)
        click.echo(f"wrote {len(pages)} page(s) covering {len(frames)} frame(s) → {output}")


if __name__ == "__main__":
    main()
