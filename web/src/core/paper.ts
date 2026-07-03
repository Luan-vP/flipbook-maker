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
