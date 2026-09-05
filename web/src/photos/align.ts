/**
 * Square-frame alignment for photo sequences.
 *
 * A flipbook animates only if successive frames register against each other.
 * Photos shot by hand never do, so each frame carries a `FrameTransform` that
 * pans / zooms / rotates it inside a fixed square window. This module is pure:
 * it knows about bitmaps and squares, never about the DOM controls that set
 * the numbers or the sheet layout that consumes the result.
 */

export interface FrameTransform {
  /** Pan, as a fraction of the square's side. 0 = centred. */
  tx: number;
  ty: number;
  /** Zoom on top of the fit-inside baseline. 1 = whole frame visible. */
  scale: number;
  /** Clockwise rotation, radians. */
  rotation: number;
}

export const IDENTITY_TRANSFORM: Readonly<FrameTransform> = Object.freeze({
  tx: 0,
  ty: 0,
  scale: 1,
  rotation: 0,
});

export interface PhotoFrame {
  name: string;
  bitmap: ImageBitmap;
  transform: FrameTransform;
}

/**
 * Scale at which `bitmap` fits entirely inside a square of `side` px.
 *
 * Contain, not cover: the source photos are scans of varying aspect ratio, and
 * cropping a tall one before the artist has positioned it hides the very thing
 * they need to see to register it.
 */
export function fitScale(bitmap: ImageBitmap, side: number): number {
  return Math.min(side / bitmap.width, side / bitmap.height);
}

/**
 * Draw one transformed frame into the square [0, side] × [0, side] of `ctx`.
 * The caller positions the square by translating `ctx` first.
 */
export function drawSquare(
  ctx: CanvasRenderingContext2D,
  bitmap: ImageBitmap,
  transform: FrameTransform,
  side: number,
  background?: string,
): void {
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, side, side);
  ctx.clip();

  if (background) {
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, side, side);
  }

  const s = fitScale(bitmap, side) * transform.scale;
  ctx.translate(side / 2 + transform.tx * side, side / 2 + transform.ty * side);
  ctx.rotate(transform.rotation);
  ctx.scale(s, s);
  ctx.drawImage(bitmap, -bitmap.width / 2, -bitmap.height / 2);

  ctx.restore();
}

/** Render a single frame to its own square canvas. */
export function renderSquare(
  bitmap: ImageBitmap,
  transform: FrameTransform,
  side: number,
  background = "white",
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = side;
  canvas.height = side;
  const ctx = canvas.getContext("2d")!;
  ctx.imageSmoothingQuality = "high";
  drawSquare(ctx, bitmap, transform, side, background);
  return canvas;
}

/**
 * Bake the aligned sequence into square bitmaps ready for `renderSheets`.
 * Once baked the transforms are gone — downstream layout sees plain frames.
 */
export async function bakeSquares(
  frames: PhotoFrame[],
  side: number,
  background = "white",
  onProgress?: (current: number, total: number) => void,
): Promise<ImageBitmap[]> {
  const out: ImageBitmap[] = [];
  for (let i = 0; i < frames.length; i++) {
    const canvas = renderSquare(frames[i].bitmap, frames[i].transform, side, background);
    out.push(await createImageBitmap(canvas));
    onProgress?.(i + 1, frames.length);
  }
  return out;
}
