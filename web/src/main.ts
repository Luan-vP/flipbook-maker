import { loadFiles, UploadedFrame } from "./ui/upload";
import { readLayoutConfig } from "./ui/controls";
import { renderSheets } from "./core/layout";
import { savePdf, savePages } from "./core/io";
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
import { PAPER_SIZES_MM } from "./core/paper";

// ── State ──────────────────────────────────────────────────────────────────

let uploadedFrames: UploadedFrame[] = [];
let renderedPages: HTMLCanvasElement[] = [];
let currentSheetIndex = 0;

// ── DOM refs ───────────────────────────────────────────────────────────────

const uploadInput = document.getElementById("upload-input") as HTMLInputElement;
const uploadArea = document.getElementById("upload-area") as HTMLDivElement;
const thumbnailStrip = document.getElementById("thumbnail-strip") as HTMLDivElement;
const frameCount = document.getElementById("frame-count") as HTMLSpanElement;
const controlsForm = document.getElementById("controls") as HTMLFormElement;
const btnRender = document.getElementById("btn-render") as HTMLButtonElement;
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

// ── Upload handling ────────────────────────────────────────────────────────

uploadInput.addEventListener("change", handleUpload);

uploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadArea.classList.add("drag-over");
});
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  if (e.dataTransfer?.files) handleFileList(e.dataTransfer.files);
});

async function handleUpload() {
  if (uploadInput.files) handleFileList(uploadInput.files);
}

async function handleFileList(files: FileList) {
  btnRender.disabled = true;
  btnDownloadPdf.disabled = true;
  btnDownloadPng.disabled = true;
  frameCount.textContent = "Loading…";

  uploadedFrames = await loadFiles(files);
  frameCount.textContent = `${uploadedFrames.length} frame${uploadedFrames.length !== 1 ? "s" : ""}`;
  renderThumbnails();
  btnRender.disabled = uploadedFrames.length === 0;
  renderedPages = [];
  currentSheetIndex = 0;
  clearPreview();
}

function renderThumbnails() {
  thumbnailStrip.innerHTML = "";
  const max = Math.min(uploadedFrames.length, 12);
  for (let i = 0; i < max; i++) {
    const c = document.createElement("canvas");
    c.width = 48;
    c.height = 48;
    c.getContext("2d")!.drawImage(uploadedFrames[i].bitmap, 0, 0, 48, 48);
    c.title = uploadedFrames[i].name;
    thumbnailStrip.appendChild(c);
  }
  if (uploadedFrames.length > max) {
    const more = document.createElement("span");
    more.className = "more-badge";
    more.textContent = `+${uploadedFrames.length - max}`;
    thumbnailStrip.appendChild(more);
  }
}

// ── Render ─────────────────────────────────────────────────────────────────

btnRender.addEventListener("click", async () => {
  if (uploadedFrames.length === 0) return;

  btnRender.disabled = true;
  btnDownloadPdf.disabled = true;
  btnDownloadPng.disabled = true;
  renderProgress.hidden = false;
  renderProgress.value = 0;

  const config = readLayoutConfig(controlsForm);

  renderedPages = await renderSheets(
    uploadedFrames.map((f) => f.bitmap),
    config,
    (current, total) => {
      renderProgress.value = Math.round((current / total) * 100);
    },
  );

  renderProgress.hidden = true;
  currentSheetIndex = 0;
  showSheet(0);

  btnRender.disabled = false;
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

// ── Live preview debounce ──────────────────────────────────────────────────

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

controlsForm.addEventListener("change", () => {
  if (renderedPages.length === 0 || uploadedFrames.length === 0) return;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const config = readLayoutConfig(controlsForm);
    const preview = await renderSheets(
      uploadedFrames.map((f) => f.bitmap),
      config,
    );
    renderedPages = preview;
    showSheet(currentSheetIndex);
  }, 300);
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
