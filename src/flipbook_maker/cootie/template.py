from __future__ import annotations

import math
from pathlib import Path
from textwrap import wrap as _wrap

from PIL import Image, ImageColor, ImageDraw, ImageFont

from flipbook_maker.core.paper import PAPER_SIZES_MM
from flipbook_maker.core.units import mm_to_px

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_COLORS = ["red", "blue", "green", "yellow"]

DEFAULT_FORTUNES = [
    "A surprise awaits you soon",
    "Good luck follows your steps",
    "Share kindness freely today",
    "An adventure is on the horizon",
    "You will find what you seek",
    "Creativity blooms within you",
    "A friend brings good news",
    "Your future is bright",
]

# Color display names for labelling sections
_COLOR_DISPLAY = {
    "red": "RED",
    "blue": "BLUE",
    "green": "GREEN",
    "yellow": "YELLOW",
    "pink": "PINK",
    "purple": "PURPLE",
    "orange": "ORANGE",
    "teal": "TEAL",
}

# Darker text colors for light-background sections
_DARK_TEXT = {
    "yellow": "black",
    "white": "black",
    "lime": "black",
    "cyan": "black",
    "pink": "black",
    "lightblue": "black",
}


def _text_color_for(fill: str) -> str:
    return _DARK_TEXT.get(fill.lower(), "white")


def _load_font(size_px: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
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


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    fill,
    width: int = 2,
    dash: int = 12,
    gap: int = 8,
) -> None:
    """Draw a dashed line between two points."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    drawing = True
    while pos < length:
        seg_end = min(pos + (dash if drawing else gap), length)
        if drawing:
            draw.line(
                [
                    (x1 + ux * pos, y1 + uy * pos),
                    (x1 + ux * seg_end, y1 + uy * seg_end),
                ],
                fill=fill,
                width=width,
            )
        pos = seg_end
        drawing = not drawing


def _centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _draw_text_in_triangle(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[float, float]],
    text: str,
    font: ImageFont.ImageFont,
    fill,
    max_width_px: int,
    rotate: int = 0,
) -> None:
    """Render wrapped text centered at triangle centroid, optionally rotated."""
    cx, cy = _centroid(pts)
    # Estimate chars per line from triangle width
    try:
        char_w = draw.textbbox((0, 0), "M", font=font)[2]
    except Exception:
        char_w = max(1, max_width_px // 10)
    chars = max(6, max_width_px // max(1, char_w))
    lines = _wrap(text, width=chars)

    # Measure block
    line_h = draw.textbbox((0, 0), "Mg", font=font)[3] + 2

    if rotate != 0:
        # Render to tmp image, rotate, paste
        block_w = max(
            draw.textbbox((0, 0), ln, font=font)[2] for ln in lines
        ) + 4
        block_h = line_h * len(lines) + 4
        tmp = Image.new("RGBA", (block_w + 8, block_h + 8), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        for i, ln in enumerate(lines):
            lw = td.textbbox((0, 0), ln, font=font)[2]
            td.text(((block_w - lw) // 2 + 4, i * line_h + 4), ln, font=font, fill=fill)
        tmp = tmp.rotate(rotate, expand=True)
        draw._image.paste(tmp, (int(cx - tmp.width // 2), int(cy - tmp.height // 2)), tmp)
    else:
        total_h = line_h * len(lines)
        y = cy - total_h // 2
        for ln in lines:
            lw = draw.textbbox((0, 0), ln, font=font)[2]
            draw.text((cx - lw // 2, y), ln, font=font, fill=fill)
            y += line_h


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_cootie_template(
    fortunes: list[str] | None = None,
    colors: list[str] | None = None,
    dpi: int = 300,
    paper: str = "a4",
    margin_mm: float = 12.0,
    background: str = "white",
    fold_line_color: str = "#aaaaaa",
    show_instructions: bool = True,
) -> list[Image.Image]:
    """Render a printable cootie catcher (fortune teller) template.

    The template prints as a square on the page.  When cut out and folded
    following the dashed fold lines, it becomes a functioning cootie catcher.

    Args:
        fortunes: 8 fortune strings. Defaults to generic placeholder fortunes.
        colors:   4 color names (PIL color strings) for the outer panels.
                  Defaults to red, blue, green, yellow.
        dpi:      Output resolution.
        paper:    Paper size key (a4, letter, …).
        margin_mm: Margin around the square on the page.
        background: Page background color.
        fold_line_color: Color for dashed fold guides.
        show_instructions: Print folding instructions below the square.
    """
    fortunes = (fortunes or DEFAULT_FORTUNES)[:]
    colors = (colors or DEFAULT_COLORS)[:]
    while len(fortunes) < 8:
        fortunes.append("?")
    while len(colors) < 4:
        colors.append("white")
    fortunes = fortunes[:8]
    colors = colors[:4]

    w_mm, h_mm = PAPER_SIZES_MM[paper]
    page_w = mm_to_px(w_mm, dpi)
    page_h = mm_to_px(h_mm, dpi)
    margin = mm_to_px(margin_mm, dpi)

    # Square fits within page, accounting for instruction space below
    instr_reserve = mm_to_px(18.0, dpi) if show_instructions else 0
    sq = min(page_w - 2 * margin, page_h - 2 * margin - instr_reserve)
    ox = (page_w - sq) // 2  # top-left x of square
    oy = margin               # top-left y

    page = Image.new("RGB", (page_w, page_h), ImageColor.getrgb(background))
    draw = ImageDraw.Draw(page)

    # --- Key geometry points (absolute pixel coords) ---
    S = sq
    def pt(nx: float, ny: float) -> tuple[int, int]:
        return (int(ox + nx * S), int(oy + ny * S))

    TL = pt(0, 0)
    TR = pt(1, 0)
    BR = pt(1, 1)
    BL = pt(0, 1)
    T  = pt(0.5, 0)    # top edge midpoint
    R  = pt(1, 0.5)    # right edge midpoint
    B  = pt(0.5, 1)    # bottom edge midpoint
    L  = pt(0, 0.5)    # left edge midpoint
    C  = pt(0.5, 0.5)  # center

    # Midpoints where full diagonals intersect the diamond sides
    M_TL = pt(0.25, 0.25)  # midpoint of T–L segment (NW hypotenuse)
    M_TR = pt(0.75, 0.25)  # midpoint of T–R segment (NE hypotenuse)
    M_BR = pt(0.75, 0.75)  # midpoint of R–B segment (SE hypotenuse)
    M_BL = pt(0.25, 0.75)  # midpoint of L–B segment (SW hypotenuse)

    # ---------------------------------------------------------------------------
    # Fill color sections  (4 triangles inside the center diamond)
    # NW: T, L, C  |  NE: T, R, C  |  SE: B, R, C  |  SW: B, L, C
    # ---------------------------------------------------------------------------
    color_sections = [
        (colors[0], [T, L, C]),   # NW
        (colors[1], [T, R, C]),   # NE
        (colors[2], [B, R, C]),   # SE
        (colors[3], [B, L, C]),   # SW
    ]
    for color, poly in color_sections:
        draw.polygon(poly, fill=ImageColor.getrgb(color))

    # ---------------------------------------------------------------------------
    # Fill fortune sections  (2 sub-triangles per corner = 8 total)
    # Numbered 1-8 going clockwise from top-left corner
    # ---------------------------------------------------------------------------
    fortune_bg = "#f5f5f5"
    fortune_sections = [
        [TL, T, M_TL],    # 1 – NW corner, right sub-triangle
        [TL, L, M_TL],    # 2 – NW corner, bottom sub-triangle
        [TR, T, M_TR],    # 3 – NE corner, left sub-triangle
        [TR, R, M_TR],    # 4 – NE corner, bottom sub-triangle
        [BR, R, M_BR],    # 5 – SE corner, top sub-triangle
        [BR, B, M_BR],    # 6 – SE corner, left sub-triangle
        [BL, B, M_BL],    # 7 – SW corner, right sub-triangle
        [BL, L, M_BL],    # 8 – SW corner, top sub-triangle
    ]
    for poly in fortune_sections:
        draw.polygon(poly, fill=ImageColor.getrgb(fortune_bg))

    # ---------------------------------------------------------------------------
    # Draw square border
    # ---------------------------------------------------------------------------
    border_px = max(2, mm_to_px(0.5, dpi))
    draw.rectangle([TL, BR], outline="black", width=border_px)

    # ---------------------------------------------------------------------------
    # Draw fold lines (dashed)
    # ---------------------------------------------------------------------------
    fold_clr = ImageColor.getrgb(fold_line_color)
    fold_w = max(2, mm_to_px(0.35, dpi))
    fold_lines = [
        (T, L), (T, R), (B, L), (B, R),   # diamond sides
        (TL, BR), (TR, BL),                # full diagonals
        (T, B), (L, R),                    # midlines (diamond internal divisions)
    ]
    for p1, p2 in fold_lines:
        _draw_dashed_line(draw, p1, p2, fill=fold_clr, width=fold_w)

    # ---------------------------------------------------------------------------
    # Label color sections
    # ---------------------------------------------------------------------------
    label_font_px = max(12, mm_to_px(5.0, dpi))
    label_font = _load_font(label_font_px)
    color_label_positions = [
        (colors[0], [T, L, C]),
        (colors[1], [T, R, C]),
        (colors[2], [B, R, C]),
        (colors[3], [B, L, C]),
    ]
    for color, poly in color_label_positions:
        tc = _text_color_for(color)
        label = _COLOR_DISPLAY.get(color.lower(), color.upper()[:6])
        _draw_text_in_triangle(
            draw, poly, label, label_font,
            fill=ImageColor.getrgb(tc),
            max_width_px=int(S * 0.3),
        )

    # ---------------------------------------------------------------------------
    # Label fortune sections with number + fortune text
    # ---------------------------------------------------------------------------
    num_font_px = max(8, mm_to_px(3.5, dpi))
    fortune_font_px = max(6, mm_to_px(2.8, dpi))
    num_font = _load_font(num_font_px)
    fortune_font = _load_font(fortune_font_px)
    fortune_text_color = ImageColor.getrgb("#222222")

    # Rotation angles to keep text readable relative to nearest edge
    fortune_rotations = [45, -45, -45, 45, 45, -45, -45, 45]

    for i, (poly, fortune, rot) in enumerate(
        zip(fortune_sections, fortunes, fortune_rotations)
    ):
        cx, cy = _centroid(poly)
        label = f"{i + 1}"
        nb = draw.textbbox((0, 0), label, font=num_font)
        nw, nh = nb[2] - nb[0], nb[3] - nb[1]
        # number near centroid, shifted slightly toward corner
        draw.text((int(cx - nw // 2), int(cy - nh // 2) - num_font_px // 2), label, font=num_font, fill=fortune_text_color)
        # fortune text below the number
        _draw_text_in_triangle(
            draw, poly, fortune, fortune_font,
            fill=fortune_text_color,
            max_width_px=int(S * 0.22),
            rotate=rot,
        )

    # ---------------------------------------------------------------------------
    # Folding instructions
    # ---------------------------------------------------------------------------
    if show_instructions:
        instr_y = oy + sq + mm_to_px(5.0, dpi)
        instr_font = _load_font(max(8, mm_to_px(3.2, dpi)))
        steps = [
            "How to fold your cootie catcher:",
            "1. Cut out the square.  2. Fold all four corners to the center.",
            "3. Flip over. Fold those corners to the center.  4. Fold in half both ways.",
            "5. Unfold the last fold. Push the four corners together from below.",
        ]
        step_h = max(8, mm_to_px(4.5, dpi))
        for j, step in enumerate(steps):
            sb = draw.textbbox((0, 0), step, font=instr_font)
            sw = sb[2] - sb[0]
            draw.text(
                ((page_w - sw) // 2, instr_y + j * step_h),
                step,
                font=instr_font,
                fill=ImageColor.getrgb("#333333"),
            )

    return [page]
