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
```

Frames are taken in alphanumeric order (`frame_001.png`, `frame_002.png`, …).

## Develop

```bash
pip install -e .[dev]
pytest
ruff check .
```

## Layout

A4 portrait (210 × 297 mm) is divided into `cols × rows` cells. Within each
cell the frame is scaled to fit (preserving aspect ratio) and pasted against
the right wall, vertically centred. Cut along the cell boundaries and bind
the left edges.
