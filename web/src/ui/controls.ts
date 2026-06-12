import { LayoutConfig, DEFAULT_CONFIG } from "../core/layout";
import { PAPER_SIZES_MM } from "../core/paper";

export function readLayoutConfig(form: HTMLFormElement): LayoutConfig {
  const data = new FormData(form);

  function str(name: string, fallback: string): string {
    return (data.get(name) as string | null)?.trim() || fallback;
  }
  function num(name: string, fallback: number): number {
    const v = parseFloat(str(name, String(fallback)));
    return isNaN(v) ? fallback : v;
  }
  function bool(name: string): boolean {
    return data.get(name) === "on" || data.get(name) === "true";
  }

  const paper = str("paper", "a4");
  const orientation = str("orientation", "portrait");
  let pageSizeMm = PAPER_SIZES_MM[paper] ?? PAPER_SIZES_MM["a4"];
  if (orientation === "landscape") {
    pageSizeMm = [pageSizeMm[1], pageSizeMm[0]];
  }

  const bindColor = str("bindStripColor", "");

  return {
    cols: Math.max(1, Math.round(num("cols", DEFAULT_CONFIG.cols))),
    rows: Math.max(1, Math.round(num("rows", DEFAULT_CONFIG.rows))),
    dpi: Math.max(72, Math.round(num("dpi", DEFAULT_CONFIG.dpi))),
    marginMm: Math.max(0, num("marginMm", DEFAULT_CONFIG.marginMm)),
    background: str("background", DEFAULT_CONFIG.background),
    pageSizeMm,
    cutMarks: bool("cutMarks"),
    cellOutline: bool("cellOutline"),
    fit: str("fit", DEFAULT_CONFIG.fit) as LayoutConfig["fit"],
    frameNumbers: bool("frameNumbers"),
    frameNumberColor: str("frameNumberColor", DEFAULT_CONFIG.frameNumberColor),
    frameNumberOffsetMm: Math.max(0, num("frameNumberOffsetMm", DEFAULT_CONFIG.frameNumberOffsetMm)),
    bindStripMm: Math.max(0, num("bindStripMm", DEFAULT_CONFIG.bindStripMm)),
    bindStripColor: bindColor || null,
  };
}
