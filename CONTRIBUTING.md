# Contributing

## Architecture

`flipbook-maker` is a small Python package with a hexagonal-leaning split:

- `flipbook_maker.layout` — pure layout logic. Builds `PIL.Image` pages from a
  `LayoutConfig` and an ordered list of frame paths. No CLI concerns, no I/O
  beyond reading the listed frames and the background image (if any).
- `flipbook_maker.cli` — Click-based CLI. Parses arguments, calls into
  `layout`, writes the output PDF. Keep argument parsing and user-facing
  messages out of `layout`.

When adding features, prefer extending `LayoutConfig` (a frozen dataclass) and
threading values through `render_sheets`. Avoid sneaking new I/O into the
layout module — load assets in the caller and pass `PIL.Image` objects in.

## Workflow

- Branch from `develop`.
- Open PRs against `develop`. `main` mirrors the last release.
- All PRs run `ruff check` and `pytest` via GitHub Actions; both must pass.
- Tag `@claude` in an issue or PR comment to invoke the Claude Code action.

## Local setup

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check .
```
