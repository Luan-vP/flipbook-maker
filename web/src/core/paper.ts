export const PAPER_SIZES_MM: Record<string, [number, number]> = {
  a4: [210, 297],
  a3: [297, 420],
  letter: [215.9, 279.4],
  legal: [215.9, 355.6],
};

export type PaperKey = keyof typeof PAPER_SIZES_MM;
