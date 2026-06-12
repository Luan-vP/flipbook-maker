import { TarotCard } from "./deck";
import { mmToPx } from "../core/units";
import { PAPER_SIZES_MM } from "../core/paper";
import jsPDF from "jspdf";

export interface TarotConfig {
  dpi: number;
  paper: string;
  printMode: boolean;
  background: string;
  foreground: string;
  cellOutline: boolean;
  pageNumbers: boolean;
}

export const DEFAULT_TAROT_CONFIG: TarotConfig = {
  dpi: 150,
  paper: "a4",
  printMode: false,
  background: "#1a1a2e",
  foreground: "#e0d0b0",
  cellOutline: true,
  pageNumbers: true,
};

function makeCanvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && current) {
      lines.push(current);
      current = word;
    } else {
      current = test;
    }
  }
  if (current) lines.push(current);
  return lines;
}

function renderCardPanel(
  canvas: HTMLCanvasElement,
  card: TarotCard,
  x: number,
  y: number,
  w: number,
  h: number,
  config: TarotConfig,
): void {
  const ctx = canvas.getContext("2d")!;

  ctx.fillStyle = config.background;
  ctx.fillRect(x, y, w, h);

  if (config.cellOutline) {
    ctx.strokeStyle = config.foreground;
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 2, y + 2, w - 4, h - 4);
  }

  const pad = Math.round(w * 0.08);
  const titleSize = Math.max(12, Math.round(h * 0.09));
  const descSize = Math.max(9, Math.round(h * 0.055));

  ctx.fillStyle = config.foreground;
  ctx.font = `bold ${titleSize}px serif`;
  ctx.textAlign = "center";

  const nameLines = wrapText(ctx, card.name, w - 2 * pad);
  const lineH = titleSize * 1.3;
  let ty = y + pad + titleSize;
  for (const line of nameLines) {
    ctx.fillText(line, x + w / 2, ty);
    ty += lineH;
  }

  ctx.font = `${descSize}px sans-serif`;
  const descLines = wrapText(ctx, card.description, w - 2 * pad);
  ty += pad * 0.5;
  const descLineH = descSize * 1.4;
  for (const line of descLines) {
    if (ty + descLineH > y + h - pad) break;
    ctx.fillText(line, x + w / 2, ty);
    ty += descLineH;
  }

  ctx.textAlign = "left";
}

export function renderTarotGrid(
  cards: TarotCard[],
  config: TarotConfig,
): HTMLCanvasElement {
  const pageMm = [...PAPER_SIZES_MM[config.paper]] as [number, number];
  const [pw, ph] = [mmToPx(pageMm[1], config.dpi), mmToPx(pageMm[0], config.dpi)]; // landscape
  const cols = 4;
  const rows = 2;
  const marginPx = mmToPx(8, config.dpi);
  const cellW = Math.floor((pw - 2 * marginPx) / cols);
  const cellH = Math.floor((ph - 2 * marginPx) / rows);

  const canvas = makeCanvas(pw, ph);
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = config.background;
  ctx.fillRect(0, 0, pw, ph);

  for (let i = 0; i < Math.min(cards.length, 8); i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = marginPx + col * cellW;
    const y = marginPx + row * cellH;
    renderCardPanel(canvas, cards[i], x, y, cellW, cellH, config);
  }

  return canvas;
}

export function renderTarotZine(
  past: TarotCard,
  present: TarotCard,
  future: TarotCard,
  config: TarotConfig,
): HTMLCanvasElement[] {
  const pageMm = PAPER_SIZES_MM[config.paper];
  const pw = mmToPx(pageMm[0], config.dpi);
  const ph = mmToPx(pageMm[1], config.dpi);
  const pages: HTMLCanvasElement[] = [];

  function blankPage(): HTMLCanvasElement {
    const c = makeCanvas(pw, ph);
    const ctx = c.getContext("2d")!;
    ctx.fillStyle = config.background;
    ctx.fillRect(0, 0, pw, ph);
    return c;
  }

  function addText(
    canvas: HTMLCanvasElement,
    text: string,
    size: number,
    cx: number,
    cy: number,
    bold = false,
  ) {
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = config.foreground;
    ctx.font = `${bold ? "bold " : ""}${size}px serif`;
    ctx.textAlign = "center";
    ctx.fillText(text, cx, cy);
    ctx.textAlign = "left";
  }

  // Page 1: Cover
  const cover = blankPage();
  addText(cover, "Tarot", Math.round(ph * 0.08), pw / 2, ph * 0.4, true);
  addText(cover, "A three-card reading", Math.round(ph * 0.04), pw / 2, ph * 0.52);
  pages.push(cover);

  // Pages 2-7: card pairs
  const cardPairs: [string, TarotCard][] = [
    ["Past", past],
    ["Present", present],
    ["Future", future],
  ];
  for (const [label, card] of cardPairs) {
    // left page: position label
    const leftPage = blankPage();
    addText(leftPage, label, Math.round(ph * 0.06), pw / 2, ph * 0.45, true);
    pages.push(leftPage);

    // right page: card details
    const rightPage = blankPage();
    renderCardPanel(rightPage, card, mmToPx(10, config.dpi), mmToPx(10, config.dpi),
      pw - mmToPx(20, config.dpi), ph - mmToPx(20, config.dpi), config);
    pages.push(rightPage);
  }

  // Page 8: Back
  const back = blankPage();
  addText(back, "fold · cut centre · read in order", Math.round(ph * 0.035), pw / 2, ph * 0.5);
  pages.push(back);

  if (config.pageNumbers) {
    pages.forEach((page, i) => {
      const ctx = page.getContext("2d")!;
      const numSize = Math.max(8, mmToPx(3.5, config.dpi));
      ctx.fillStyle = config.foreground;
      ctx.font = `${numSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(String(i + 1), pw / 2, ph - mmToPx(5, config.dpi));
      ctx.textAlign = "left";
    });
  }

  return pages;
}

export async function downloadTarotPdf(
  canvases: HTMLCanvasElement[],
  filename: string,
  pageSizeMm: [number, number],
): Promise<void> {
  const [w, h] = pageSizeMm;
  const orientation = w > h ? "landscape" : "portrait";
  const pdf = new jsPDF({ orientation, unit: "mm", format: [w, h] });
  for (let i = 0; i < canvases.length; i++) {
    if (i > 0) pdf.addPage([w, h], orientation);
    pdf.addImage(canvases[i].toDataURL("image/jpeg", 0.92), "JPEG", 0, 0, w, h);
  }
  pdf.save(filename);
}
