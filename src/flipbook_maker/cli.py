from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from flipbook_maker.layout import PAPER_SIZES_MM, LayoutConfig, render_sheets, save_pages


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
@click.argument("frames_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--preview", type=int, default=None, metavar="N", is_eager=True,
              help="Render only sheet N (1-indexed) as a PNG and exit. PDF is not produced.")
@click.option("--format", "fmt", type=click.Choice(["pdf", "png"]), default="pdf",
              show_default=True, is_eager=True, help="Output format.")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              callback=_default_output, is_eager=False,
              help="Output path (PDF file or PNG dir/prefix). Defaults to flipbook.pdf or pages/.")
@click.option("--cols", type=int, default=2, show_default=True, help="Columns per sheet.")
@click.option("--rows", type=int, default=8, show_default=True, help="Rows per sheet.")
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
@click.option("--order-file", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Newline-delimited list of frame paths (absolute or relative to frames_dir).")
def main(ctx: click.Context, frames_dir: Path, preview: int | None, fmt: str, output: Path,
         cols: int, rows: int, dpi: int, margin_mm: float, background: str, glob_pattern: str,
         paper: str, landscape: bool, cut_marks: bool, cell_outline: bool, fit: str,
         order_file: Path | None) -> None:
    """Format flipbook FRAMES_DIR into a printable PDF or PNG pages."""
    if order_file is not None:
        if ctx.get_parameter_source("glob_pattern") == click.core.ParameterSource.COMMANDLINE:
            click.echo("warning: --glob is ignored when --order-file is provided", err=True)
        frames = _load_order_file(order_file, frames_dir)
        if not frames:
            raise click.ClickException(f"no frames listed in {order_file}")
    else:
        frames = sorted(frames_dir.glob(glob_pattern), key=_natural_key)
        if not frames:
            raise click.ClickException(f"no frames matched {glob_pattern!r} in {frames_dir}")
    w, h = PAPER_SIZES_MM[paper]
    page_size_mm = (h, w) if landscape else (w, h)
    config = LayoutConfig(
        cols=cols, rows=rows, dpi=dpi, margin_mm=margin_mm, background=background,
        page_size_mm=page_size_mm,
        cut_marks=cut_marks, cell_outline=cell_outline,
        fit=fit,
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
