from __future__ import annotations

from pathlib import Path

import click

from flipbook_maker.core.io import save_pages
from flipbook_maker.core.paper import PAPER_SIZES_MM
from flipbook_maker.cootie.template import DEFAULT_COLORS, DEFAULT_FORTUNES, render_cootie_template


@click.command()
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("cootie_catcher.pdf"),
    show_default=True,
    help="Output PDF or PNG path.",
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
    "--colors",
    type=str,
    default=None,
    help=(
        "Comma-separated list of 4 color names for the outer panels.  "
        f"Default: {','.join(DEFAULT_COLORS)}."
    ),
)
@click.option(
    "--fortunes",
    type=str,
    default=None,
    help="Comma-separated list of 8 fortune strings.  Wrap in quotes.",
)
@click.option(
    "--no-instructions",
    is_flag=True,
    default=False,
    help="Omit the folding instructions printed below the template.",
)
@click.option(
    "--background",
    type=str,
    default="white",
    show_default=True,
    help="Page background color.",
)
def cootie(
    output: Path,
    dpi: int,
    paper: str,
    colors: str | None,
    fortunes: str | None,
    no_instructions: bool,
    background: str,
) -> None:
    """Generate a printable cootie catcher (fortune teller) template.

    Prints a square sheet with fold guides, coloured outer panels, and fortune
    text.  Cut out the square and follow the printed instructions to fold it
    into a working cootie catcher.

    Custom fortunes and colours can be supplied as comma-separated strings:

    \b
        flipbook-cootie --colors "red,blue,green,yellow" \\
            --fortunes "You'll travel far,A gift awaits,..."
    """
    color_list = [c.strip() for c in colors.split(",")] if colors else None
    fortune_list = [f.strip() for f in fortunes.split(",")] if fortunes else None

    pages = render_cootie_template(
        fortunes=fortune_list,
        colors=color_list,
        dpi=dpi,
        paper=paper,
        background=background,
        show_instructions=not no_instructions,
    )
    save_pages(pages, output, fmt="pdf" if str(output).endswith(".pdf") else "png", dpi=dpi)
    click.echo(f"wrote cootie catcher → {output}")


if __name__ == "__main__":
    cootie()
