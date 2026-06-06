from __future__ import annotations

import pytest
from PIL import Image

from flipbook_maker.tarot import TAROT_DECK, TarotCard, _render_card_panel, render_tarot_zine


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
    from flipbook_maker.layout import save_pages

    pages = render_tarot_zine(seed=7, dpi=72)
    out = tmp_path / "tarot.pdf"
    save_pages(pages, out, fmt="pdf", dpi=72)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:4] == b"%PDF"
