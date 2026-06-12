# flipbook-maker: Comprehensive Specification

## 1. Overview

**flipbook-maker** converts ordered sequences of image frames into printable, multi-page PDF flipbook layouts designed for at-home assembly. Secondary tools generate tarot-card zines and cootie-catcher fortune-tellers using the same rendering infrastructure.

---

## 2. Architecture

### 2.1 Layer Model

| Layer | Responsibility |
|---|---|
| Pure Logic | Image compositing, layout maths — no I/O, no UI |
| I/O | PDF/PNG serialisation, filesystem helpers |
| Interface | CLI argument parsing, frame discovery, user feedback |
| Extensions | Tarot, cootie-catcher generators built on the same I/O layer |

**Invariants:**
- The layout layer never imports CLI/interface concerns.
- `LayoutConfig` is frozen/immutable; callers create a new instance to change a parameter.
- All physical measurements flow through a single `mm_to_px(mm, dpi)` conversion.

### 2.2 Source Tree (Python reference implementation)

```
src/flipbook_maker/
  __init__.py           ← public API re-exports
  flipbook/
    cli.py              ← flipbook-make entry point
    layout.py           ← core rendering (pure logic)
  tarot/
    cli.py              ← flipbook-tarot entry point
    deck.py             ← 78-card deck data
    render.py           ← card-panel compositing
  cootie/
    cli.py              ← flipbook-cootie entry point
    template.py         ← cootie-catcher geometry
  core/
    units.py            ← mm_to_px
    paper.py            ← PAPER_SIZES_MM constant
    io.py               ← save_pages / save_pdf
```

---

## 3. Data Types

### 3.1 FitMode

```
"contain" | "cover" | "stretch"
```

| Value | Behaviour |
|---|---|
| `contain` | Scale uniformly so the entire frame fits inside the usable cell area; pad the remainder with the background. Flush-right. |
| `cover` | Scale uniformly so the frame fills the entire usable cell area; crop any overflow from the center. Flush-right. |
| `stretch` | Scale non-uniformly to fill the usable cell area exactly. |

### 3.2 LayoutConfig

Frozen value object. All physical dimensions are in millimetres at construction time and converted once to pixels via `mm_to_px`.

| Field | Type | Default | Constraint |
|---|---|---|---|
| `cols` | integer | 2 | ≥ 1 |
| `rows` | integer | 8 | ≥ 1 |
| `dpi` | integer | 300 | ≥ 72 |
| `margin_mm` | float | 5.0 | ≥ 0 |
| `background` | string \| path | `"white"` | CSS colour name / hex string, or path to an image file |
| `page_size_mm` | [width, height] | A4 = [210, 297] | width > 0, height > 0 |
| `cut_marks` | boolean | false | |
| `cell_outline` | boolean | false | |
| `fit` | FitMode | `"contain"` | |
| `frame_numbers` | boolean | false | |
| `frame_number_color` | string | `"black"` | CSS colour |
| `frame_number_offset_mm` | float | 2.0 | ≥ 0 |
| `bind_strip_mm` | float | 0.0 | ≥ 0 |
| `bind_strip_color` | string \| null | null | CSS colour or null |

**Derived properties (computed from the above):**

```
page_px        → [round(page_size_mm[0] * dpi / 25.4),
                   round(page_size_mm[1] * dpi / 25.4)]

margin_px      → round(margin_mm * dpi / 25.4)

bind_strip_px  → round(bind_strip_mm * dpi / 25.4)

cell_px        → [floor((page_px[0] - 2*margin_px) / cols),
                   floor((page_px[1] - 2*margin_px) / rows)]

usable_cell_px → [cell_px[0] - bind_strip_px, cell_px[1]]
```

### 3.3 Paper Sizes

```
PAPER_SIZES_MM = {
  "a4":     [210.0, 297.0],
  "a3":     [297.0, 420.0],
  "letter": [215.9, 279.4],
  "legal":  [215.9, 355.6],
}
```

Landscape orientation swaps width and height: `[height, width]`.

---

## 4. Core Rendering Algorithm

### 4.1 render_sheets(frames, config) → Page[]

```
pages       ← []
cells_per_page ← config.cols × config.rows
current_page   ← new_blank_page(config)
cell_index     ← 0

for frame in frames:
  if cell_index == cells_per_page:
    pages.append(current_page)
    current_page ← new_blank_page(config)
    cell_index   ← 0

  col ← cell_index % config.cols
  row ← floor(cell_index / config.cols)

  cell_image ← render_cell(frame, config)

  x ← config.margin_px + col × config.cell_px[0]
  y ← config.margin_px + row × config.cell_px[1]
  paste(current_page, cell_image, at=(x, y))

  cell_index ← cell_index + 1

if cell_index > 0:
  pages.append(current_page)

for page in pages:
  if config.cut_marks:  draw_cut_marks(page, config)
  if config.cell_outline: draw_cell_outlines(page, config)

return pages
```

### 4.2 new_blank_page(config) → Image

1. Create RGBA image of `config.page_px` dimensions.
2. If `config.background` is an image path → load and resize (LANCZOS) to `page_px`.
3. Otherwise → fill with `config.background` colour.

### 4.3 render_cell(frame_path, config) → Image

1. Create RGBA cell of `config.cell_px` dimensions, filled with background colour/image (cropped to cell).
2. If `bind_strip_px > 0` and `bind_strip_color` is set → fill leftmost `bind_strip_px` columns with `bind_strip_color`.
3. Load frame image; apply `fit` mode to place within usable area (see §4.4).
4. If `config.frame_numbers` → render the 1-based frame index as text (see §4.5).
5. Return cell image.

### 4.4 Frame Placement (fit modes)

All modes flush the frame to the **right wall** of the cell: `paste_x = cell_px[0] - placed_width`.

**usable_w** = `cell_px[0] - bind_strip_px`
**usable_h** = `cell_px[1]`

**contain:**
```
scale     = min(usable_w / frame_w, usable_h / frame_h)
placed_w  = round(frame_w * scale)
placed_h  = round(frame_h * scale)
paste_x   = cell_px[0] - placed_w          ← flush right
paste_y   = round((usable_h - placed_h) / 2)  ← vertically centred
resize frame to (placed_w, placed_h) using LANCZOS
```

**cover:**
```
scale     = max(usable_w / frame_w, usable_h / frame_h)
crop_w    = round(usable_w / scale)
crop_h    = round(usable_h / scale)
crop_x    = round((frame_w - crop_w) / 2)
crop_y    = round((frame_h - crop_h) / 2)
cropped   = frame[crop_x : crop_x+crop_w, crop_y : crop_y+crop_h]
resized   = resize(cropped, (usable_w, usable_h), LANCZOS)
paste_x   = bind_strip_px
paste_y   = 0
```

**stretch:**
```
resized   = resize(frame, (usable_w, usable_h), LANCZOS)
paste_x   = bind_strip_px
paste_y   = 0
```

### 4.5 Frame Number Rendering

```
text          ← str(1-based frame index)
offset_px     ← max(frame_number_offset_mm → px, bind_strip_px / 2)  if bind strip present
              ← frame_number_offset_mm → px                           otherwise
text_x        ← cell_x + offset_px
text_y        ← cell_y + (cell_px[1] - text_height) / 2
draw text in frame_number_color at (text_x, text_y)
```

### 4.6 Cut Marks

Drawn at each corner of every cell using short tick lines (length ≈ 3 mm converted to px) in black. Ticks are drawn outside the cell boundary (into the margin) along both axes.

### 4.7 Cell Outlines

1-pixel border drawn around every cell rectangle.

---

## 5. Unit Conversion

```
mm_to_px(mm, dpi) → int:
    return round(mm * dpi / 25.4)
```

---

## 6. Frame Discovery & Sorting

### 6.1 Natural Alphanumeric Sort

Filenames are split into alternating text/number chunks; numeric chunks are sorted numerically, text chunks lexicographically (case-insensitive).

```
"frame_10.png" → ["frame_", 10, ".png"]
"frame_2.png"  → ["frame_", 2, ".png"]
"frame_2" < "frame_10"   ✓ (numeric comparison on the 2/10 part)
```

### 6.2 Discovery Methods (in priority order)

| Source | Description |
|---|---|
| `order_file` | Newline-delimited file of frame paths (absolute or relative to the order file). Glob and directory are ignored. |
| `frames_dir` | Directory path; glob pattern applied (default `*.png`), results natural-sorted. |
| `from_video` | ffmpeg extraction to temp directory, frames natural-sorted. |

### 6.3 Video Extraction (ffmpeg)

```
ffmpeg -y -i <video_path> -vf fps=<fps> <tempdir>/frame_%04d.png
```

Requires `ffmpeg` on `PATH`. On failure, stderr is surfaced to the user.

---

## 7. I/O

### 7.1 save_pages(pages, output_path, format, dpi)

| format | Behaviour |
|---|---|
| `"pdf"` | All pages saved as a single multi-page PDF. `output_path` is the file path. |
| `"png"` | Each page saved as a separate PNG. If `output_path` has no extension, treat as directory and create `page_001.png`, `page_002.png`, … inside it. |

DPI metadata is embedded in both formats.

### 7.2 save_pdf(pages, output_path, dpi)

Convenience wrapper: calls `save_pages(..., format="pdf", ...)`.

---

## 8. CLI — flipbook-make

### 8.1 Signature

```
flipbook-make [FRAMES_DIR] [OPTIONS]
```

`FRAMES_DIR` is mutually exclusive with `--from-video`.

### 8.2 Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `-o / --output` | path | `flipbook.pdf` or `pages/` | Output destination |
| `--cols` | int | 2 | Grid columns |
| `--rows` | int | 8 | Grid rows |
| `--dpi` | int | 300 | Output resolution |
| `--margin-mm` | float | 5.0 | Sheet margin (mm) |
| `--background` | string | `"white"` | Colour or image path |
| `--paper` | choice | `"a4"` | `a4 \| a3 \| letter \| legal` |
| `--landscape` | flag | false | Swap page dimensions |
| `--portrait` | flag | true | Portrait orientation |
| `--format` | choice | `"pdf"` | `pdf \| png` |
| `--fit` | choice | `"contain"` | `contain \| cover \| stretch` |
| `--glob` | string | `"*.png"` | Frame filename glob |
| `--preview` | int | — | Render only sheet N (1-indexed) as PNG |
| `--from-video` | path | — | Extract frames from video via ffmpeg |
| `--fps` | int | 12 | Frame rate for `--from-video` |
| `--order-file` | path | — | Newline-delimited frame list |
| `--cut-marks` | flag | false | Draw cut-guide ticks |
| `--cell-outline` | flag | false | Draw cell borders |
| `--frame-numbers` | flag | false | Print 1-based indices |
| `--frame-number-color` | string | `"black"` | Frame index colour |
| `--frame-number-offset-mm` | float | 2.0 | Index offset from left edge (mm) |
| `--bind-mm` | float | 0.0 | Bind-strip width (mm) |
| `--bind-color` | string | — | Bind-strip fill colour |

### 8.3 Mutual Exclusions

- `FRAMES_DIR` and `--from-video` are mutually exclusive.
- `--order-file` and `--from-video` are mutually exclusive.

### 8.4 Default Output Paths

| Condition | Default |
|---|---|
| `--format pdf` (default) | `flipbook.pdf` |
| `--format png` | `pages/` (directory) |
| `--preview` set | `preview.png` |

### 8.5 Preview Mode

When `--preview N` is provided:
- Only sheet N (1-indexed) is rendered.
- Output is always PNG regardless of `--format`.
- If N is out of range, exit with error: `"preview N out of range: M sheet(s) available"`.

---

## 9. CLI — flipbook-tarot

### 9.1 Signature

```
flipbook-tarot [OPTIONS]
```

### 9.2 Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `-o / --output` | path | `tarot_zine.pdf` | Output PDF |
| `--seed` | int | — | RNG seed for reproducibility |
| `--dpi` | int | 300 | Output resolution |
| `--paper` | choice | `"a4"` | Paper preset |
| `-p / --print` | flag | false | Ink-friendly (black on white) |
| `--background` | string | — | Background colour override |
| `--foreground` | string | — | Text/border colour override |
| `--no-cell-outline` | flag | false | Omit cell borders |
| `--random` | flag | false | 4×2 grid of 8 random cards (landscape) |
| `--no-page-numbers` | flag | false | Omit booklet page numbers |

### 9.3 Modes

**Default — 3-card reading zine (8 pages, t-fold):**

| Page | Content |
|---|---|
| 1 | Cover — title "Tarot — A three-card reading" |
| 2–3 | Past card (name + description) |
| 4–5 | Present card |
| 6–7 | Future card |
| 8 | Back — "fold · cut centre · read in order" |

**--random — 4×2 landscape grid:**

Eight randomly-selected cards rendered as a single-sheet 4×2 grid.

### 9.4 Deck

78 cards:
- **Major Arcana (22):** The Fool through The World.
- **Minor Arcana (56):** Ace–10, Page, Knight, Queen, King × Wands, Cups, Swords, Pentacles.

Each card has: `name` (string), `description` (string).

---

## 10. CLI — flipbook-cootie

### 10.1 Signature

```
flipbook-cootie [OPTIONS]
```

### 10.2 Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `-o / --output` | path | `cootie_catcher.pdf` | Output PDF |
| `--dpi` | int | 300 | Output resolution |
| `--paper` | choice | `"a4"` | Paper preset |
| `--colors` | string | `"red,blue,green,yellow"` | 4 outer panel colours (comma-separated) |
| `--fortunes` | string | *(8 defaults)* | 8 fortune strings (comma-separated) |
| `--no-instructions` | flag | false | Omit folding instructions |
| `--background` | string | `"white"` | Page background colour |

### 10.3 Geometry

A square template centred on the page:
- **4 outer triangles** (NW, NE, SE, SW): filled with the 4 panel colours; labelled with colour names.
- **8 fortune triangles** (2 per corner): numbered 1–8; each contains one fortune string rotated ±45° to align with its edge.
- **Fold lines**: diamond diagonals (dashed) and midlines (dashed).
- **Instructions block** below the square (step-by-step folding guide).

---

## 11. Error Catalogue

| Condition | Message Pattern |
|---|---|
| No frames found | `"no frames matched '{glob}' in {dir}"` |
| `FRAMES_DIR` + `--from-video` | `"FRAMES_DIR and --from-video are mutually exclusive"` |
| `--order-file` + `--from-video` | `"--order-file and --from-video are mutually exclusive"` |
| ffmpeg missing | `"ffmpeg not found on PATH"` |
| ffmpeg non-zero exit | `"ffmpeg failed: {stderr}"` |
| `--preview` out of range | `"preview {N} out of range: {M} sheet(s) available"` |
| Frame missing (order file) | `"frame not found: {path} (listed in order file)"` |
| Invalid background | `"background must be a colour name/hex or an image path"` |
| Unknown output format | `"unknown format; expected 'pdf' or 'png'"` |

---

## 12. Public Library API

```python
from flipbook_maker import (
    LayoutConfig,    # dataclass(frozen=True)
    render_sheets,   # (frames: list[Path], config: LayoutConfig) → list[Image]
    save_pages,      # (pages, out: Path, fmt="pdf", dpi=300) → None
    save_pdf,        # (pages, out: Path, dpi=300) → None
    PAPER_SIZES_MM,  # dict[str, tuple[float, float]]
    FitMode,         # Literal["contain","cover","stretch"]
)
```

---

## 13. Web Version Specification

This section describes a TypeScript/browser implementation that achieves complete **functional parity** with the Python CLI, running entirely client-side with no server required.

### 13.1 Goals

- Static HTML + JS bundle; no backend.
- Accepts PNG frame uploads (multiple files or a ZIP archive).
- Renders flipbooks in the browser using Canvas 2D.
- Outputs a downloadable PDF (multi-page) or PNG sequence (zipped).
- Exposes the same configuration surface as the CLI.
- Optional tarot and cootie-catcher generators.

### 13.2 Technology Stack

| Concern | Library |
|---|---|
| Language | TypeScript |
| Bundler | Vite (static build) |
| PDF generation | jsPDF |
| ZIP input/output | JSZip |
| Image compositing | Canvas 2D API (OffscreenCanvas where available) |
| UI framework | Vanilla HTML/CSS (no framework dependency) |

### 13.3 Module Map

```
web/
  index.html
  src/
    main.ts                ← entry point; wires UI to core
    core/
      units.ts             ← mm_to_px(mm, dpi): number
      paper.ts             ← PAPER_SIZES_MM, PaperKey type
      layout.ts            ← LayoutConfig, render_sheets, render_cell
      io.ts                ← save_pdf, save_pages (download triggers)
      sort.ts              ← naturalSort(paths)
    ui/
      controls.ts          ← reads form values → LayoutConfig
      upload.ts            ← file-input / ZIP handling → File[]
      preview.ts           ← renders preview canvas in the page
      progress.ts          ← progress bar updates
    tarot/
      deck.ts              ← TAROT_DECK constant (78 cards)
      render.ts            ← renderTarotZine / renderTarotGrid
    cootie/
      template.ts          ← renderCooticeCatcher
  public/
    favicon.ico
  vite.config.ts
  tsconfig.json
  package.json
```

### 13.4 core/units.ts

```typescript
export function mmToPx(mm: number, dpi: number): number {
  return Math.round((mm * dpi) / 25.4);
}
```

### 13.5 core/paper.ts

```typescript
export const PAPER_SIZES_MM: Record<string, [number, number]> = {
  a4:     [210,   297  ],
  a3:     [297,   420  ],
  letter: [215.9, 279.4],
  legal:  [215.9, 355.6],
};
export type PaperKey = keyof typeof PAPER_SIZES_MM;
```

### 13.6 core/layout.ts

```typescript
export type FitMode = "contain" | "cover" | "stretch";

export interface LayoutConfig {
  cols:                   number;
  rows:                   number;
  dpi:                    number;
  marginMm:               number;
  background:             string;       // CSS colour OR data-URL of image
  pageSizeMm:             [number, number];
  cutMarks:               boolean;
  cellOutline:            boolean;
  fit:                    FitMode;
  frameNumbers:           boolean;
  frameNumberColor:       string;
  frameNumberOffsetMm:    number;
  bindStripMm:            number;
  bindStripColor:         string | null;
}

export const DEFAULT_CONFIG: LayoutConfig = {
  cols: 2, rows: 8, dpi: 150,
  marginMm: 5, background: "white",
  pageSizeMm: [210, 297],
  cutMarks: false, cellOutline: false,
  fit: "contain", frameNumbers: false,
  frameNumberColor: "black", frameNumberOffsetMm: 2,
  bindStripMm: 0, bindStripColor: null,
};

// Returns one OffscreenCanvas per page
export async function renderSheets(
  frames: ImageBitmap[],
  config: LayoutConfig,
): Promise<OffscreenCanvas[]>
```

**renderSheets implementation notes:**
- Use `OffscreenCanvas` (fall back to `HTMLCanvasElement` for Safari).
- Each canvas is `pagePx[0] × pagePx[1]` at the logical pixel scale.
- Background: if `config.background` starts with `data:` or is a URL, draw as image; otherwise use as CSS fill colour.
- Cell loop identical to §4.1.
- After all cells placed, add cut marks / outlines if requested.

### 13.7 core/io.ts

```typescript
// Triggers browser download of a PDF file
export async function savePdf(
  canvases: OffscreenCanvas[],
  filename: string,
  config: LayoutConfig,
): Promise<void>

// Triggers browser download of a ZIP containing numbered PNGs
export async function savePages(
  canvases: OffscreenCanvas[],
  filename: string,
): Promise<void>
```

**savePdf notes:**
- Use jsPDF with page dimensions set to `config.pageSizeMm`.
- Each canvas converted to JPEG (quality 0.92) data-URL and added via `addImage`.
- Subsequent pages use `addPage`.

### 13.8 core/sort.ts

```typescript
export function naturalSort(names: string[]): string[] {
  // Split each name into text/number chunks; sort numerically on number chunks
}
```

### 13.9 UI — index.html Structure

```
<body>
  <header>
    <h1>flipbook-maker</h1>
    <nav><!-- Flipbook | Tarot | Cootie tabs --></nav>
  </header>

  <main id="app">
    <!-- == FLIPBOOK TAB == -->
    <section id="tab-flipbook">
      <div id="upload-area">
        <!-- Drag-drop zone; accepts PNG files or a .zip -->
        <input type="file" multiple accept=".png,image/png,.zip">
        <p>Drop PNG frames or a ZIP here</p>
      </div>

      <form id="controls">
        <!-- Paper / orientation -->
        <fieldset>
          <legend>Page</legend>
          <select name="paper">a4 | a3 | letter | legal</select>
          <label><input type="radio" name="orientation" value="portrait"> Portrait</label>
          <label><input type="radio" name="orientation" value="landscape"> Landscape</label>
          <label>DPI <input type="number" name="dpi" value="150"></label>
          <label>Margin (mm) <input type="number" name="marginMm" value="5"></label>
          <label>Background <input type="text" name="background" value="white"></label>
        </fieldset>

        <!-- Grid -->
        <fieldset>
          <legend>Grid</legend>
          <label>Columns <input type="number" name="cols" value="2"></label>
          <label>Rows <input type="number" name="rows" value="8"></label>
        </fieldset>

        <!-- Frame scaling -->
        <fieldset>
          <legend>Fit</legend>
          <select name="fit">contain | cover | stretch</select>
        </fieldset>

        <!-- Decoration -->
        <fieldset>
          <legend>Decoration</legend>
          <label><input type="checkbox" name="cutMarks"> Cut marks</label>
          <label><input type="checkbox" name="cellOutline"> Cell outlines</label>
          <label><input type="checkbox" name="frameNumbers"> Frame numbers</label>
          <label>Number colour <input type="text" name="frameNumberColor" value="black"></label>
          <label>Number offset (mm) <input type="number" name="frameNumberOffsetMm" value="2"></label>
        </fieldset>

        <!-- Bind strip -->
        <fieldset>
          <legend>Bind strip</legend>
          <label>Width (mm) <input type="number" name="bindStripMm" value="0"></label>
          <label>Colour <input type="text" name="bindStripColor"></label>
        </fieldset>
      </form>

      <!-- Preview -->
      <div id="preview-area">
        <div id="preview-toolbar">
          <button id="btn-prev-sheet">‹</button>
          <span id="sheet-counter">Sheet 1 / 1</span>
          <button id="btn-next-sheet">›</button>
        </div>
        <canvas id="preview-canvas"></canvas>
      </div>

      <!-- Actions -->
      <div id="actions">
        <button id="btn-render">Render</button>
        <button id="btn-download-pdf" disabled>Download PDF</button>
        <button id="btn-download-png" disabled>Download PNGs (ZIP)</button>
        <progress id="render-progress" value="0" max="100" hidden></progress>
      </div>
    </section>

    <!-- == TAROT TAB == -->
    <section id="tab-tarot" hidden>
      <form id="tarot-controls">
        <label>Seed <input type="number" name="seed"></label>
        <label><input type="checkbox" name="random"> Random 8-card grid</label>
        <label><input type="checkbox" name="print"> Ink-friendly</label>
        <label>Paper <select name="paper">…</select></label>
        <label>DPI <input type="number" name="dpi" value="150"></label>
      </form>
      <button id="btn-tarot-render">Generate</button>
      <button id="btn-tarot-download" disabled>Download PDF</button>
      <canvas id="tarot-canvas"></canvas>
    </section>

    <!-- == COOTIE TAB == -->
    <section id="tab-cootie" hidden>
      <form id="cootie-controls">
        <label>Colors (comma-separated) <input type="text" name="colors" value="red,blue,green,yellow"></label>
        <label>Fortunes (comma-separated, 8 values) <textarea name="fortunes"></textarea></label>
        <label><input type="checkbox" name="noInstructions"> Hide instructions</label>
        <label>Background <input type="text" name="background" value="white"></label>
        <label>DPI <input type="number" name="dpi" value="150"></label>
      </form>
      <button id="btn-cootie-render">Generate</button>
      <button id="btn-cootie-download" disabled>Download PDF</button>
      <canvas id="cootie-canvas"></canvas>
    </section>
  </main>
</body>
```

### 13.10 UI Behaviour

**Upload:**
- Accepts `multiple` PNG files or a single ZIP.
- ZIP contents are extracted client-side using JSZip; PNG entries are collected.
- File list is natural-sorted by filename.
- Thumbnail strip shows first 10 frames with count badge.

**Render flow:**
1. User uploads frames, adjusts controls, clicks **Render**.
2. `renderSheets` runs asynchronously; progress bar updates after each page.
3. On completion, preview canvas shows first sheet; next/prev buttons navigate pages.
4. Download buttons are enabled.

**Preview:**
- Preview canvas is scaled to fit the available container width (CSS `max-width: 100%`).
- The underlying canvas is full-resolution (dpi-based pixel dimensions).
- Sheet navigation updates canvas `src` from the rendered pages array.

**Download PDF:**
- Calls `savePdf`, which uses jsPDF to assemble pages and triggers `link.click()` download.

**Download PNGs:**
- Calls `savePages`, which creates a ZIP with JSZip and triggers download.

**Real-time preview update:**
- Any control change triggers a debounced (300 ms) re-render of the *current preview sheet only* (not the full document) to give live feedback without full re-render cost.

### 13.11 Tarot UI Behaviour

- On **Generate**: selects 3 cards (or 8 for `--random`) from the deck, renders canvases, enables download.
- Seed input makes selection reproducible.
- Preview shows the generated layout at reduced size.

### 13.12 Cootie UI Behaviour

- On **Generate**: validates 4 colours and 8 fortunes, renders the cootie-catcher template, enables download.
- Live preview updates as colours/fortunes change (debounced).

---

## 14. Rendering Fidelity Requirements

The web implementation must match the Python reference on these invariants:

1. **Right-wall alignment**: flush-right in every fit mode.
2. **Contain aspect ratio**: no distortion; frame always fits inside usable area.
3. **Cover crop**: cropped from center in both axes.
4. **Stretch**: fills exact usable dimensions.
5. **Frame ordering**: natural alphanumeric sort applied to filenames.
6. **mm_to_px rounding**: `Math.round(mm * dpi / 25.4)` — same as Python `round()`.
7. **Page count**: `ceil(len(frames) / (cols * rows))`.
8. **Margin symmetry**: equal margin on all four sides.
9. **Bind strip**: always left-edge, never right-edge.
10. **Frame numbers**: centred vertically, offset from left edge as specified.

---

## 15. Build & Deployment

### 15.1 Build

```bash
cd web
npm install
npm run build      # outputs to web/dist/
```

### 15.2 Dev Server

```bash
npm run dev        # Vite dev server with HMR
```

### 15.3 Static Hosting

The `web/dist/` directory is a self-contained static site. Deploy to:
- GitHub Pages
- Netlify (drag-and-drop `dist/`)
- Any static file host

No server-side runtime required.

### 15.4 package.json Scripts

```json
{
  "scripts": {
    "dev":   "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }
}
```

---

## 16. Testing (Web)

| Layer | Tool | What |
|---|---|---|
| Unit | Vitest | `mmToPx`, `naturalSort`, `LayoutConfig` derived values |
| Rendering | Vitest + node-canvas | `renderCell` output pixel checks for all fit modes |
| Integration | Playwright | Upload → render → download flow |

**Key test cases (mirror the Python test suite):**
- 16 frames at 2×8 → exactly 1 page.
- 20 frames at 2×8 → exactly 2 pages.
- `contain` mode: frame pixel does not exceed usable cell boundary.
- `cover` mode: every cell pixel is covered.
- Right-wall invariant: rightmost column of pixels in cell is always from the frame (not background).
- Natural sort: `["frame_10.png","frame_2.png"]` → `["frame_2.png","frame_10.png"]`.
- `mmToPx(25.4, 300)` → `300`.
