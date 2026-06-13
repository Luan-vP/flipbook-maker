import { loadVideo, UploadedFrame } from "./ui/upload";
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
