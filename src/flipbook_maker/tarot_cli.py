from __future__ import annotations

from pathlib import Path

import click

from flipbook_maker.layout import PAPER_SIZES_MM, save_pages
from flipbook_maker.tarot import render_tarot_zine


@click.command()
@click.option("--seed", type=int, default=None, help="Random seed for reproducible card selection.")
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("tarot_zine.pdf"),
    show_default=True,
    help="Output PDF path.",
)
@click.option("--dpi", type=int, default=300, show_default=True, help="Output DPI.")
@click.option(
    "--paper",
    type=click.Choice(list(PAPER_SIZES_MM.keys())),
    default="a4",
    show_default=True,
    help="Paper size preset.",
)
@click.option(
    "-p", "--print", "print_friendly", is_flag=True, default=False,
    help="Print-friendly black-on-white (saves ink). Overridden by explicit "
         "--background/--foreground.",
)
@click.option("--background", type=str, default=None,
              help="Background color (name or hex). Default: black (white with --print).")
@click.option("--foreground", type=str, default=None,
              help="Text and border color (name or hex). Default: white (black with --print).")
@click.option("--no-cell-outline", is_flag=True, default=False,
              help="Omit the cut-guide outlines between panels.")
def tarot(
    seed: int | None,
    output: Path,
    dpi: int,
    paper: str,
    print_friendly: bool,
    background: str | None,
    foreground: str | None,
    no_cell_outline: bool,
) -> None:
    """Generate an 8-panel tarot zine on a single landscape sheet.

    Prints one A4 landscape page with 8 randomly selected tarot cards arranged
    in a 4x2 grid, ready to fold into a t-fold zine. Each panel shows the card
    name and a short description centered in monospace text.

    Use --print for a black-on-white sheet that is easy on printer ink.
    """
    default_bg, default_fg = ("white", "black") if print_friendly else ("black", "white")
    background = background or default_bg
    foreground = foreground or default_fg
    pages = render_tarot_zine(
        seed=seed,
        dpi=dpi,
        paper=paper,
        landscape=True,
        background=background,
        foreground=foreground,
        cell_outline=not no_cell_outline,
    )
    save_pages(pages, output, fmt="pdf", dpi=dpi)
    click.echo(f"wrote tarot zine → {output}")


if __name__ == "__main__":
    tarot()
