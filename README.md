# flipbook-maker

Format a folder of PNG frames into printable A4 flipbook sheets.

Each frame is placed flush-right inside a horizontal cell so the left strip
forms a clean binding/flip edge. Default grid is **2 × 8** (16 frames per A4
page); background is a configurable colour or texture image.

## Install

```bash
pip install -e .[dev]
```

## Use

```bash
flipbook-make frames/ -o flipbook.pdf
flipbook-make frames/ --cols 2 --rows 8 --background "#f5f0e6"
flipbook-make frames/ --background path/to/paper-texture.png
flipbook-make frames/ --paper a3 --landscape
```

Frames are taken in alphanumeric order (`frame_001.png`, `frame_002.png`, …).

### Paper size and orientation

| Flag | Options | Default |
|------|---------|---------|
| `--paper` | `a4`, `a3`, `letter`, `legal` | `a4` |
| `--landscape` / `--portrait` | — | portrait |

Paper sizes in mm:

| Preset | Width × Height (portrait) |
|--------|--------------------------|
| `a4` | 210 × 297 |
| `a3` | 297 × 420 |
| `letter` | 215.9 × 279.4 |
| `legal` | 215.9 × 355.6 |

The default grid is **2 × 8** regardless of paper size. Override with `--cols` / `--rows` when using larger paper.

## Preview

Iterating on `--cols`, `--rows`, or `--background` is faster with a single-sheet preview.
Pass `--preview N` (1-indexed sheet number) to render only that sheet and write it as a PNG,
then exit without producing a PDF:

```bash
# Preview sheet 1 (most common — check layout before a full run)
flipbook-make frames/ --preview 1

# Preview a specific sheet with custom options
flipbook-make frames/ --cols 3 --rows 6 --background "#f5f0e6" --preview 2

# Write preview to a named file
flipbook-make frames/ --preview 1 -o check.png

# Write preview to stdout (pipe to an image viewer)
flipbook-make frames/ --preview 1 -o -
```

When no `-o` is given, the preview is written to `preview.png` in the current directory.

## From video

Skip the manual frame-extraction step by pointing directly at a video file:

```bash
flipbook-make --from-video clip.mp4 -o flipbook.pdf
flipbook-make --from-video clip.mp4 --fps 24 -o flipbook.pdf
```

`--fps N` (default **12**) controls how many frames per second are extracted.
All other flags (`--cols`, `--rows`, `--background`, `--paper`, …) work as usual.
`FRAMES_DIR` must be omitted when `--from-video` is used.

### ffmpeg prerequisite

Frame extraction shells out to [ffmpeg](https://ffmpeg.org/). Install it and
make sure it is on your `PATH` before using `--from-video`:

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

The tool checks for ffmpeg at run time and prints a clear error if it is missing.

## Develop

```bash
pip install -e .[dev]
pytest
ruff check .
```

## Frame numbering

Pass `--frame-numbers` to print a small 1-based index in the left bind strip
of each cell. This helps reassemble the stack after cutting:

```bash
flipbook-make frames/ --frame-numbers
flipbook-make frames/ --frame-numbers --frame-number-color white  # dark backgrounds
flipbook-make frames/ --frame-numbers --frame-number-offset-mm 3.0
```

**Dark-background caveat**: the default colour is black. On a dark background
the number will be unreadable. Pass `--frame-number-color white` (or any CSS
colour / hex string) to override. The tool does not auto-invert.

**Cover/stretch fit modes caveat** (see `--fit`, upcoming): when a frame fills
the full cell width the number may be overdrawn by the frame image. Prefer
`--frame-numbers` with the default `contain` fit mode.

## Layout

The page is divided into `cols × rows` cells. Within each cell the frame is
scaled to fit (preserving aspect ratio) and pasted against the right wall,
vertically centred. Cut along the cell boundaries and bind the left edges.
