import { mmToPx } from "../core/units";
import { PAPER_SIZES_MM } from "../core/paper";
import jsPDF from "jspdf";

export interface CootieConfig {
  dpi: number;
  paper: string;
  colors: string[];
  fortunes: string[];
  showInstructions: boolean;
  background: string;
}

export const DEFAULT_COOTIE_CONFIG: CootieConfig = {
  dpi: 150,
  paper: "a4",
  colors: ["red", "blue", "green", "yellow"],
  fortunes: [
    "Good fortune awaits",
    "Adventure is near",
    "A surprise today",
    "Be bold",
    "Rest and reflect",
    "Share your joy",
    "New doors open",
    "Trust yourself",
  ],
  showInstructions: true,
  background: "white",
};

function drawDashedLine(
  ctx: CanvasRenderingContext2D,
  x1: number, y1: number,
  x2: number, y2: number,
  dashLen: number,
) {
  ctx.save();
  ctx.setLineDash([dashLen, dashLen]);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.restore();
}

export function renderCooticeCatcher(config: CootieConfig): HTMLCanvasElement {
  const pageMm = PAPER_SIZES_MM[config.paper];
  const pw = mmToPx(pageMm[0], config.dpi);
  const ph = mmToPx(pageMm[1], config.dpi);

  const canvas = document.createElement("canvas");
  canvas.width = pw;
  canvas.height = ph;
  const ctx = canvas.getContext("2d")!;

  ctx.fillStyle = config.background;
  ctx.fillRect(0, 0, pw, ph);

  // Square size and center
  const sqSize = Math.min(pw, ph) * 0.72;
  const cx = pw / 2;
  const cy = config.showInstructions ? ph * 0.42 : ph / 2;
  const half = sqSize / 2;

  // Corner points of the square
  const TL = [cx - half, cy - half];
  const TR = [cx + half, cy - half];
  const BL = [cx - half, cy + half];
  const BR = [cx + half, cy + half];
  const MID_T = [cx, cy - half];
  const MID_B = [cx, cy + half];
  const MID_L = [cx - half, cy];
  const MID_R = [cx + half, cy];

  // Draw 4 coloured outer triangles (corners to center)
  const outerTriangles = [
    { pts: [TL, MID_T, [cx, cy], MID_L], color: config.colors[0] ?? "red" },    // NW
    { pts: [MID_T, TR, MID_R, [cx, cy]], color: config.colors[1] ?? "blue" },   // NE
    { pts: [[cx, cy], MID_R, BR, MID_B], color: config.colors[2] ?? "green" },  // SE
    { pts: [MID_L, [cx, cy], MID_B, BL], color: config.colors[3] ?? "yellow" }, // SW
  ];

  for (const tri of outerTriangles) {
    ctx.beginPath();
    ctx.moveTo(tri.pts[0][0], tri.pts[0][1]);
    for (let i = 1; i < tri.pts.length; i++) ctx.lineTo(tri.pts[i][0], tri.pts[i][1]);
    ctx.closePath();
    ctx.fillStyle = tri.color;
    ctx.fill();
  }

  // Draw 8 fortune triangles (inner corners)
  const innerQuarter = half / 2;
  const fortuneTriangles = [
    // NW quadrant, 2 triangles
    { pts: [TL, MID_T, [cx, cy]], vertices: [[cx - half, cy - half], [cx, cy - half], [cx, cy]], fortune: config.fortunes[0] ?? "", angle: -Math.PI / 4 },
    { pts: [TL, [cx, cy], MID_L], vertices: [[cx - half, cy - half], [cx, cy], [cx - half, cy]], fortune: config.fortunes[1] ?? "", angle: Math.PI * 3 / 4 },
    // NE quadrant
    { pts: [MID_T, TR, [cx, cy]], vertices: [[cx, cy - half], [cx + half, cy - half], [cx, cy]], fortune: config.fortunes[2] ?? "", angle: -Math.PI * 3 / 4 },
    { pts: [TR, MID_R, [cx, cy]], vertices: [[cx + half, cy - half], [cx + half, cy], [cx, cy]], fortune: config.fortunes[3] ?? "", angle: Math.PI / 4 },
    // SE quadrant
    { pts: [[cx, cy], MID_R, BR], vertices: [[cx, cy], [cx + half, cy], [cx + half, cy + half]], fortune: config.fortunes[4] ?? "", angle: Math.PI / 4 },
    { pts: [[cx, cy], BR, MID_B], vertices: [[cx, cy], [cx + half, cy + half], [cx, cy + half]], fortune: config.fortunes[5] ?? "", angle: -Math.PI * 3 / 4 },
    // SW quadrant
    { pts: [MID_L, [cx, cy], MID_B], vertices: [[cx - half, cy], [cx, cy], [cx, cy + half]], fortune: config.fortunes[6] ?? "", angle: Math.PI * 3 / 4 },
    { pts: [MID_L, MID_B, BL], vertices: [[cx - half, cy], [cx, cy + half], [cx - half, cy + half]], fortune: config.fortunes[7] ?? "", angle: -Math.PI / 4 },
  ];

  for (let i = 0; i < fortuneTriangles.length; i++) {
    const ft = fortuneTriangles[i];
    // Draw light fill
    ctx.beginPath();
    ctx.moveTo(ft.vertices[0][0], ft.vertices[0][1]);
    for (let j = 1; j < ft.vertices.length; j++) ctx.lineTo(ft.vertices[j][0], ft.vertices[j][1]);
    ctx.closePath();
    ctx.fillStyle = "rgba(255,255,255,0.6)";
    ctx.fill();

    // Number label
    const numX = (ft.vertices[0][0] + ft.vertices[1][0] + ft.vertices[2][0]) / 3;
    const numY = (ft.vertices[0][1] + ft.vertices[1][1] + ft.vertices[2][1]) / 3;
    const fontSize = Math.max(10, Math.round(sqSize * 0.05));
    ctx.save();
    ctx.translate(numX, numY);
    ctx.rotate(ft.angle);
    ctx.fillStyle = "#333";
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(i + 1), 0, -fontSize * 0.8);
    const descSize = Math.max(7, Math.round(fontSize * 0.7));
    ctx.font = `${descSize}px sans-serif`;
    ctx.fillText(ft.fortune, 0, fontSize * 0.5);
    ctx.restore();
  }

  // Colour labels
  const labelPositions = [
    { x: cx - innerQuarter, y: cy - innerQuarter, angle: Math.PI / 4, color: config.colors[0] ?? "red" },
    { x: cx + innerQuarter, y: cy - innerQuarter, angle: -Math.PI / 4, color: config.colors[1] ?? "blue" },
    { x: cx + innerQuarter, y: cy + innerQuarter, angle: Math.PI / 4, color: config.colors[2] ?? "green" },
    { x: cx - innerQuarter, y: cy + innerQuarter, angle: -Math.PI / 4, color: config.colors[3] ?? "yellow" },
  ];
  const labelFontSize = Math.max(8, Math.round(sqSize * 0.045));
  for (const lp of labelPositions) {
    ctx.save();
    ctx.translate(lp.x, lp.y);
    ctx.rotate(lp.angle);
    ctx.fillStyle = "white";
    ctx.font = `bold ${labelFontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(lp.color.toUpperCase(), 0, 0);
    ctx.restore();
  }

  // Dashed fold lines
  const dashLen = mmToPx(3, config.dpi);
  ctx.strokeStyle = "#555";
  ctx.lineWidth = 1;

  // Diagonals
  drawDashedLine(ctx, TL[0], TL[1], BR[0], BR[1], dashLen);
  drawDashedLine(ctx, TR[0], TR[1], BL[0], BL[1], dashLen);
  // Midlines
  drawDashedLine(ctx, MID_T[0], MID_T[1], MID_B[0], MID_B[1], dashLen);
  drawDashedLine(ctx, MID_L[0], MID_L[1], MID_R[0], MID_R[1], dashLen);

  // Outer square border
  ctx.strokeStyle = "#333";
  ctx.lineWidth = 2;
  ctx.setLineDash([]);
  ctx.strokeRect(cx - half, cy - half, sqSize, sqSize);

  // Folding instructions
  if (config.showInstructions) {
    const instrY = cy + half + mmToPx(8, config.dpi);
    const stepSize = Math.max(9, Math.round(pw * 0.024));
    const steps = [
      "1. Cut out the square along the outer border.",
      "2. Fold all four corners to the center.",
      "3. Flip over and fold all four corners to the center again.",
      "4. Fold in half (hot-dog style), then open and fold the other way.",
      "5. Slip thumbs and index fingers under the flaps to use.",
    ];
    ctx.fillStyle = "#333";
    ctx.font = `${stepSize}px sans-serif`;
    ctx.textAlign = "left";
    for (let i = 0; i < steps.length; i++) {
      ctx.fillText(steps[i], cx - half, instrY + i * stepSize * 1.6);
    }
  }

  return canvas;
}

export async function downloadCooticePdf(
  canvas: HTMLCanvasElement,
  filename: string,
  pageSizeMm: [number, number],
): Promise<void> {
  const [w, h] = pageSizeMm;
  const pdf = new jsPDF({ unit: "mm", format: [w, h] });
  pdf.addImage(canvas.toDataURL("image/jpeg", 0.92), "JPEG", 0, 0, w, h);
  pdf.save(filename);
}
