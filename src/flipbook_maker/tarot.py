from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap as _wrap

from PIL import Image, ImageColor, ImageDraw, ImageFont

from flipbook_maker.layout import PAPER_SIZES_MM, save_pages


def _mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / 25.4))


def _load_mono_font(size_px: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size_px)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size_px)
    except TypeError:
        return ImageFont.load_default()


@dataclass(frozen=True)
class TarotCard:
    name: str
    description: str


TAROT_DECK: list[TarotCard] = [
    # Major Arcana
    TarotCard("The Fool", "A new beginning; leap of faith into the unknown"),
    TarotCard("The Magician", "Will and skill united; the power to manifest"),
    TarotCard("The High Priestess", "Hidden wisdom; trust your intuition"),
    TarotCard("The Empress", "Abundance and nature; nurturing creation"),
    TarotCard("The Emperor", "Structure and authority; stability built on logic"),
    TarotCard("The Hierophant", "Tradition and guidance; seek wise counsel"),
    TarotCard("The Lovers", "Choice and union; values aligned in harmony"),
    TarotCard("The Chariot", "Willpower and victory; discipline drives progress"),
    TarotCard("Strength", "Inner courage and compassion; gentle power prevails"),
    TarotCard("The Hermit", "Solitude and reflection; seek the light within"),
    TarotCard("Wheel of Fortune", "Cycles and fate; embrace constant change"),
    TarotCard("Justice", "Balance and truth; actions have consequences"),
    TarotCard("The Hanged Man", "Surrender and new perspective; pause to see clearly"),
    TarotCard("Death", "Transformation and ending; make way for renewal"),
    TarotCard("Temperance", "Balance and patience; blend opposites with care"),
    TarotCard("The Devil", "Shadow and bondage; face what holds you captive"),
    TarotCard("The Tower", "Sudden upheaval; what is false must fall"),
    TarotCard("The Star", "Hope and renewal; light returns after darkness"),
    TarotCard("The Moon", "Illusion and the subconscious; navigate the unknown"),
    TarotCard("The Sun", "Joy and vitality; clarity and success shine forth"),
    TarotCard("Judgement", "Reckoning and awakening; heed the higher call"),
    TarotCard("The World", "Completion and wholeness; the journey fulfilled"),
    # Wands
    TarotCard("Ace of Wands", "A spark of inspiration; new creative potential"),
    TarotCard("Two of Wands", "Planning and vision; the world awaits your move"),
    TarotCard("Three of Wands", "Expansion and foresight; ventures set in motion"),
    TarotCard("Four of Wands", "Celebration and homecoming; harmony achieved"),
    TarotCard("Five of Wands", "Competition and conflict; creative tension rises"),
    TarotCard("Six of Wands", "Victory and recognition; your efforts acclaimed"),
    TarotCard("Seven of Wands", "Stand your ground; defend what you have built"),
    TarotCard("Eight of Wands", "Swift movement; news and action come quickly"),
    TarotCard("Nine of Wands", "Perseverance under strain; nearly there, hold on"),
    TarotCard("Ten of Wands", "Burden and responsibility; you carry too much"),
    TarotCard("Page of Wands", "Enthusiasm and curiosity; a message of adventure"),
    TarotCard("Knight of Wands", "Bold action and daring; rush toward the horizon"),
    TarotCard("Queen of Wands", "Confidence and warmth; magnetic creative force"),
    TarotCard("King of Wands", "Vision and leadership; inspire with bold purpose"),
    # Cups
    TarotCard("Ace of Cups", "An overflow of feeling; love and new beginnings"),
    TarotCard("Two of Cups", "Mutual connection; a bond of equal love forms"),
    TarotCard("Three of Cups", "Celebration and friendship; joy shared together"),
    TarotCard("Four of Cups", "Contemplation and apathy; consider what you ignore"),
    TarotCard("Five of Cups", "Grief and loss; look beyond what has spilled"),
    TarotCard("Six of Cups", "Nostalgia and innocence; gifts from the past return"),
    TarotCard("Seven of Cups", "Fantasy and choice; not all that glitters is real"),
    TarotCard("Eight of Cups", "Walking away; seek deeper meaning beyond comfort"),
    TarotCard("Nine of Cups", "Contentment and wishes; satisfaction draws near"),
    TarotCard("Ten of Cups", "Lasting happiness; family and heart fully at peace"),
    TarotCard("Page of Cups", "Creative dreaming; a tender and intuitive message"),
    TarotCard("Knight of Cups", "Romantic pursuit; follow the heart's quiet calling"),
    TarotCard("Queen of Cups", "Emotional depth and empathy; nurture with wisdom"),
    TarotCard("King of Cups", "Emotional mastery; lead with compassion and calm"),
    # Swords
    TarotCard("Ace of Swords", "Mental clarity; a breakthrough cuts to the truth"),
    TarotCard("Two of Swords", "Indecision and stalemate; remove the blindfold"),
    TarotCard("Three of Swords", "Heartbreak and grief; truth, though it hurts, heals"),
    TarotCard("Four of Swords", "Rest and recovery; retreat to restore your mind"),
    TarotCard("Five of Swords", "Conflict and defeat; choose your battles wisely"),
    TarotCard("Six of Swords", "Transition and movement; sail toward calmer waters"),
    TarotCard("Seven of Swords", "Strategy and deception; act with careful cunning"),
    TarotCard("Eight of Swords", "Feeling trapped by thought; the bonds are your own"),
    TarotCard("Nine of Swords", "Anxiety and dread; fears loom larger in the dark"),
    TarotCard("Ten of Swords", "Endings and rock bottom; it is over; now rebuild"),
    TarotCard("Page of Swords", "Curiosity and vigilance; gather facts before acting"),
    TarotCard("Knight of Swords", "Charging ahead; act swiftly before you overthink"),
    TarotCard("Queen of Swords", "Clear intellect and directness; speak what is true"),
    TarotCard("King of Swords", "Authority of mind; lead with ethics and precision"),
    # Pentacles
    TarotCard("Ace of Pentacles", "Material beginnings; a seed of prosperity planted"),
    TarotCard("Two of Pentacles", "Juggling and balance; manage change with grace"),
    TarotCard("Three of Pentacles", "Collaboration and craft; great work needs teamwork"),
    TarotCard("Four of Pentacles", "Security and control; loosen the grip on comfort"),
    TarotCard("Five of Pentacles", "Hardship and lack; help is closer than it seems"),
    TarotCard("Six of Pentacles", "Generosity and fairness; give and receive freely"),
    TarotCard("Seven of Pentacles", "Investment and patience; growth takes time to show"),
    TarotCard("Eight of Pentacles", "Diligence and mastery; hone your craft with care"),
    TarotCard("Nine of Pentacles", "Abundance and self-reliance; enjoy your harvest"),
    TarotCard("Ten of Pentacles", "Legacy and lasting wealth; roots run deep and true"),
    TarotCard("Page of Pentacles", "Study and ambition; plant seeds of future skill"),
    TarotCard("Knight of Pentacles", "Methodical effort; slow and steady brings results"),
    TarotCard("Queen of Pentacles", "Practical nurturing; tend your world with loving care"),
    TarotCard("King of Pentacles", "Mastery of the material; lead through steady prosperity"),
]


def _render_card_panel(
    card: TarotCard,
    cell_w: int,
    cell_h: int,
    dpi: int = 300,
    background: str = "black",
    foreground: str = "white",
) -> Image.Image:
    panel = Image.new("RGB", (cell_w, cell_h), ImageColor.getrgb(background))
    draw = ImageDraw.Draw(panel)
    fg = ImageColor.getrgb(foreground)

    pad_px = _mm_to_px(4.0, dpi)
    content_w = cell_w - 2 * pad_px

    name_size = _mm_to_px(5.5, dpi)
    desc_size = _mm_to_px(3.5, dpi)
    name_font = _load_mono_font(name_size)
    desc_font = _load_mono_font(desc_size)

    # Measure character width to estimate wrap width
    char_bbox = draw.textbbox((0, 0), "M", font=desc_font)
    char_w = max(1, char_bbox[2] - char_bbox[0])
    max_chars = max(10, content_w // char_w)
    desc_lines = _wrap(card.description, width=max_chars)

    name_bbox = draw.textbbox((0, 0), card.name, font=name_font)
    name_w = name_bbox[2] - name_bbox[0]
    name_h = name_bbox[3] - name_bbox[1]

    line_ref = draw.textbbox((0, 0), "Mg", font=desc_font)
    line_h = line_ref[3] - line_ref[1]
    line_gap = max(2, _mm_to_px(1.0, dpi))

    desc_block_h = len(desc_lines) * line_h + max(0, len(desc_lines) - 1) * line_gap

    rule_gap = _mm_to_px(2.0, dpi)
    rule_h = max(1, _mm_to_px(0.4, dpi))
    block_h = rule_h + rule_gap + name_h + rule_gap + rule_h + rule_gap + desc_block_h

    y = (cell_h - block_h) // 2

    # Inset decorative border
    border_inset = _mm_to_px(2.0, dpi)
    border_w = max(1, _mm_to_px(0.3, dpi))
    draw.rectangle(
        [(border_inset, border_inset), (cell_w - border_inset, cell_h - border_inset)],
        outline=fg,
        width=border_w,
    )

    # Rule, name, rule, description — all horizontally centered
    rule_x0 = pad_px + content_w // 6
    rule_x1 = cell_w - pad_px - content_w // 6
    draw.line([(rule_x0, y + rule_h // 2), (rule_x1, y + rule_h // 2)], fill=fg, width=rule_h)
    y += rule_h + rule_gap

    draw.text(((cell_w - name_w) // 2, y), card.name, font=name_font, fill=fg)
    y += name_h + rule_gap

    draw.line([(rule_x0, y + rule_h // 2), (rule_x1, y + rule_h // 2)], fill=fg, width=rule_h)
    y += rule_h + rule_gap

    for line in desc_lines:
        lb = draw.textbbox((0, 0), line, font=desc_font)
        draw.text(((cell_w - (lb[2] - lb[0])) // 2, y), line, font=desc_font, fill=fg)
        y += line_h + line_gap

    return panel


def render_tarot_zine(
    seed: int | None = None,
    dpi: int = 300,
    cols: int = 4,
    rows: int = 2,
    paper: str = "a4",
    landscape: bool = True,
    margin_mm: float = 5.0,
    background: str = "black",
    foreground: str = "white",
    cell_outline: bool = True,
) -> list[Image.Image]:
    """Render one landscape sheet with cols×rows randomly selected tarot card panels."""
    rng = random.Random(seed)
    cards = rng.sample(TAROT_DECK, cols * rows)

    w_mm, h_mm = PAPER_SIZES_MM[paper]
    if landscape:
        w_mm, h_mm = h_mm, w_mm

    page_w = _mm_to_px(w_mm, dpi)
    page_h = _mm_to_px(h_mm, dpi)
    margin = _mm_to_px(margin_mm, dpi)

    cell_w = (page_w - 2 * margin) // cols
    cell_h = (page_h - 2 * margin) // rows

    page = Image.new("RGB", (page_w, page_h), ImageColor.getrgb(background))
    draw = ImageDraw.Draw(page)

    for i, card in enumerate(cards):
        row, col = divmod(i, cols)
        x = margin + col * cell_w
        y = margin + row * cell_h
        panel = _render_card_panel(card, cell_w, cell_h, dpi, background, foreground)
        page.paste(panel, (x, y))
        if cell_outline:
            outline_px = max(1, _mm_to_px(0.2, dpi))
            draw.rectangle(
                [(x, y), (x + cell_w, y + cell_h)],
                outline=ImageColor.getrgb(foreground),
                width=outline_px,
            )

    return [page]


READING_POSITIONS: list[tuple[str, str]] = [
    ("Past", "What has shaped this moment"),
    ("Present", "Where you stand now"),
    ("Future", "Where the current path leads"),
]


# Booklet page number -> (row, col, rotate180) on the flat sheet, for the
# classic one-cut 8-page zine fold. The top row is printed upside down so the
# pages read 1 -> 8 once the sheet is folded and the centre crease is cut.
_ZINE_IMPOSITION: dict[int, tuple[int, int, bool]] = {
    1: (1, 3, False),  # front cover
    2: (0, 3, True),
    3: (0, 2, True),
    4: (0, 1, True),
    5: (0, 0, True),
    6: (1, 0, False),
    7: (1, 1, False),
    8: (1, 2, False),  # back
}


def _stamp_page_number(panel: Image.Image, number: int, dpi: int, foreground: str) -> None:
    draw = ImageDraw.Draw(panel)
    font = _load_mono_font(_mm_to_px(2.8, dpi))
    label = str(number)
    bbox = draw.textbbox((0, 0), label, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    edge = _mm_to_px(4.0, dpi)
    draw.text(
        ((panel.width - w) // 2, panel.height - edge - h),
        label,
        font=font,
        fill=ImageColor.getrgb(foreground),
    )


def render_tarot_reading(
    seed: int | None = None,
    dpi: int = 300,
    paper: str = "a4",
    landscape: bool = True,
    margin_mm: float = 5.0,
    background: str = "black",
    foreground: str = "white",
    cell_outline: bool = True,
    page_numbers: bool = True,
) -> list[Image.Image]:
    """Render a 3-card Past/Present/Future reading as an 8-page foldable zine.

    Three cards are drawn at random. The eight booklet pages are imposed onto a
    single landscape sheet in one-cut zine order so that, once folded, they read
    1 -> 8: a cover, then each position followed by the card drawn for it, then a
    closing page.
    """
    rng = random.Random(seed)
    past, present, future = rng.sample(TAROT_DECK, 3)

    # (name, description) for booklet pages 1..8, in reading order.
    booklet: list[tuple[str, str]] = [
        ("Tarot", "A three-card reading"),                   # 1 front cover
        READING_POSITIONS[0],                                # 2 Past
        (past.name, past.description),                       # 3 Past card
        READING_POSITIONS[1],                                # 4 Present
        (present.name, present.description),                 # 5 Present card
        READING_POSITIONS[2],                                # 6 Future
        (future.name, future.description),                   # 7 Future card
        ("Tarot", "fold · cut centre · read in order"),  # 8 back
    ]

    w_mm, h_mm = PAPER_SIZES_MM[paper]
    if landscape:
        w_mm, h_mm = h_mm, w_mm
    page_w = _mm_to_px(w_mm, dpi)
    page_h = _mm_to_px(h_mm, dpi)
    margin = _mm_to_px(margin_mm, dpi)
    cols, rows = 4, 2
    cell_w = (page_w - 2 * margin) // cols
    cell_h = (page_h - 2 * margin) // rows

    sheet = Image.new("RGB", (page_w, page_h), ImageColor.getrgb(background))
    draw = ImageDraw.Draw(sheet)

    for page_no, (name, desc) in enumerate(booklet, start=1):
        panel = _render_card_panel(
            TarotCard(name, desc), cell_w, cell_h, dpi, background, foreground
        )
        if page_numbers:
            _stamp_page_number(panel, page_no, dpi, foreground)
        row, col, rotate = _ZINE_IMPOSITION[page_no]
        if rotate:
            panel = panel.rotate(180)
        x = margin + col * cell_w
        y = margin + row * cell_h
        sheet.paste(panel, (x, y))
        if cell_outline:
            outline_px = max(1, _mm_to_px(0.2, dpi))
            draw.rectangle(
                [(x, y), (x + cell_w, y + cell_h)],
                outline=ImageColor.getrgb(foreground),
                width=outline_px,
            )

    return [sheet]
