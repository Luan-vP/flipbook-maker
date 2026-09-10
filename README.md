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

## Web UI — Photos tab

The browser app (`web/`, deployed at flipbook.luanvp.info) has a **Photos** tab
for building a flipbook from a set of stills rather than a video.

```bash
cd web
npm install
npm run dev      # http://localhost:5173
```

**Load and order.** Drop in any number of images (PNG, JPEG, WebP, GIF, BMP,
AVIF) or a single ZIP of them. Files are sorted naturally, so `img2` lands
before `img10`. If your filenames run backwards relative to the animation, tick
**Reverse order**. Drag thumbnails in the filmstrip to reorder by hand.

**Align.** Photos shot by hand never register with each other, so each frame
carries its own position inside a fixed square window:

| Control | Action |
|---|---|
| Drag in the square | Pan |
| Scroll wheel | Zoom |
| <kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd> | Nudge (hold <kbd>Shift</kbd> for coarse) |
| <kbd>[</kbd> <kbd>]</kbd> | Rotate |
| <kbd>n</kbd> / <kbd>p</kbd> | Step frames |

Zoom is relative to a **contain** baseline: 100% shows the whole photo inside
the square, above that crops in.

The **Onion** overlay is what makes registration possible — it draws a
neighbouring frame on top of the current one. `Previous frame` / `Next frame` /
`Both neighbours` blend at the chosen opacity; **Difference vs previous** uses a
difference blend, so anything correctly registered goes black and anything out
of place stays coloured. That is usually the fastest way to line two frames up.

`Copy → next` pushes the current transform onto the following frame and steps
to it — the quickest way to walk a sequence. `Apply to all` pushes it to every
frame.

**Preloading a set.** Re-picking files on every reload gets old during a long
alignment session. Drop your frames in `web/public/preload/<set>/` alongside a
`manifest.json`, then open `?preload=<set>`:

```json
{
  "name": "Phoenix watercolour",
  "rotate": 90,
  "frames": ["frame_01.jpeg", "frame_02.jpeg", "frame_03.jpeg"]
}
```

`frames` is the animation order (so bake any reversal into the list), and the
optional `rotate` is degrees clockwise applied to every frame as a starting
point. `web/public/preload/` is gitignored — these are your own images, not
repo content.

**Export alignment** writes a `manifest.json` sidecar holding the ordering and
every frame's transform, plus the print settings and a description of the
coordinate convention. It is deliberately a superset of the preload manifest:
store it alongside the images, and pointing `?preload=<set>` at that folder
restores the whole session — so the work is not trapped in one browser's
storage. A transform carried in the manifest beats the blanket `rotate`.

**Your alignment is saved automatically.** Transforms are written to
localStorage, namespaced per preload set and keyed by filename, so a reload or
an accidental refresh restores where you were. `Forget saved` discards them and
returns every frame to its starting position.

**Play.** The viewer flips the aligned squares at 1–60 fps, looping,
ping-ponging, or once through. Scrubbing selects that frame in the aligner, so
when a frame stutters you can drop straight into fixing it.

**Rolling paper strips.** Tick **Size cells to paper strips** to lay the
flipbook out on roach-card-sized cells instead of the cols/rows grid. One
dimension is fixed by the paper (**Strip width**, default 16mm); the **Length**
is nominal and allowed to flex by **Flex ±**, because letting it vary is what
lets the cells divide A4 without waste. The solver picks the length in that
range giving the most whole copies, then the least waste, then the closest fit
to your nominal.

With 14 frames, 16mm strips and a 42 ±6mm length it settles on **40 × 16mm —
5 × 17 = 85 cells, 6 complete flipbooks per A4 sheet**, leaving a 24mm blank
strip to the left of each 16mm square image. That strip is the roll/bind edge
the layout is already built around, so `Length runs: Across` is the useful
default; `Down the sheet` puts the long axis vertical instead.

**Cell outlines** are on by default in the Photos tab — with 85 cells to a
sheet you need a line to cut along. Cut guides (both outlines and cut marks)
are stroked at a constant 0.2mm rather than a fixed pixel width, so raising DPI
sharpens them instead of thinning them away.

**Duplicate to fill sheet** repeats the whole sequence for as many complete
copies as the grid holds — in strip mode or on a plain grid. Untick it to set
**Copies** by hand. Printed frame numbers restart at 1 for every copy, so each
pile you cut reads 1..N rather than running on to 84. The readout under the
fieldset always states the resulting cell size, grid, copies and sheet count
before you commit to a build.

**Print.** `Build sheets` bakes the aligned squares and runs them through the
same layout as the CLI — right-wall aligned, left strip for binding — then
`PDF` or `PNGs (ZIP)` downloads them. Frame count sets the sheet count; the
default 2 × 8 grid fits 16 frames per A4 sheet.
