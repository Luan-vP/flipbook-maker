import { loadVideo, UploadedFrame } from "./ui/upload";
import { readLayoutConfig } from "./ui/controls";
import { renderSheets } from "./core/layout";
import { savePdf, savePages } from "./core/io";
import { renderMultiChapterSheets } from "./multi/chapter";
import { drawCards } from "./tarot/deck";
import {
  renderTarotGrid,
  renderTarotZine,
  downloadTarotPdf,
  DEFAULT_TAROT_CONFIG,
} from "./tarot/render";
import {
  renderCooticeCatcher,
  downloadCooticePdf,
  DEFAULT_COOTIE_CONFIG,
} from "./cootie/template";
import { PAPER_SIZES_MM, FRAME_SIZE_PRESETS_MM, gridForFrameSize } from "./core/paper";

// ── State ──────────────────────────────────────────────────────────────────

let uploadedFrames: UploadedFrame[] = [];
let renderedPages: HTMLCanvasElement[] = [];
let currentSheetIndex = 0;

// ── DOM refs ───────────────────────────────────────────────────────────────

const uploadInput = document.getElementById("upload-input") as HTMLInputElement;
const fileName = document.getElementById("file-name") as HTMLSpanElement;
const btnGo = document.getElementById("btn-go") as HTMLButtonElement;
const btnAdvancedToggle = document.getElementById("btn-advanced-toggle") as HTMLButtonElement;
const advancedPanel = document.getElementById("advanced-panel") as HTMLDivElement;
const controlsForm = document.getElementById("controls") as HTMLFormElement;
const btnDownloadPdf = document.getElementById("btn-download-pdf") as HTMLButtonElement;
const btnDownloadPng = document.getElementById("btn-download-png") as HTMLButtonElement;
const renderProgress = document.getElementById("render-progress") as HTMLProgressElement;
const previewCanvas = document.getElementById("preview-canvas") as HTMLCanvasElement;
const sheetCounter = document.getElementById("sheet-counter") as HTMLSpanElement;
const btnPrevSheet = document.getElementById("btn-prev-sheet") as HTMLButtonElement;
const btnNextSheet = document.getElementById("btn-next-sheet") as HTMLButtonElement;

// ── Tab navigation ─────────────────────────────────────────────────────────

document.querySelectorAll<HTMLButtonElement>(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll<HTMLElement>(".tab-section").forEach((s) => (s.hidden = true));
    btn.classList.add("active");
    const target = btn.dataset.tab!;
    document.getElementById(`tab-${target}`)!.hidden = false;
  });
});

// ── Frame size presets (e.g. filter-tip) ───────────────────────────────────

function wireFrameSizePreset(form: HTMLFormElement) {
  const select = form.querySelector<HTMLSelectElement>('[name="frameSize"]');
  if (!select) return;
  select.addEventListener("change", () => {
    const frameSizeMm = FRAME_SIZE_PRESETS_MM[select.value];
    if (!frameSizeMm) return;

    const paperSelect = form.querySelector<HTMLSelectElement>('[name="paper"]');
    if (paperSelect) paperSelect.value = "a4";
    const portraitRadio = form.querySelector<HTMLInputElement>('[name="orientation"][value="portrait"]');
    if (portraitRadio) portraitRadio.checked = true;

    const marginInput = form.querySelector<HTMLInputElement>('[name="marginMm"]');
    const marginMm = marginInput ? parseFloat(marginInput.value) || 0 : 5;

    const [cols, rows] = gridForFrameSize(PAPER_SIZES_MM["a4"], marginMm, frameSizeMm);
    const colsInput = form.querySelector<HTMLInputElement>('[name="cols"]');
    if (colsInput) colsInput.value = String(cols);
    const rowsInput = form.querySelector<HTMLInputElement>('[name="rows"]');
    if (rowsInput) rowsInput.value = String(rows);
  });
}

// ── Advanced settings toggle ───────────────────────────────────────────────

btnAdvancedToggle.addEventListener("click", () => {
  advancedPanel.hidden = !advancedPanel.hidden;
  btnAdvancedToggle.textContent = advancedPanel.hidden ? "Advanced ▾" : "Advanced ▴";
});

// ── Upload handling ────────────────────────────────────────────────────────

uploadInput.addEventListener("change", () => {
  const file = uploadInput.files?.[0];
  if (file) {
    fileName.textContent = file.name;
    btnGo.disabled = false;
  } else {
    fileName.textContent = "No file selected";
    btnGo.disabled = true;
  }
  renderedPages = [];
  currentSheetIndex = 0;
  clearPreview();
});

// ── Go button ──────────────────────────────────────────────────────────────

btnGo.addEventListener("click", async () => {
  const file = uploadInput.files?.[0];
  if (!file) return;

  btnGo.disabled = true;
  btnDownloadPdf.disabled = true;
  btnDownloadPng.disabled = true;
  renderProgress.hidden = false;
  renderProgress.value = 0;

  const config = readLayoutConfig(controlsForm);
  const pages = Math.max(1, parseInt((controlsForm.querySelector('[name="pages"]') as HTMLInputElement)?.value || "3") || 3);
  const totalFrames = pages * config.cols * config.rows;

  // Phase 1: extract frames (0–50%)
  uploadedFrames = await loadVideo(file, totalFrames, (current, total) => {
    renderProgress.value = Math.round((current / total) * 50);
  });

  // Phase 2: render sheets (50–100%)
  renderedPages = await renderSheets(
    uploadedFrames.map((f) => f.bitmap),
    config,
    (current, total) => {
      renderProgress.value = 50 + Math.round((current / total) * 50);
    },
  );

  renderProgress.hidden = true;
  currentSheetIndex = 0;
  showSheet(0);

  btnGo.disabled = false;
  btnDownloadPdf.disabled = false;
  btnDownloadPng.disabled = false;
});

// ── Preview navigation ─────────────────────────────────────────────────────

btnPrevSheet.addEventListener("click", () => showSheet(currentSheetIndex - 1));
btnNextSheet.addEventListener("click", () => showSheet(currentSheetIndex + 1));

function showSheet(index: number) {
  if (renderedPages.length === 0) return;
  currentSheetIndex = Math.max(0, Math.min(index, renderedPages.length - 1));
  sheetCounter.textContent = `Sheet ${currentSheetIndex + 1} / ${renderedPages.length}`;
  btnPrevSheet.disabled = currentSheetIndex === 0;
  btnNextSheet.disabled = currentSheetIndex === renderedPages.length - 1;

  const src = renderedPages[currentSheetIndex];
  previewCanvas.width = src.width;
  previewCanvas.height = src.height;
  previewCanvas.getContext("2d")!.drawImage(src, 0, 0);
}

function clearPreview() {
  const ctx = previewCanvas.getContext("2d")!;
  ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
  sheetCounter.textContent = "Sheet — / —";
  btnPrevSheet.disabled = true;
  btnNextSheet.disabled = true;
}

// ── Download ───────────────────────────────────────────────────────────────

btnDownloadPdf.addEventListener("click", async () => {
  if (renderedPages.length === 0) return;
  const config = readLayoutConfig(controlsForm);
  btnDownloadPdf.disabled = true;
  await savePdf(renderedPages, "flipbook.pdf", config.pageSizeMm);
  btnDownloadPdf.disabled = false;
});

btnDownloadPng.addEventListener("click", async () => {
  if (renderedPages.length === 0) return;
  btnDownloadPng.disabled = true;
  await savePages(renderedPages, "flipbook-pages.zip");
  btnDownloadPng.disabled = false;
});


// ── Tarot tab ──────────────────────────────────────────────────────────────

const tarotForm = document.getElementById("tarot-controls") as HTMLFormElement;
const btnTarotRender = document.getElementById("btn-tarot-render") as HTMLButtonElement;
const btnTarotDownload = document.getElementById("btn-tarot-download") as HTMLButtonElement;
const tarotCanvas = document.getElementById("tarot-canvas") as HTMLCanvasElement;

let tarotPages: HTMLCanvasElement[] = [];

btnTarotRender.addEventListener("click", () => {
  const data = new FormData(tarotForm);
  const seed = parseInt(data.get("seed") as string);
  const isRandom = data.get("tarotMode") === "random";
  const printMode = data.get("print") === "on";
  const paper = (data.get("paper") as string) || "a4";

  const tarotConfig = {
    ...DEFAULT_TAROT_CONFIG,
    paper,
    printMode,
    background: printMode ? "white" : DEFAULT_TAROT_CONFIG.background,
    foreground: printMode ? "black" : DEFAULT_TAROT_CONFIG.foreground,
  };

  const effectiveSeed = isNaN(seed) ? undefined : seed;

  if (isRandom) {
    const cards = drawCards(8, effectiveSeed);
    tarotPages = [renderTarotGrid(cards, tarotConfig)];
  } else {
    const [past, present, future] = drawCards(3, effectiveSeed);
    tarotPages = renderTarotZine(past, present, future, tarotConfig);
  }

  const first = tarotPages[0];
  tarotCanvas.width = first.width;
  tarotCanvas.height = first.height;
  tarotCanvas.getContext("2d")!.drawImage(first, 0, 0);
  btnTarotDownload.disabled = false;
});

btnTarotDownload.addEventListener("click", async () => {
  if (tarotPages.length === 0) return;
  const data = new FormData(tarotForm);
  const paper = (data.get("paper") as string) || "a4";
  const isRandom = data.get("tarotMode") === "random";
  const pageMm = PAPER_SIZES_MM[paper];
  const sizeMm: [number, number] = isRandom
    ? [pageMm[1], pageMm[0]]
    : [pageMm[0], pageMm[1]];
  btnTarotDownload.disabled = true;
  await downloadTarotPdf(tarotPages, "tarot.pdf", sizeMm);
  btnTarotDownload.disabled = false;
});

// ── Cootie tab ─────────────────────────────────────────────────────────────

const cootieForm = document.getElementById("cootie-controls") as HTMLFormElement;
const btnCootieRender = document.getElementById("btn-cootie-render") as HTMLButtonElement;
const btnCootieDownload = document.getElementById("btn-cootie-download") as HTMLButtonElement;
const cootieCanvas = document.getElementById("cootie-canvas") as HTMLCanvasElement;

let cootieCanvas_rendered: HTMLCanvasElement | null = null;

function getCootieConfig() {
  const data = new FormData(cootieForm);
  const colorsStr = (data.get("colors") as string) || DEFAULT_COOTIE_CONFIG.colors.join(",");
  const fortunesStr = (data.get("fortunes") as string) || DEFAULT_COOTIE_CONFIG.fortunes.join(",");
  const colors = colorsStr.split(",").map((c) => c.trim()).filter(Boolean);
  const fortunes = fortunesStr.split(",").map((f) => f.trim()).filter(Boolean);
  const paper = (data.get("paper") as string) || "a4";
  const bg = ((data.get("background") as string) || "white").trim();
  return {
    ...DEFAULT_COOTIE_CONFIG,
    colors,
    fortunes,
    paper,
    background: bg,
    showInstructions: data.get("noInstructions") !== "on",
  };
}

btnCootieRender.addEventListener("click", () => {
  const config = getCootieConfig();
  cootieCanvas_rendered = renderCooticeCatcher(config);
  cootieCanvas.width = cootieCanvas_rendered.width;
  cootieCanvas.height = cootieCanvas_rendered.height;
  cootieCanvas.getContext("2d")!.drawImage(cootieCanvas_rendered, 0, 0);
  btnCootieDownload.disabled = false;
});

let cootieDebounce: ReturnType<typeof setTimeout> | null = null;
cootieForm.addEventListener("change", () => {
  if (cootieDebounce) clearTimeout(cootieDebounce);
  cootieDebounce = setTimeout(() => btnCootieRender.click(), 400);
});

btnCootieDownload.addEventListener("click", async () => {
  if (!cootieCanvas_rendered) return;
  const data = new FormData(cootieForm);
  const paper = (data.get("paper") as string) || "a4";
  const pageMm = PAPER_SIZES_MM[paper] as [number, number];
  btnCootieDownload.disabled = true;
  await downloadCooticePdf(cootieCanvas_rendered, "cootie_catcher.pdf", pageMm);
  btnCootieDownload.disabled = false;
});

// ── Multi-Chapter tab ──────────────────────────────────────────────────────

interface ChapterState {
  id: number;
  file: File;
  name: string;
  duration: number;
  fps: number;
  element: HTMLElement;
  fpsInput: HTMLInputElement;
  framesLabel: HTMLElement;
}

let nextChapterId = 0;
const multiChapters: ChapterState[] = [];
let multiRenderedPages: HTMLCanvasElement[] = [];
let multiCurrentSheet = 0;

const btnAddChapter = document.getElementById("btn-add-chapter") as HTMLButtonElement;
const multiFileInput = document.getElementById("multi-file-input") as HTMLInputElement;
const multiChapterList = document.getElementById("multi-chapter-list") as HTMLDivElement;
const multiBalanceCheckbox = document.getElementById("multi-balance") as HTMLInputElement;
const multiBalanceTargetWrap = document.getElementById("multi-balance-target-wrap") as HTMLSpanElement;
const multiBalanceTarget = document.getElementById("multi-balance-target") as HTMLInputElement;
const multiBalanceInfo = document.getElementById("multi-balance-info") as HTMLSpanElement;
const btnMultiGo = document.getElementById("btn-multi-go") as HTMLButtonElement;
const multiProgress = document.getElementById("multi-progress") as HTMLProgressElement;
const btnMultiPdf = document.getElementById("btn-multi-pdf") as HTMLButtonElement;
const btnMultiPng = document.getElementById("btn-multi-png") as HTMLButtonElement;
const multiPreviewCanvas = document.getElementById("multi-preview-canvas") as HTMLCanvasElement;
const multiSheetCounter = document.getElementById("multi-sheet-counter") as HTMLSpanElement;
const btnMultiPrev = document.getElementById("btn-multi-prev") as HTMLButtonElement;
const btnMultiNext = document.getElementById("btn-multi-next") as HTMLButtonElement;
const btnMultiAdvancedToggle = document.getElementById("btn-multi-advanced-toggle") as HTMLButtonElement;
const multiAdvancedPanel = document.getElementById("multi-advanced-panel") as HTMLDivElement;
const multiControlsForm = document.getElementById("multi-controls") as HTMLFormElement;

wireFrameSizePreset(controlsForm);
wireFrameSizePreset(multiControlsForm);

btnMultiAdvancedToggle.addEventListener("click", () => {
  multiAdvancedPanel.hidden = !multiAdvancedPanel.hidden;
  btnMultiAdvancedToggle.textContent = multiAdvancedPanel.hidden ? "Advanced ▾" : "Advanced ▴";
});

// ── Balance controls ───────────────────────────────────────────────────────

multiBalanceCheckbox.addEventListener("change", () => {
  multiBalanceTargetWrap.hidden = !multiBalanceCheckbox.checked;
  updateChapterLabels();
});

multiBalanceTarget.addEventListener("input", updateChapterLabels);

function getExplicitTarget(): number | null {
  const v = parseInt(multiBalanceTarget.value);
  return !isNaN(v) && v > 0 ? v : null;
}

function computeBalanceTarget(): number {
  const explicit = getExplicitTarget();
  if (explicit !== null) return explicit;
  const readyChapters = multiChapters.filter((c) => c.duration > 0);
  if (readyChapters.length === 0) return 0;
  return Math.min(...readyChapters.map((c) => Math.max(1, Math.round(c.duration * c.fps))));
}

function updateChapterLabels() {
  const balance = multiBalanceCheckbox.checked;
  const target = balance ? computeBalanceTarget() : null;

  for (const ch of multiChapters) {
    if (ch.duration === 0) {
      ch.framesLabel.textContent = "loading…";
      continue;
    }
    if (balance && target !== null && target > 0) {
      const effFps = target / ch.duration;
      ch.framesLabel.textContent = `→ ${target} frames (${effFps.toFixed(1)} fps)`;
      ch.fpsInput.disabled = false; // still editable as hint for auto-target
    } else {
      const n = Math.max(1, Math.round(ch.duration * ch.fps));
      ch.framesLabel.textContent = `→ ${n} frames`;
      ch.fpsInput.disabled = false;
    }
  }

  if (balance && target !== null && target > 0) {
    multiBalanceInfo.textContent = `All chapters balanced to ${target} frames`;
  } else if (balance) {
    multiBalanceInfo.textContent = multiChapters.length >= 2 ? "Add chapters to compute target" : "";
  } else {
    const counts = multiChapters.filter((c) => c.duration > 0).map((c) => Math.max(1, Math.round(c.duration * c.fps)));
    if (counts.length >= 2) {
      const min = Math.min(...counts);
      const max = Math.max(...counts);
      if (min !== max) {
        multiBalanceInfo.textContent = `Frame counts differ (${min}–${max}); shortest sets the limit`;
      } else {
        multiBalanceInfo.textContent = "";
      }
    } else {
      multiBalanceInfo.textContent = "";
    }
  }

  updateMultiGoBtn();
}

function updateMultiGoBtn() {
  btnMultiGo.disabled =
    multiChapters.length < 2 || multiChapters.some((c) => c.duration === 0);
}

// ── Add / remove chapters ──────────────────────────────────────────────────

btnAddChapter.addEventListener("click", () => multiFileInput.click());

multiFileInput.addEventListener("change", () => {
  const file = multiFileInput.files?.[0];
  if (file) addChapter(file);
  multiFileInput.value = "";
});

function addChapter(file: File) {
  const id = nextChapterId++;

  const el = document.createElement("div");
  el.className = "chapter-item";

  const removeBtn = document.createElement("button");
  removeBtn.textContent = "✕";
  removeBtn.className = "chapter-remove-btn";
  removeBtn.title = "Remove chapter";

  const nameSpan = document.createElement("span");
  nameSpan.className = "chapter-name";
  nameSpan.textContent = file.name;
  nameSpan.title = file.name;

  const durationSpan = document.createElement("span");
  durationSpan.className = "chapter-duration";
  durationSpan.textContent = "…";

  const fpsLabel = document.createElement("label");
  fpsLabel.className = "chapter-fps-label";
  fpsLabel.textContent = "FPS ";
  const fpsInput = document.createElement("input");
  fpsInput.type = "number";
  fpsInput.value = "10";
  fpsInput.min = "1";
  fpsInput.max = "60";
  fpsInput.step = "0.5";
  fpsInput.className = "chapter-fps-input";
  fpsLabel.appendChild(fpsInput);

  const framesLabel = document.createElement("span");
  framesLabel.className = "chapter-frames";
  framesLabel.textContent = "loading…";

  el.appendChild(removeBtn);
  el.appendChild(nameSpan);
  el.appendChild(durationSpan);
  el.appendChild(fpsLabel);
  el.appendChild(framesLabel);
  multiChapterList.appendChild(el);

  const state: ChapterState = {
    id,
    file,
    name: file.name,
    duration: 0,
    fps: 10,
    element: el,
    fpsInput,
    framesLabel,
  };
  multiChapters.push(state);

  // Load video metadata to get duration
  const url = URL.createObjectURL(file);
  const vid = document.createElement("video");
  vid.preload = "metadata";
  vid.src = url;
  vid.addEventListener(
    "loadedmetadata",
    () => {
      state.duration = vid.duration;
      durationSpan.textContent = `${vid.duration.toFixed(1)} s`;
      URL.revokeObjectURL(url);
      updateChapterLabels();
    },
    { once: true },
  );

  removeBtn.addEventListener("click", () => {
    const idx = multiChapters.findIndex((c) => c.id === id);
    if (idx !== -1) multiChapters.splice(idx, 1);
    el.remove();
    updateChapterLabels();
  });

  fpsInput.addEventListener("input", () => {
    state.fps = Math.max(0.1, parseFloat(fpsInput.value) || 10);
    updateChapterLabels();
  });

  updateMultiGoBtn();
}

// ── Go ─────────────────────────────────────────────────────────────────────

btnMultiGo.addEventListener("click", async () => {
  if (multiChapters.length < 2) return;

  btnMultiGo.disabled = true;
  btnMultiPdf.disabled = true;
  btnMultiPng.disabled = true;
  multiProgress.hidden = false;
  multiProgress.value = 0;

  const balance = multiBalanceCheckbox.checked;
  const balanceCount = balance ? computeBalanceTarget() : null;

  const config = readLayoutConfig(multiControlsForm);

  // Phase 1: extract frames from each chapter (0–60%)
  const chapterFrames: { name: string; frames: ImageBitmap[] }[] = [];
  for (let i = 0; i < multiChapters.length; i++) {
    const ch = multiChapters[i];
    const frameCount = balanceCount !== null
      ? balanceCount
      : Math.max(1, Math.round(ch.duration * ch.fps));

    const frames = await loadVideo(ch.file, frameCount, (cur, tot) => {
      const chapterBase = (i / multiChapters.length) * 60;
      const chapterSlice = (1 / multiChapters.length) * 60;
      multiProgress.value = Math.round(chapterBase + (cur / tot) * chapterSlice);
    });

    chapterFrames.push({ name: ch.name, frames: frames.map((f) => f.bitmap) });
  }

  // Phase 2: render sheets (60–100%)
  multiRenderedPages = await renderMultiChapterSheets(
    chapterFrames,
    config,
    (cur, tot) => {
      multiProgress.value = 60 + Math.round((cur / tot) * 40);
    },
  );

  multiProgress.hidden = true;
  multiCurrentSheet = 0;
  showMultiSheet(0);

  btnMultiGo.disabled = false;
  btnMultiPdf.disabled = false;
  btnMultiPng.disabled = false;
});

// ── Preview navigation ─────────────────────────────────────────────────────

btnMultiPrev.addEventListener("click", () => showMultiSheet(multiCurrentSheet - 1));
btnMultiNext.addEventListener("click", () => showMultiSheet(multiCurrentSheet + 1));

function showMultiSheet(index: number) {
  if (multiRenderedPages.length === 0) return;
  multiCurrentSheet = Math.max(0, Math.min(index, multiRenderedPages.length - 1));
  multiSheetCounter.textContent = `Sheet ${multiCurrentSheet + 1} / ${multiRenderedPages.length}`;
  btnMultiPrev.disabled = multiCurrentSheet === 0;
  btnMultiNext.disabled = multiCurrentSheet === multiRenderedPages.length - 1;

  const src = multiRenderedPages[multiCurrentSheet];
  multiPreviewCanvas.width = src.width;
  multiPreviewCanvas.height = src.height;
  multiPreviewCanvas.getContext("2d")!.drawImage(src, 0, 0);
}

// ── Download ───────────────────────────────────────────────────────────────

btnMultiPdf.addEventListener("click", async () => {
  if (multiRenderedPages.length === 0) return;
  const config = readLayoutConfig(multiControlsForm);
  btnMultiPdf.disabled = true;
  await savePdf(multiRenderedPages, "multi-chapter.pdf", config.pageSizeMm);
  btnMultiPdf.disabled = false;
});

btnMultiPng.addEventListener("click", async () => {
  if (multiRenderedPages.length === 0) return;
  btnMultiPng.disabled = true;
  await savePages(multiRenderedPages, "multi-chapter-pages.zip");
  btnMultiPng.disabled = false;
});
