---
name: tarot-duplex
description: Turn a one-page zine (JPG/PNG or single-page PDF) into a 2-page PDF with a 3-card tarot reading on the back, ready for double-sided printing. Use when the user wants to "put tarot on the back", "make a double-sided zine", "add a reading to print duplex", or back a page with a tarot draw.
---

# tarot-duplex

Back a one-page zine with a tarot reading and emit a print-ready 2-page PDF:
page 1 is the user's front, page 2 is a Past/Present/Future reading sized to
match. Printed double-sided, the reading lands on the back of the page.

## When to use

- The user has a one-page zine (front art) and wants a tarot draw on the reverse
  for duplex printing.
- They mention "double-sided", "on the back", "duplex", or "2-up to fold".

For a reading *in chat* (no print), use the `tarot-reading` skill instead. The
two share seed logic — see Reproducing a chat reading below.

## How to run

Runs in the project environment (needs `flipbook_maker` + Pillow):

```bash
uv run python skills/tarot-duplex/duplex.py FRONT [-o OUT.pdf] [--seed N] [--flip long|short] [--dpi 300]
```

- **`FRONT`** — the one-page zine: `.jpg`/`.png`/etc., or a single-page `.pdf`
  (first page is used).
- **`-o/--output`** — output path (default: `<front>_duplex.pdf`).
- **`--seed N`** — reproducible draw; same seed as `flipbook-tarot --seed N`.
- **`--flip`** — duplex binding edge (see below). Default `long`.
- **`--dpi`** — output raster DPI. Default `300`.

**PDF fronts** need the optional `pdf` extra:

```bash
uv sync --extra pdf            # once
uv run --extra pdf python skills/tarot-duplex/duplex.py front.pdf
```

JPG/PNG fronts need nothing extra.

## Getting the flip right

How the back must be oriented depends on how the printer turns the page:

- **`--flip long`** (default) — long-edge binding, the usual duplex default. The
  back prints upright with no rotation.
- **`--flip short`** — short-edge binding. The back is rotated 180° so it still
  reads upright on the reverse.

If a test print comes out with the back upside-down relative to the front, switch
the flip setting. Suggest the user print one copy to check before a batch.

## Reproducing a chat reading

The back is drawn with the same logic as `render_tarot_reading`, so a reading
revealed via the `tarot-reading` skill (which prints its `seed`) can be put on
the back of a zine exactly:

```bash
uv run python skills/tarot-duplex/duplex.py front.jpg --seed <seed-from-reading>
```

## Notes

- The reading is rendered in the front's orientation (portrait/landscape) and
  resized to the front's exact pixel dimensions so the two pages register when
  printed duplex. A front whose aspect ratio differs greatly from the reading's
  A4 layout will stretch the back slightly.
- PDF fronts are rasterized at `--dpi` (vector content becomes a bitmap on the
  output). For crispest results pass `--dpi 300` or higher.
