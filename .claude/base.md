# Architecture base

Origami-style map of `flipbook-maker`. Other tools (conductr orchestrate, the
architect agent) read this to keep changes coherent.

## Base

A single Python package, `flipbook_maker`, that turns an ordered list of PNG
frames into a multi-page PDF laid out for at-home printing of a flipbook.

## Arms (use-cases)

- **layout** — compose `LayoutConfig` + frame paths into rendered `PIL.Image`
  pages, then serialise to a PDF. Lives in `src/flipbook_maker/layout.py`.
- **cli** — Click entrypoint exposed as the `flipbook-make` console script.
  Lives in `src/flipbook_maker/cli.py`.

## Folds (boundaries we keep clean)

| Fold | What it separates | Rule |
|------|-------------------|------|
| Layout ↔ CLI | pure rendering ↔ user-facing argument plumbing | `layout` never imports `click`, never prints, never reads CLI flags. |
| Layout ↔ Filesystem | rendering ↔ disk I/O | `layout` only opens paths it is *given* (frames, background image). It never globs, never decides what file to write. The caller (CLI, library user) does that. |
| Frame vs cell | source frame ↔ destination cell on the sheet | A cell is sized by `LayoutConfig`; a frame is whatever the user supplies. `_place_in_cell` is the only place the two coordinate spaces meet. |

## Products

- `flipbook-make` CLI (entry point via `pyproject.toml`).
- `flipbook_maker.render_sheets()` / `save_pdf()` — public library surface.

## Invariants

1. **Right-wall alignment.** Frames are pasted flush with the right edge of
   their cell. This is the defining visual property of the format — the left
   strip becomes the bind/flip edge. Anything that touches `_place_in_cell`
   must preserve this.
2. **Aspect ratio is preserved.** Frames are scaled to fit, never stretched.
3. **A4 portrait is the default page.** Other page sizes are allowed via
   `LayoutConfig.page_size_mm` but the CLI does not expose them yet — add a
   flag rather than hard-coding alternatives elsewhere.
4. **`LayoutConfig` is frozen.** Add new options as new fields with sensible
   defaults; don't mutate.
