from __future__ import annotations

from flipbook_maker.tarot import (
    READING_POSITIONS,
    TAROT_DECK,
    TarotCard,
    _render_card_panel,
    render_tarot_reading,
    render_tarot_zine,
)


def test_tarot_deck_count() -> None:
    assert len(TAROT_DECK) == 78


def test_tarot_deck_unique_names() -> None:
    names = [c.name for c in TAROT_DECK]
    assert len(names) == len(set(names))


def test_tarot_deck_all_have_descriptions() -> None:
    for card in TAROT_DECK:
        assert card.description, f"{card.name} has an empty description"


def test_render_tarot_zine_returns_one_page() -> None:
    pages = render_tarot_zine(seed=42, dpi=72)
    assert len(pages) == 1


def test_render_tarot_zine_is_landscape() -> None:
    pages = render_tarot_zine(seed=42, dpi=72)
    w, h = pages[0].size
    assert w > h


def test_render_tarot_zine_is_rgb() -> None:
    pages = render_tarot_zine(seed=42, dpi=72)
    assert pages[0].mode == "RGB"


def test_render_tarot_zine_reproducible() -> None:
    pages_a = render_tarot_zine(seed=42, dpi=72)
    pages_b = render_tarot_zine(seed=42, dpi=72)
    assert list(pages_a[0].getdata()) == list(pages_b[0].getdata())


def test_render_tarot_zine_different_seeds_differ() -> None:
    pages_a = render_tarot_zine(seed=1, dpi=72)
    pages_b = render_tarot_zine(seed=2, dpi=72)
    assert list(pages_a[0].getdata()) != list(pages_b[0].getdata())


def test_render_tarot_zine_no_seed() -> None:
    # Should not raise; output is non-deterministic but valid
    pages = render_tarot_zine(dpi=72)
    assert len(pages) == 1
    assert pages[0].mode == "RGB"


def test_render_card_panel_dimensions() -> None:
    card = TarotCard("Test Card", "A short description for layout testing")
    panel = _render_card_panel(card, 300, 400, dpi=72)
    assert panel.size == (300, 400)


def test_render_card_panel_is_rgb() -> None:
    card = TarotCard("Test Card", "A short description for layout testing")
    panel = _render_card_panel(card, 300, 400, dpi=72)
    assert panel.mode == "RGB"


def test_render_card_panel_background_color() -> None:
    card = TarotCard("Test Card", "A short description for layout testing")
    panel = _render_card_panel(card, 300, 400, dpi=72, background="navy")
    r, g, b = panel.getpixel((0, 0))
    # Navy is (0, 0, 128) — just check it's not black or white
    assert b > 50


def test_render_tarot_zine_custom_colors() -> None:
    pages = render_tarot_zine(seed=10, dpi=72, background="navy", foreground="gold")
    assert pages[0].mode == "RGB"


def test_render_tarot_zine_no_cell_outline() -> None:
    pages = render_tarot_zine(seed=10, dpi=72, cell_outline=False)
    assert len(pages) == 1


def test_render_tarot_zine_save_pdf(tmp_path) -> None:
    from flipbook_maker import save_pages

    pages = render_tarot_zine(seed=7, dpi=72)
    out = tmp_path / "tarot.pdf"
    save_pages(pages, out, fmt="pdf", dpi=72)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:4] == b"%PDF"


def test_render_tarot_zine_print_friendly_is_white() -> None:
    # Black-on-white for printing: the page background should be white.
    pages = render_tarot_zine(seed=42, dpi=72, background="white", foreground="black")
    assert pages[0].getpixel((0, 0)) == (255, 255, 255)


def test_reading_has_three_positions() -> None:
    assert [name for name, _ in READING_POSITIONS] == ["Past", "Present", "Future"]


def test_render_tarot_reading_single_landscape_rgb_page() -> None:
    pages = render_tarot_reading(seed=42, dpi=72)
    assert len(pages) == 1
    assert pages[0].mode == "RGB"
    assert pages[0].width > pages[0].height


def test_render_tarot_reading_reproducible() -> None:
    a = render_tarot_reading(seed=42, dpi=72)
    b = render_tarot_reading(seed=42, dpi=72)
    assert list(a[0].getdata()) == list(b[0].getdata())


def test_render_tarot_reading_different_seeds_differ() -> None:
    a = render_tarot_reading(seed=1, dpi=72)
    b = render_tarot_reading(seed=2, dpi=72)
    assert list(a[0].getdata()) != list(b[0].getdata())


def test_render_tarot_reading_page_numbers_toggle_changes_output() -> None:
    with_nums = render_tarot_reading(seed=3, dpi=72, page_numbers=True)
    without = render_tarot_reading(seed=3, dpi=72, page_numbers=False)
    assert list(with_nums[0].getdata()) != list(without[0].getdata())


def test_cli_default_is_reading(tmp_path) -> None:
    from click.testing import CliRunner

    from flipbook_maker.tarot.cli import tarot

    out = tmp_path / "reading.pdf"
    runner = CliRunner()
    result = runner.invoke(tarot, ["--seed", "42", "--dpi", "72", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_cli_random_flag_runs(tmp_path) -> None:
    from click.testing import CliRunner

    from flipbook_maker.tarot.cli import tarot

    out = tmp_path / "grid.pdf"
    runner = CliRunner()
    result = runner.invoke(tarot, ["--random", "--seed", "42", "--dpi", "72", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_print_flag_runs(tmp_path) -> None:
    from click.testing import CliRunner

    from flipbook_maker.tarot.cli import tarot

    out = tmp_path / "tarot.pdf"
    runner = CliRunner()
    result = runner.invoke(
        tarot, ["--print", "--seed", "42", "--dpi", "72", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_cli_explicit_colors_override_print_flag(tmp_path) -> None:
    # An explicit --background must win even when --print is also passed.
    from click.testing import CliRunner

    from flipbook_maker.tarot.cli import tarot

    out = tmp_path / "tarot.pdf"
    runner = CliRunner()
    result = runner.invoke(
        tarot,
        ["--print", "--background", "navy", "--seed", "1", "--dpi", "72", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
