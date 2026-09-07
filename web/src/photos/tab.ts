/**
 * Photos tab: turn a folder of stills into a registered, playable flipbook.
 *
 * Three stages share one ordered `PhotoFrame[]`:
 *   1. load + order  — natural sort, optional reverse, drag to reorder
 *   2. align         — pan/zoom/rotate each frame inside a square window,
 *                      with onion-skin overlays to register against a neighbour
 *   3. play          — flip the aligned squares at a chosen fps
 * Print reuses the existing sheet layout: the squares are baked and handed to
 * `renderSheets` unchanged, so the right-wall bind edge still holds.
 *
 * Aligning a sequence by hand is slow work, so two things protect it: a set can
 * be preloaded from `public/preload/<name>/manifest.json` via `?preload=<name>`
 * (skipping the file picker on every reload), and transforms are autosaved to
 * localStorage keyed by filename, so a refresh does not throw the work away.
 */

import { loadFiles } from "../ui/upload";
import { readLayoutConfig } from "../ui/controls";
import { renderSheets, computeDimensions, LayoutConfig } from "../core/layout";
import { solveStripCell, StripPacking } from "../core/paper";
import { savePdf, savePages } from "../core/io";
import {
  PhotoFrame,
  FrameTransform,
  IDENTITY_TRANSFORM,
  drawSquare,
  bakeSquares,
} from "./align";

const EDITOR_SIDE = 460;
const PLAY_SIDE = 260;
const THUMB_SIDE = 54;
const MIN_SCALE = 0.15;
const MAX_SCALE = 8;
const STORAGE_KEY = "flipbook-maker.photos.transforms";

type OnionMode = "off" | "prev" | "next" | "both" | "difference";

export function initPhotosTab(): void {
  // ── DOM refs ─────────────────────────────────────────────────────────────

  const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

  const input = $<HTMLInputElement>("photos-input");
  const btnAdd = $<HTMLButtonElement>("btn-photos-add");
  const btnClear = $<HTMLButtonElement>("btn-photos-clear");
  const btnForget = $<HTMLButtonElement>("btn-photos-forget");
  const reverseToggle = $<HTMLInputElement>("photos-reverse");
  const countLabel = $<HTMLSpanElement>("photos-count");
  const strip = $<HTMLDivElement>("photos-strip");
  const status = $<HTMLSpanElement>("photos-status");

  const btnAdvanced = $<HTMLButtonElement>("btn-photos-advanced-toggle");
  const advancedPanel = $<HTMLDivElement>("photos-advanced-panel");
  const controlsForm = $<HTMLFormElement>("photos-controls");

  const stripMode = $<HTMLInputElement>("photos-strip-mode");
  const stripWidth = $<HTMLInputElement>("photos-strip-width");
  const stripLength = $<HTMLInputElement>("photos-strip-length");
  const stripTolerance = $<HTMLInputElement>("photos-strip-tolerance");
  const stripOrientation = $<HTMLSelectElement>("photos-strip-orientation");
  const fillSheet = $<HTMLInputElement>("photos-fill-sheet");
  const copiesInput = $<HTMLInputElement>("photos-copies");
  const stripReadout = $<HTMLParagraphElement>("photos-strip-readout");

  const btnBuild = $<HTMLButtonElement>("btn-photos-build");
  const progress = $<HTMLProgressElement>("photos-progress");
  const btnPdf = $<HTMLButtonElement>("btn-photos-pdf");
  const btnPng = $<HTMLButtonElement>("btn-photos-png");

  const alignCanvas = $<HTMLCanvasElement>("align-canvas");
  const alignLabel = $<HTMLSpanElement>("align-label");
  const alignEmpty = $<HTMLDivElement>("align-empty");
  const zoomInput = $<HTMLInputElement>("align-zoom");
  const zoomValue = $<HTMLSpanElement>("align-zoom-value");
  const rotateInput = $<HTMLInputElement>("align-rotate");
  const rotateValue = $<HTMLSpanElement>("align-rotate-value");
  const onionSelect = $<HTMLSelectElement>("align-onion");
  const onionOpacity = $<HTMLInputElement>("align-onion-opacity");
  const guidesToggle = $<HTMLInputElement>("align-guides");
  const btnAlignPrev = $<HTMLButtonElement>("btn-align-prev");
  const btnAlignNext = $<HTMLButtonElement>("btn-align-next");
  const btnAlignReset = $<HTMLButtonElement>("btn-align-reset");
  const btnAlignCopyNext = $<HTMLButtonElement>("btn-align-copy-next");
  const btnAlignApplyAll = $<HTMLButtonElement>("btn-align-apply-all");

  const playCanvas = $<HTMLCanvasElement>("play-canvas");
  const btnPlay = $<HTMLButtonElement>("btn-play");
  const fpsInput = $<HTMLInputElement>("play-fps");
  const modeSelect = $<HTMLSelectElement>("play-mode");
  const scrub = $<HTMLInputElement>("play-scrub");
  const playCounter = $<HTMLSpanElement>("play-counter");

  const sheetCanvas = $<HTMLCanvasElement>("photos-sheet-canvas");
  const sheetCounter = $<HTMLSpanElement>("photos-sheet-counter");
  const btnSheetPrev = $<HTMLButtonElement>("btn-photos-prev-sheet");
  const btnSheetNext = $<HTMLButtonElement>("btn-photos-next-sheet");

  // ── State ────────────────────────────────────────────────────────────────

  let frames: PhotoFrame[] = [];
  let selected = 0;
  let sheets: HTMLCanvasElement[] = [];
  let sheetIndex = 0;

  let playing = false;
  let playIndex = 0;
  let playDirection = 1;
  let lastFrameTime = 0;

  const dpr = Math.min(window.devicePixelRatio || 1, 2);

  /** Namespaces saved transforms, so two sets can share a filename safely. */
  let setPrefix = "";
  /** Transform a "Forget saved" reset returns to (a manifest may rotate). */
  let baseline: FrameTransform = { ...IDENTITY_TRANSFORM };

  // ── Transform persistence ────────────────────────────────────────────────
  // Keyed by filename rather than index, so reordering or reloading a subset
  // still restores the right transform to the right photo.

  function loadSavedTransforms(): Record<string, FrameTransform> {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function saveTransforms(): void {
    try {
      const saved = loadSavedTransforms();
      for (const f of frames) saved[setPrefix + f.name] = f.transform;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
      setStatus(`Alignment saved — ${frames.length} frames`);
    } catch {
      setStatus("Could not save alignment (storage unavailable)");
    }
  }

  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  function scheduleSave(): void {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveTransforms, 500);
  }

  function setStatus(text: string): void {
    status.textContent = text;
  }

  /** Restore any transform previously saved for these filenames. */
  function applySavedTransforms(list: PhotoFrame[]): number {
    const saved = loadSavedTransforms();
    let restored = 0;
    for (const f of list) {
      const t = saved[setPrefix + f.name];
      if (t) {
        f.transform = { ...IDENTITY_TRANSFORM, ...t };
        restored++;
      }
    }
    return restored;
  }

  // ── Preload sets ─────────────────────────────────────────────────────────

  interface PreloadManifest {
    name?: string;
    /** Degrees clockwise applied to every frame as a starting point. */
    rotate?: number;
    frames: string[];
  }

  /**
   * Load `public/preload/<set>/manifest.json` and its images. Lets a working
   * session resume from a URL instead of re-picking files every reload.
   */
  async function preload(set: string): Promise<void> {
    const base = `preload/${encodeURIComponent(set)}/`;
    setStatus(`Loading “${set}”…`);
    progress.hidden = false;
    progress.value = 0;

    try {
      const res = await fetch(base + "manifest.json");
      if (!res.ok) throw new Error(`manifest.json → HTTP ${res.status}`);
      const manifest: PreloadManifest = await res.json();
      if (!Array.isArray(manifest.frames) || manifest.frames.length === 0) {
        throw new Error("manifest lists no frames");
      }

      const rotation = ((manifest.rotate ?? 0) * Math.PI) / 180;
      setPrefix = `${set}/`;
      baseline = { ...IDENTITY_TRANSFORM, rotation };
      const loaded: PhotoFrame[] = [];
      for (const file of manifest.frames) {
        const imgRes = await fetch(base + encodeURIComponent(file));
        if (!imgRes.ok) throw new Error(`${file} → HTTP ${imgRes.status}`);
        loaded.push({
          name: file,
          bitmap: await createImageBitmap(await imgRes.blob()),
          transform: { ...baseline },
        });
        progress.value = Math.round((loaded.length / manifest.frames.length) * 100);
      }

      // A saved alignment always wins over the manifest's starting rotation.
      const restored = applySavedTransforms(loaded);
      frames = loaded;
      selected = 0;
      playIndex = 0;
      onFramesChanged();
      setStatus(
        restored > 0
          ? `Loaded “${manifest.name ?? set}” — restored ${restored} saved alignment${restored === 1 ? "" : "s"}`
          : `Loaded “${manifest.name ?? set}” — ${loaded.length} frames`,
      );
    } catch (err) {
      setStatus(`Preload failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      progress.hidden = true;
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────

  btnAdd.addEventListener("click", () => input.click());

  input.addEventListener("change", async () => {
    const files = input.files;
    if (!files || files.length === 0) return;

    btnAdd.disabled = true;
    progress.hidden = false;
    progress.value = 0;

    const loaded = await loadFiles(files, (cur, tot) => {
      progress.value = Math.round((cur / tot) * 100);
    });

    const added = loaded.map((f) => ({
      name: f.name,
      bitmap: f.bitmap,
      transform: { ...IDENTITY_TRANSFORM },
    }));
    // A batch is reversed within itself, then always appended — adding more
    // photos should never reorder the ones already placed.
    if (reverseToggle.checked) added.reverse();
    applySavedTransforms(added);
    frames = frames.concat(added);

    progress.hidden = true;
    btnAdd.disabled = false;
    input.value = "";

    selected = 0;
    playIndex = 0;
    onFramesChanged();
  });

  reverseToggle.addEventListener("change", () => {
    frames.reverse();
    selected = frames.length ? frames.length - 1 - selected : 0;
    playIndex = 0;
    onFramesChanged();
  });

  btnForget.addEventListener("click", () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* storage unavailable; nothing was saved anyway */
    }
    for (const f of frames) f.transform = { ...baseline };
    rebuildStrip();
    refreshSelection();
    renderPlayback();
    setStatus("Saved alignment cleared — all frames back to their starting position");
  });

  btnClear.addEventListener("click", () => {
    stopPlayback();
    frames = [];
    sheets = [];
    selected = 0;
    playIndex = 0;
    onFramesChanged();
  });

  // ── Filmstrip ────────────────────────────────────────────────────────────

  let dragFrom: number | null = null;

  function rebuildStrip(): void {
    strip.textContent = "";

    frames.forEach((frame, i) => {
      const item = document.createElement("div");
      item.className = "strip-item" + (i === selected ? " selected" : "");
      item.draggable = true;
      item.title = `${i + 1}. ${frame.name}`;

      const thumb = document.createElement("canvas");
      thumb.width = THUMB_SIDE;
      thumb.height = THUMB_SIDE;
      drawSquare(thumb.getContext("2d")!, frame.bitmap, frame.transform, THUMB_SIDE, "#000");
      item.appendChild(thumb);

      const index = document.createElement("span");
      index.className = "strip-index";
      index.textContent = String(i + 1);
      item.appendChild(index);

      const remove = document.createElement("button");
      remove.className = "strip-remove";
      remove.textContent = "✕";
      remove.title = "Remove this photo";
      remove.addEventListener("click", (e) => {
        e.stopPropagation();
        frames.splice(i, 1);
        if (selected >= frames.length) selected = Math.max(0, frames.length - 1);
        onFramesChanged();
      });
      item.appendChild(remove);

      item.addEventListener("click", () => {
        selected = i;
        if (!playing) playIndex = i;
        refreshSelection();
      });

      item.addEventListener("dragstart", () => {
        dragFrom = i;
        item.classList.add("dragging");
      });
      item.addEventListener("dragend", () => {
        dragFrom = null;
        item.classList.remove("dragging");
      });
      item.addEventListener("dragover", (e) => {
        e.preventDefault();
        item.classList.add("drop-target");
      });
      item.addEventListener("dragleave", () => item.classList.remove("drop-target"));
      item.addEventListener("drop", (e) => {
        e.preventDefault();
        item.classList.remove("drop-target");
        if (dragFrom === null || dragFrom === i) return;
        const [moved] = frames.splice(dragFrom, 1);
        frames.splice(i, 0, moved);
        selected = i;
        onFramesChanged();
      });

      strip.appendChild(item);
    });
  }

  /** Repaint only the selected thumbnail — cheap enough to run while dragging. */
  function refreshSelectedThumb(): void {
    const item = strip.children[selected] as HTMLElement | undefined;
    const thumb = item?.querySelector("canvas") as HTMLCanvasElement | null;
    if (!thumb) return;
    const ctx = thumb.getContext("2d")!;
    ctx.clearRect(0, 0, THUMB_SIDE, THUMB_SIDE);
    drawSquare(ctx, frames[selected].bitmap, frames[selected].transform, THUMB_SIDE, "#000");
  }

  // ── Alignment editor ─────────────────────────────────────────────────────

  alignCanvas.width = EDITOR_SIDE * dpr;
  alignCanvas.height = EDITOR_SIDE * dpr;
  alignCanvas.style.width = `${EDITOR_SIDE}px`;
  alignCanvas.style.height = `${EDITOR_SIDE}px`;

  function current(): PhotoFrame | null {
    return frames[selected] ?? null;
  }

  function drawGuides(ctx: CanvasRenderingContext2D): void {
    const s = EDITOR_SIDE;
    ctx.save();
    ctx.strokeStyle = "rgba(124, 158, 219, 0.55)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    for (let i = 1; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo((s * i) / 3, 0);
      ctx.lineTo((s * i) / 3, s);
      ctx.moveTo(0, (s * i) / 3);
      ctx.lineTo(s, (s * i) / 3);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
    ctx.beginPath();
    ctx.moveTo(s / 2, 0);
    ctx.lineTo(s / 2, s);
    ctx.moveTo(0, s / 2);
    ctx.lineTo(s, s / 2);
    ctx.stroke();
    ctx.restore();
  }

  function renderEditor(): void {
    const ctx = alignCanvas.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, EDITOR_SIDE, EDITOR_SIDE);
    ctx.fillStyle = "#101010";
    ctx.fillRect(0, 0, EDITOR_SIDE, EDITOR_SIDE);

    const frame = current();
    if (!frame) return;

    ctx.imageSmoothingQuality = "high";
    drawSquare(ctx, frame.bitmap, frame.transform, EDITOR_SIDE);

    const mode = onionSelect.value as OnionMode;
    if (mode !== "off") {
      const alpha = parseFloat(onionOpacity.value) / 100;
      const neighbours: PhotoFrame[] = [];
      if (mode === "prev" || mode === "both" || mode === "difference") {
        if (frames[selected - 1]) neighbours.push(frames[selected - 1]);
      }
      if (mode === "next" || mode === "both") {
        if (frames[selected + 1]) neighbours.push(frames[selected + 1]);
      }

      ctx.save();
      ctx.globalAlpha = mode === "difference" ? 1 : alpha;
      ctx.globalCompositeOperation = mode === "difference" ? "difference" : "source-over";
      for (const n of neighbours) drawSquare(ctx, n.bitmap, n.transform, EDITOR_SIDE);
      ctx.restore();
    }

    if (guidesToggle.checked) drawGuides(ctx);
  }

  function setTransform(patch: Partial<FrameTransform>): void {
    const frame = current();
    if (!frame) return;
    frame.transform = { ...frame.transform, ...patch };
    if (patch.scale !== undefined) {
      frame.transform.scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, frame.transform.scale));
    }
    syncTransformInputs();
    renderEditor();
    refreshSelectedThumb();
    scheduleSave();
    if (!playing) renderPlayback();
  }

  function syncTransformInputs(): void {
    const frame = current();
    const t = frame ? frame.transform : IDENTITY_TRANSFORM;
    zoomInput.value = String(Math.round(t.scale * 100));
    zoomValue.textContent = `${Math.round(t.scale * 100)}%`;
    const degrees = (t.rotation * 180) / Math.PI;
    rotateInput.value = degrees.toFixed(1);
    rotateValue.textContent = `${degrees.toFixed(1)}°`;
  }

  // Pan by dragging.
  let panning = false;
  let panX = 0;
  let panY = 0;

  alignCanvas.addEventListener("pointerdown", (e) => {
    if (!current()) return;
    panning = true;
    panX = e.clientX;
    panY = e.clientY;
    alignCanvas.setPointerCapture(e.pointerId);
    alignCanvas.classList.add("panning");
  });

  alignCanvas.addEventListener("pointermove", (e) => {
    if (!panning) return;
    const frame = current()!;
    setTransform({
      tx: frame.transform.tx + (e.clientX - panX) / EDITOR_SIDE,
      ty: frame.transform.ty + (e.clientY - panY) / EDITOR_SIDE,
    });
    panX = e.clientX;
    panY = e.clientY;
  });

  function endPan(e: PointerEvent): void {
    if (!panning) return;
    panning = false;
    alignCanvas.releasePointerCapture(e.pointerId);
    alignCanvas.classList.remove("panning");
  }
  alignCanvas.addEventListener("pointerup", endPan);
  alignCanvas.addEventListener("pointercancel", endPan);

  alignCanvas.addEventListener(
    "wheel",
    (e) => {
      const frame = current();
      if (!frame) return;
      e.preventDefault();
      setTransform({ scale: frame.transform.scale * Math.exp(-e.deltaY * 0.0015) });
    },
    { passive: false },
  );

  alignCanvas.addEventListener("keydown", (e) => {
    const frame = current();
    if (!frame) return;
    const step = e.shiftKey ? 0.02 : 0.002;
    const t = frame.transform;
    switch (e.key) {
      case "ArrowLeft": setTransform({ tx: t.tx - step }); break;
      case "ArrowRight": setTransform({ tx: t.tx + step }); break;
      case "ArrowUp": setTransform({ ty: t.ty - step }); break;
      case "ArrowDown": setTransform({ ty: t.ty + step }); break;
      case "+": case "=": setTransform({ scale: t.scale * 1.05 }); break;
      case "-": case "_": setTransform({ scale: t.scale / 1.05 }); break;
      case "[": setTransform({ rotation: t.rotation - (e.shiftKey ? 0.01745 : 0.00175) }); break;
      case "]": setTransform({ rotation: t.rotation + (e.shiftKey ? 0.01745 : 0.00175) }); break;
      case "n": select(selected + 1); break;
      case "p": select(selected - 1); break;
      default: return;
    }
    e.preventDefault();
  });

  zoomInput.addEventListener("input", () =>
    setTransform({ scale: parseFloat(zoomInput.value) / 100 }),
  );
  rotateInput.addEventListener("input", () =>
    setTransform({ rotation: (parseFloat(rotateInput.value) * Math.PI) / 180 }),
  );
  onionSelect.addEventListener("change", renderEditor);
  onionOpacity.addEventListener("input", renderEditor);
  guidesToggle.addEventListener("change", renderEditor);

  btnAlignPrev.addEventListener("click", () => select(selected - 1));
  btnAlignNext.addEventListener("click", () => select(selected + 1));

  btnAlignReset.addEventListener("click", () => {
    if (!current()) return;
    setTransform({ ...IDENTITY_TRANSFORM });
  });

  btnAlignCopyNext.addEventListener("click", () => {
    const frame = current();
    if (!frame || !frames[selected + 1]) return;
    frames[selected + 1].transform = { ...frame.transform };
    select(selected + 1);
    scheduleSave();
  });

  btnAlignApplyAll.addEventListener("click", () => {
    const frame = current();
    if (!frame) return;
    for (const f of frames) f.transform = { ...frame.transform };
    rebuildStrip();
    renderEditor();
    renderPlayback();
    scheduleSave();
  });

  function select(index: number): void {
    if (frames.length === 0) return;
    selected = Math.max(0, Math.min(index, frames.length - 1));
    if (!playing) playIndex = selected;
    refreshSelection();
  }

  function refreshSelection(): void {
    strip.querySelectorAll(".strip-item").forEach((el, i) =>
      el.classList.toggle("selected", i === selected),
    );
    const frame = current();
    alignLabel.textContent = frame
      ? `Frame ${selected + 1} / ${frames.length} — ${frame.name}`
      : "No photo selected";
    btnAlignPrev.disabled = selected === 0 || frames.length === 0;
    btnAlignNext.disabled = frames.length === 0 || selected === frames.length - 1;
    btnAlignCopyNext.disabled = frames.length === 0 || selected === frames.length - 1;
    syncTransformInputs();
    renderEditor();
    if (!playing) {
      scrub.value = String(selected);
      renderPlayback();
    }
  }

  // ── Playback ─────────────────────────────────────────────────────────────

  playCanvas.width = PLAY_SIDE * dpr;
  playCanvas.height = PLAY_SIDE * dpr;
  playCanvas.style.width = `${PLAY_SIDE}px`;
  playCanvas.style.height = `${PLAY_SIDE}px`;

  function renderPlayback(): void {
    const ctx = playCanvas.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, PLAY_SIDE, PLAY_SIDE);
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, PLAY_SIDE, PLAY_SIDE);
    const frame = frames[playIndex];
    if (frame) drawSquare(ctx, frame.bitmap, frame.transform, PLAY_SIDE);
    playCounter.textContent = frames.length
      ? `${playIndex + 1} / ${frames.length}`
      : "— / —";
  }

  function advance(): boolean {
    const mode = modeSelect.value;
    if (mode === "pingpong") {
      if (playIndex + playDirection >= frames.length || playIndex + playDirection < 0) {
        playDirection *= -1;
      }
      playIndex += playDirection;
      return true;
    }
    const next = playIndex + 1;
    if (next >= frames.length) {
      if (mode === "once") return false;
      playIndex = 0;
      return true;
    }
    playIndex = next;
    return true;
  }

  function tick(ts: number): void {
    if (!playing) return;
    const fps = Math.max(1, parseFloat(fpsInput.value) || 12);
    if (ts - lastFrameTime >= 1000 / fps) {
      lastFrameTime = ts;
      if (!advance()) {
        stopPlayback();
        return;
      }
      scrub.value = String(playIndex);
      renderPlayback();
    }
    requestAnimationFrame(tick);
  }

  function startPlayback(): void {
    if (frames.length < 2) return;
    playing = true;
    playDirection = 1;
    lastFrameTime = 0;
    btnPlay.textContent = "■ Stop";
    requestAnimationFrame(tick);
  }

  function stopPlayback(): void {
    playing = false;
    btnPlay.textContent = "▶ Play";
  }

  btnPlay.addEventListener("click", () => (playing ? stopPlayback() : startPlayback()));

  scrub.addEventListener("input", () => {
    stopPlayback();
    playIndex = parseInt(scrub.value) || 0;
    renderPlayback();
    // Scrubbing to a frame that stutters should drop you straight into aligning it.
    selected = playIndex;
    refreshSelection();
  });

  // ── Sheets, PDF, PNGs ────────────────────────────────────────────────────

  btnAdvanced.addEventListener("click", () => {
    advancedPanel.hidden = !advancedPanel.hidden;
    btnAdvanced.textContent = advancedPanel.hidden ? "Advanced ▾" : "Advanced ▴";
  });

  // ── Rolling-paper strips ─────────────────────────────────────────────────

  /**
   * Resolve the grid and copy count for a build. In strip mode the cell size
   * comes from the paper rather than from cols/rows, and the sequence repeats
   * to fill whatever that grid leaves room for.
   */
  function resolveBuild(config: LayoutConfig): {
    config: LayoutConfig;
    copies: number;
    packing: StripPacking | null;
  } {
    if (!stripMode.checked || frames.length === 0) {
      // "Fill sheet" means the same thing here as in strip mode: repeat the
      // sequence for as many whole copies as the grid holds.
      const cells = config.cols * config.rows;
      const copies =
        fillSheet.checked && frames.length > 0
          ? Math.max(1, Math.floor(cells / frames.length))
          : Math.max(1, parseInt(copiesInput.value) || 1);
      return { config, copies, packing: null };
    }

    const packing = solveStripCell(
      config.pageSizeMm,
      config.marginMm,
      Math.max(1, parseFloat(stripWidth.value) || 16),
      Math.max(1, parseFloat(stripLength.value) || 42),
      Math.max(0, parseFloat(stripTolerance.value) || 0),
      frames.length,
      stripOrientation.value === "horizontal",
    );
    if (!packing) return { config, copies: 1, packing: null };

    const copies = fillSheet.checked
      ? Math.max(1, packing.copies)
      : Math.max(1, parseInt(copiesInput.value) || 1);

    return {
      config: { ...config, cols: packing.cols, rows: packing.rows },
      copies,
      packing,
    };
  }

  function updateStripReadout(): void {
    copiesInput.disabled = fillSheet.checked;
    const on = stripMode.checked;
    stripReadout.classList.toggle("active", on);

    if (frames.length === 0) {
      stripReadout.textContent = on
        ? "Load photos to size the grid."
        : "Using the Grid settings.";
      return;
    }

    const base = readLayoutConfig(controlsForm);
    const { packing, copies } = resolveBuild(base);

    if (!on) {
      const cells = base.cols * base.rows;
      const sheets = Math.ceil((copies * frames.length) / cells);
      stripReadout.textContent =
        `Grid ${base.cols} × ${base.rows} = ${cells} cells. ` +
        `${copies} cop${copies === 1 ? "y" : "ies"} of ${frames.length} on ${sheets} sheet${sheets === 1 ? "" : "s"}.`;
      return;
    }

    if (!packing) {
      stripReadout.textContent =
        "No length in that range divides the sheet — widen the flex, or shorten the strip.";
      return;
    }

    const [w, h] = packing.cellMm;
    const square = Math.min(w, h);
    const sheets = Math.ceil((copies * frames.length) / packing.cells);
    stripReadout.textContent =
      `${w.toFixed(1)} × ${h.toFixed(1)}mm — ${packing.cols} × ${packing.rows} = ${packing.cells} cells. ` +
      `${copies} cop${copies === 1 ? "y" : "ies"} of ${frames.length} on ${sheets} sheet${sheets === 1 ? "" : "s"}` +
      `${fillSheet.checked ? `, ${packing.spare} cell${packing.spare === 1 ? "" : "s"} spare` : ""}. ` +
      `Image ${square.toFixed(1)}mm square, ${(Math.max(w, h) - square).toFixed(1)}mm roll strip.`;
  }

  for (const el of [stripMode, stripWidth, stripLength, stripTolerance, stripOrientation, fillSheet, copiesInput]) {
    el.addEventListener("input", updateStripReadout);
    el.addEventListener("change", updateStripReadout);
  }
  controlsForm.addEventListener("change", updateStripReadout);

  /** Solid colours can back the square; texture URLs are left to the sheet. */
  function squareBackground(background: string): string | undefined {
    return /^(data:|blob:|https?:)/.test(background) ? undefined : background;
  }

  async function buildSheets(): Promise<void> {
    if (frames.length === 0) return;
    stopPlayback();

    btnBuild.disabled = true;
    btnPdf.disabled = true;
    btnPng.disabled = true;
    progress.hidden = false;
    progress.value = 0;

    const { config, copies } = resolveBuild(readLayoutConfig(controlsForm));
    // Each copy restarts at 1, so every cut stack reads 1..N.
    const buildConfig: LayoutConfig = {
      ...config,
      frameNumberModulo: copies > 1 ? frames.length : null,
    };

    const dims = computeDimensions(buildConfig);
    // Bake at 2x the size the cell will draw, so `contain` downsamples rather
    // than upscales.
    const side = Math.max(64, Math.round(Math.min(dims.usableW, dims.cellPx[1]) * 2));

    const baked = await bakeSquares(
      frames,
      side,
      squareBackground(buildConfig.background),
      (cur, tot) => (progress.value = Math.round((cur / tot) * 50)),
    );

    // Repeat the sequence; the same bitmaps are reused, not re-baked.
    const bitmaps: ImageBitmap[] = [];
    for (let c = 0; c < copies; c++) bitmaps.push(...baked);

    sheets = await renderSheets(bitmaps, buildConfig, (cur, tot) => {
      progress.value = 50 + Math.round((cur / tot) * 50);
    });

    progress.hidden = true;
    btnBuild.disabled = false;
    btnPdf.disabled = false;
    btnPng.disabled = false;
    showSheet(0);
  }

  btnBuild.addEventListener("click", buildSheets);

  function showSheet(index: number): void {
    if (sheets.length === 0) {
      sheetCounter.textContent = "Sheet — / —";
      btnSheetPrev.disabled = true;
      btnSheetNext.disabled = true;
      return;
    }
    sheetIndex = Math.max(0, Math.min(index, sheets.length - 1));
    sheetCounter.textContent = `Sheet ${sheetIndex + 1} / ${sheets.length}`;
    btnSheetPrev.disabled = sheetIndex === 0;
    btnSheetNext.disabled = sheetIndex === sheets.length - 1;

    const src = sheets[sheetIndex];
    sheetCanvas.width = src.width;
    sheetCanvas.height = src.height;
    sheetCanvas.getContext("2d")!.drawImage(src, 0, 0);
  }

  btnSheetPrev.addEventListener("click", () => showSheet(sheetIndex - 1));
  btnSheetNext.addEventListener("click", () => showSheet(sheetIndex + 1));

  btnPdf.addEventListener("click", async () => {
    if (sheets.length === 0) return;
    const { config } = resolveBuild(readLayoutConfig(controlsForm));
    btnPdf.disabled = true;
    await savePdf(sheets, "flipbook.pdf", config.pageSizeMm);
    btnPdf.disabled = false;
  });

  btnPng.addEventListener("click", async () => {
    if (sheets.length === 0) return;
    btnPng.disabled = true;
    await savePages(sheets, "flipbook-pages.zip");
    btnPng.disabled = false;
  });

  // ── Shared refresh ───────────────────────────────────────────────────────

  function onFramesChanged(): void {
    countLabel.textContent = frames.length
      ? `${frames.length} photo${frames.length === 1 ? "" : "s"}`
      : "No photos loaded";
    alignEmpty.hidden = frames.length > 0;
    scrub.max = String(Math.max(0, frames.length - 1));
    scrub.disabled = frames.length === 0;
    playIndex = Math.min(playIndex, Math.max(0, frames.length - 1));
    btnPlay.disabled = frames.length < 2;
    btnBuild.disabled = frames.length === 0;
    btnClear.disabled = frames.length === 0;
    btnAlignReset.disabled = frames.length === 0;
    btnAlignApplyAll.disabled = frames.length === 0;
    rebuildStrip();
    refreshSelection();
    renderPlayback();
    updateStripReadout();
  }

  onFramesChanged();

  const preloadSet = new URLSearchParams(location.search).get("preload");
  if (preloadSet) void preload(preloadSet);
}
