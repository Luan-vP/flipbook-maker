from __future__ import annotations

from pathlib import Path

import click

from flipbook_maker.layout import LayoutConfig, render_sheets, save_pdf


@click.command()
@click.argument("frames_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=Path("flipbook.pdf"),
              show_default=True, help="Output PDF path.")
@click.option("--cols", type=int, default=2, show_default=True, help="Columns per sheet.")
@click.option("--rows", type=int, default=8, show_default=True, help="Rows per sheet.")
@click.option("--dpi", type=int, default=300, show_default=True, help="Output DPI.")
@click.option("--margin-mm", type=float, default=5.0, show_default=True, help="Sheet margin in mm.")
@click.option("--background", type=str, default="white", show_default=True,
              help="Background color (name/hex) OR path to a texture image.")
@click.option("--glob", "glob_pattern", type=str, default="*.png", show_default=True,
              help="Glob pattern for frame files within frames_dir.")
def main(frames_dir: Path, output: Path, cols: int, rows: int, dpi: int, margin_mm: float,
         background: str, glob_pattern: str) -> None:
    """Format flipbook FRAMES_DIR into a printable PDF."""
    frames = sorted(frames_dir.glob(glob_pattern))
    if not frames:
        raise click.ClickException(f"no frames matched {glob_pattern!r} in {frames_dir}")
    config = LayoutConfig(
        cols=cols, rows=rows, dpi=dpi, margin_mm=margin_mm, background=background,
    )
    pages = render_sheets(frames, config)
    save_pdf(pages, output)
    click.echo(f"wrote {len(pages)} page(s) covering {len(frames)} frame(s) → {output}")


if __name__ == "__main__":
    main()
