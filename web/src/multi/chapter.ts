import {
  LayoutConfig,
  computeDimensions,
  renderCell,
  fillBackground,
  drawCutMarks,
  drawCellOutlines,
} from "../core/layout";

export interface ChapterFrames {
  name: string;
  frames: ImageBitmap[];
}

/**
 * Renders one page per frame-slot group, with each chapter stacked as a row.
 *
 * Layout per page (cols=2, 3 chapters):
 *   | frame i Ch1 | frame i+1 Ch1 |
 *   | frame i Ch2 | frame i+1 Ch2 |
 *   | frame i Ch3 | frame i+1 Ch3 |
 *
 * config.rows is ignored — rows are determined by the number of chapters.
 * config.cols controls how many frame-slots appear side-by-side per page.
 */
export async function renderMultiChapterSheets(
  chapters: ChapterFrames[],
  config: LayoutConfig,
  onProgress?: (current: number, total: number) => void,
): Promise<HTMLCanvasElement[]> {
  if (chapters.length === 0) return [];

  const frameCount = Math.min(...chapters.map((c) => c.frames.length));
  const numChapters = chapters.length;
  const multiConfig: LayoutConfig = { ...config, rows: numChapters };
  const dims = computeDimensions(multiConfig);
  const pageCount = Math.max(1, Math.ceil(frameCount / config.cols));
  const pages: HTMLCanvasElement[] = [];

  const totalOps = pageCount * config.cols * numChapters;
  let done = 0;

  for (let p = 0; p < pageCount; p++) {
    const canvas = document.createElement("canvas");
    canvas.width = dims.pagePx[0];
    canvas.height = dims.pagePx[1];
    const ctx = canvas.getContext("2d")!;

    await fillBackground(ctx, config.background, dims.pagePx[0], dims.pagePx[1]);

    for (let j = 0; j < config.cols; j++) {
      const frameIdx = p * config.cols + j;
      if (frameIdx >= frameCount) break;

      for (let c = 0; c < numChapters; c++) {
        const x = dims.marginPx + j * dims.cellPx[0];
        const y = dims.marginPx + c * dims.cellPx[1];
        const cell = await renderCell(
          chapters[c].frames[frameIdx],
          frameIdx,
          multiConfig,
          dims,
        );
        ctx.drawImage(cell, x, y);
        done++;
        onProgress?.(done, totalOps);
      }
    }

    if (config.cutMarks) drawCutMarks(ctx, multiConfig, dims);
    if (config.cellOutline) drawCellOutlines(ctx, multiConfig, dims);

    pages.push(canvas);
  }

  return pages;
}
