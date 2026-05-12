---
name: flipbook
description: Build a printable flipbook PDF from a directory of PNG frames using the flipbook_maker package. Use when the user asks to "make a flipbook", "lay out frames for printing", or "generate flipbook print sheets".
---

# flipbook

Compose a directory of PNG frames into an A4-ready PDF using `flipbook_maker`.

## When to use

- The user has a folder of frame PNGs (typically named `frame_001.png`, …) and
  wants a print-ready PDF.
- The user asks about cell size, grid layout, or background customization for
  flipbook printing.

## How to invoke

```bash
flipbook-make <frames_dir> -o <out.pdf> [--cols N] [--rows M] [--background <color|path>]
```

Defaults: `--cols 2 --rows 8`, white background, 300 DPI, 5 mm margin.

## Library surface

```python
from flipbook_maker import LayoutConfig, render_sheets
from flipbook_maker.layout import save_pdf

pages = render_sheets(frame_paths, LayoutConfig(cols=2, rows=8, background="#f5f0e6"))
save_pdf(pages, Path("flipbook.pdf"))
```

## Constraints

- Right-wall alignment is the defining property — don't change `_place_in_cell`
  without preserving it.
- `layout.py` is pure render logic; do not introduce CLI imports or globbing
  there. Filesystem decisions (which files to include, where to write) belong
  in `cli.py` or in the caller.
