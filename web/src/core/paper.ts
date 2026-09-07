export const PAPER_SIZES_MM: Record<string, [number, number]> = {
  a4: [210, 297],
  a3: [297, 420],
  letter: [215.9, 279.4],
  legal: [215.9, 355.6],
};

export type PaperKey = keyof typeof PAPER_SIZES_MM;

// Fixed cell sizes for "print at actual size" layouts. filter-tip is a
// standard single/King-size rolling-paper filter tip card (44 x 68mm) —
// verify against your actual tip brand before relying on it for a precise cut.
export const FRAME_SIZE_PRESETS_MM: Record<string, [number, number]> = {
  "filter-tip": [44, 68],
};

export function gridForFrameSize(
  pageSizeMm: [number, number],
  marginMm: number,
  frameSizeMm: [number, number],
): [number, number] {
  const usableW = pageSizeMm[0] - 2 * marginMm;
  const usableH = pageSizeMm[1] - 2 * marginMm;
  const cols = Math.max(1, Math.floor(usableW / frameSizeMm[0]));
  const rows = Math.max(1, Math.floor(usableH / frameSizeMm[1]));
  return [cols, rows];
}

export interface StripPacking {
  cols: number;
  rows: number;
  /** Cell size as [width, height] in mm. */
  cellMm: [number, number];
  cells: number;
  copies: number;
  spare: number;
}

/**
 * Choose a cell size for rolling-paper strips.
 *
 * One dimension is fixed by the physical paper (its width); the other is free,
 * so we pick the length that divides the sheet evenly and yields the most
 * whole copies of the sequence. Ranked by copies, then by least waste, then by
 * closeness to the nominal length.
 *
 * With `lengthHorizontal` the cell is wider than tall, so the square frame sits
 * flush right and the remaining width becomes the blank strip you roll — the
 * same left-edge strip the rest of the layout is built around.
 */
export function solveStripCell(
  pageSizeMm: [number, number],
  marginMm: number,
  stripWidthMm: number,
  nominalLengthMm: number,
  toleranceMm: number,
  framesPerCopy: number,
  lengthHorizontal = true,
): StripPacking | null {
  const usableW = pageSizeMm[0] - 2 * marginMm;
  const usableH = pageSizeMm[1] - 2 * marginMm;
  if (stripWidthMm <= 0 || usableW <= 0 || usableH <= 0) return null;

  const across = Math.floor((lengthHorizontal ? usableH : usableW) / stripWidthMm);
  const span = lengthHorizontal ? usableW : usableH;
  if (across < 1) return null;

  const minLen = Math.max(1, nominalLengthMm - toleranceMm);
  const maxLen = nominalLengthMm + toleranceMm;

  let best: StripPacking | null = null;
  for (let n = 1; n <= 500; n++) {
    const len = span / n;
    if (len < minLen) break;
    if (len > maxLen) continue;

    const cells = across * n;
    const copies = framesPerCopy > 0 ? Math.floor(cells / framesPerCopy) : 0;
    const candidate: StripPacking = {
      cols: lengthHorizontal ? n : across,
      rows: lengthHorizontal ? across : n,
      cellMm: lengthHorizontal ? [len, stripWidthMm] : [stripWidthMm, len],
      cells,
      copies,
      spare: framesPerCopy > 0 ? cells - copies * framesPerCopy : cells,
    };

    if (best === null || rankStrip(candidate, nominalLengthMm) > rankStrip(best, nominalLengthMm)) {
      best = candidate;
    }
  }
  return best;
}

function rankStrip(p: StripPacking, nominalLengthMm: number): number {
  const length = Math.max(p.cellMm[0], p.cellMm[1]);
  return p.copies * 1e6 - p.spare * 1e3 - Math.abs(length - nominalLengthMm);
}
