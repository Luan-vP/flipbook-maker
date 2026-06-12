import jsPDF from "jspdf";
import JSZip from "jszip";

function triggerDownload(url: string, filename: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function savePdf(
  canvases: HTMLCanvasElement[],
  filename: string,
  pageSizeMm: [number, number],
): Promise<void> {
  const [w, h] = pageSizeMm;
  const orientation = w > h ? "landscape" : "portrait";
  const pdf = new jsPDF({ orientation, unit: "mm", format: [w, h] });

  for (let i = 0; i < canvases.length; i++) {
    if (i > 0) pdf.addPage([w, h], orientation);
    const dataUrl = canvases[i].toDataURL("image/jpeg", 0.92);
    pdf.addImage(dataUrl, "JPEG", 0, 0, w, h);
  }

  pdf.save(filename);
}

export async function savePages(
  canvases: HTMLCanvasElement[],
  filename: string,
): Promise<void> {
  const zip = new JSZip();
  const folder = zip.folder("pages")!;

  for (let i = 0; i < canvases.length; i++) {
    const num = String(i + 1).padStart(3, "0");
    const blob = await new Promise<Blob>((resolve) =>
      canvases[i].toBlob((b) => resolve(b!), "image/png"),
    );
    folder.file(`page_${num}.png`, blob);
  }

  const zipBlob = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(zipBlob);
  triggerDownload(url, filename);
}
