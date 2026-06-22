import { mmToPx } from "./units";

export type FitMode = "contain" | "cover" | "stretch";

export interface LayoutConfig {
  cols: number;
  rows: number;
  dpi: number;
  marginMm: number;
  background: string;
  pageSizeMm: [number, number];
  cutMarks: boolean;
  cellOutline: boolean;
  fit: FitMode;
  frameNumbers: boolean;
  frameNumberColor: string;
  frameNumberOffsetMm: number;
  bindStripMm: number;
  bindStripColor: string | null;
}

export const DEFAULT_CONFIG: LayoutConfig = {
  cols: 2,
  rows: 8,
  dpi: 150,
  marginMm: 5,
  background: "white",
  pageSizeMm: [210, 297],
  cutMarks: false,
  cellOutline: false,
  fit: "contain",
  frameNumbers: false,
  frameNumberColor: "black",
  frameNumberOffsetMm: 2,
  bindStripMm: 0,
  bindStripColor: null,
};

export interface LayoutDimensions {
  pagePx: [number, number];
  marginPx: number;
  cellPx: [number, number];
  bindStripPx: number;
  usableW: number;
}

export function computeDimensions(config: LayoutConfig): LayoutDimensions {
  const pagePx: [number, number] = [
    mmToPx(config.pageSizeMm[0], config.dpi),
    mmToPx(config.pageSizeMm[1], config.dpi),
  ];
  const marginPx = mmToPx(config.marginMm, config.dpi);
  const cellPx: [number, number] = [
    Math.floor((pagePx[0] - 2 * marginPx) / config.cols),
    Math.floor((pagePx[1] - 2 * marginPx) / config.rows),
  ];
  const bindStripPx = mmToPx(config.bindStripMm, config.dpi);
  const usableW = cellPx[0] - bindStripPx;
  return { pagePx, marginPx, cellPx, bindStripPx, usableW };
}

function makeCanvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

export async function fillBackground(
  ctx: CanvasRenderingContext2D,
  bg: string,
  w: number,
  h: number,
): Promise<void> {
  if (bg.startsWith("data:") || bg.startsWith("blob:") || bg.startsWith("http")) {
    await new Promise<void>((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, w, h);
        resolve();
      };
      img.onerror = reject;
      img.src = bg;
    });
  } else {
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
  }
}

export async function renderCell(
  frame: ImageBitmap,
  frameIndex: number,
  config: LayoutConfig,
  dims: LayoutDimensions,
): Promise<HTMLCanvasElement> {
  const [cw, ch] = dims.cellPx;
  const canvas = makeCanvas(cw, ch);
  const ctx = canvas.getContext("2d")!;

  await fillBackground(ctx, config.background, cw, ch);

  if (dims.bindStripPx > 0 && config.bindStripColor) {
    ctx.fillStyle = config.bindStripColor;
    ctx.fillRect(0, 0, dims.bindStripPx, ch);
  }

  const fw = frame.width;
  const fh = frame.height;
  const uw = dims.usableW;

  if (config.fit === "contain") {
    const scale = Math.min(uw / fw, ch / fh);
    const pw = Math.round(fw * scale);
    const ph = Math.round(fh * scale);
    const px = cw - pw;
    const py = Math.round((ch - ph) / 2);
    ctx.drawImage(frame, px, py, pw, ph);
  } else if (config.fit === "cover") {
    const scale = Math.max(uw / fw, ch / fh);
    const cropW = Math.round(uw / scale);
    const cropH = Math.round(ch / scale);
    const cropX = Math.round((fw - cropW) / 2);
    const cropY = Math.round((fh - cropH) / 2);
    ctx.drawImage(frame, cropX, cropY, cropW, cropH, dims.bindStripPx, 0, uw, ch);
  } else {
    // stretch
    ctx.drawImage(frame, dims.bindStripPx, 0, uw, ch);
  }

  if (config.frameNumbers) {
    const offsetPx = mmToPx(config.frameNumberOffsetMm, config.dpi);
    const effectiveOffset =
      dims.bindStripPx > 0
        ? Math.max(offsetPx, Math.floor(dims.bindStripPx / 2))
        : offsetPx;
    const fontSize = Math.max(8, Math.round(ch * 0.06));
    ctx.font = `${fontSize}px sans-serif`;
    ctx.fillStyle = config.frameNumberColor;
    const text = String(frameIndex + 1);
    const metrics = ctx.measureText(text);
    const textH =
      metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent;
    ctx.fillText(text, effectiveOffset, (ch - textH) / 2 + metrics.actualBoundingBoxAscent);
  }

  return canvas;
}

export function drawCutMarks(
  ctx: CanvasRenderingContext2D,
  config: LayoutConfig,
  dims: LayoutDimensions,
): void {
  const tickPx = mmToPx(3, config.dpi);
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;

  for (let row = 0; row <= config.rows; row++) {
    for (let col = 0; col <= config.cols; col++) {
      const x = dims.marginPx + col * dims.cellPx[0];
      const y = dims.marginPx + row * dims.cellPx[1];

      ctx.beginPath();
      ctx.moveTo(x - tickPx, y);
      ctx.lineTo(x + tickPx, y);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(x, y - tickPx);
      ctx.lineTo(x, y + tickPx);
      ctx.stroke();
    }
  }
}

export function drawCellOutlines(
  ctx: CanvasRenderingContext2D,
  config: LayoutConfig,
  dims: LayoutDimensions,
): void {
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  for (let row = 0; row < config.rows; row++) {
    for (let col = 0; col < config.cols; col++) {
      const x = dims.marginPx + col * dims.cellPx[0];
      const y = dims.marginPx + row * dims.cellPx[1];
      ctx.strokeRect(x, y, dims.cellPx[0], dims.cellPx[1]);
    }
  }
}

export async function renderSheets(
  frames: ImageBitmap[],
  config: LayoutConfig,
  onProgress?: (current: number, total: number) => void,
): Promise<HTMLCanvasElement[]> {
  const dims = computeDimensions(config);
  const cellsPerPage = config.cols * config.rows;
  const pageCount = Math.max(1, Math.ceil(frames.length / cellsPerPage));
  const pages: HTMLCanvasElement[] = [];

  for (let p = 0; p < pageCount; p++) {
    const canvas = makeCanvas(dims.pagePx[0], dims.pagePx[1]);
    const ctx = canvas.getContext("2d")!;

    await fillBackground(ctx, config.background, dims.pagePx[0], dims.pagePx[1]);

    const startIdx = p * cellsPerPage;
    const endIdx = Math.min(startIdx + cellsPerPage, frames.length);

    for (let i = startIdx; i < endIdx; i++) {
      const cellIndex = i - startIdx;
      const col = cellIndex % config.cols;
      const row = Math.floor(cellIndex / config.cols);
      const x = dims.marginPx + col * dims.cellPx[0];
      const y = dims.marginPx + row * dims.cellPx[1];

      const cell = await renderCell(frames[i], i, config, dims);
      ctx.drawImage(cell, x, y);

      if (onProgress) onProgress(i + 1, frames.length);
    }

    if (config.cutMarks) drawCutMarks(ctx, config, dims);
    if (config.cellOutline) drawCellOutlines(ctx, config, dims);

    pages.push(canvas);
  }

  return pages;
}
