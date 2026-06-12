import JSZip from "jszip";
import { naturalSort } from "../core/sort";

export interface UploadedFrame {
  name: string;
  bitmap: ImageBitmap;
}

async function loadImageBitmap(blob: Blob): Promise<ImageBitmap> {
  return createImageBitmap(blob);
}

export async function loadFiles(files: FileList | File[]): Promise<UploadedFrame[]> {
  const fileArray = Array.from(files);

  // If exactly one ZIP file, extract it
  if (fileArray.length === 1 && fileArray[0].name.toLowerCase().endsWith(".zip")) {
    return loadZip(fileArray[0]);
  }

  const pngs = fileArray.filter((f) => f.type === "image/png" || f.name.toLowerCase().endsWith(".png"));
  const sortedNames = naturalSort(pngs.map((f) => f.name));
  const nameToFile = new Map(pngs.map((f) => [f.name, f]));

  const frames: UploadedFrame[] = [];
  for (const name of sortedNames) {
    const file = nameToFile.get(name)!;
    const bitmap = await loadImageBitmap(file);
    frames.push({ name, bitmap });
  }
  return frames;
}

async function loadZip(file: File): Promise<UploadedFrame[]> {
  const zip = await JSZip.loadAsync(file);
  const entries: { name: string; blob: Blob }[] = [];

  for (const [path, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;
    const filename = path.split("/").pop() ?? path;
    if (!filename.toLowerCase().endsWith(".png")) continue;
    const blob = await entry.async("blob");
    entries.push({ name: filename, blob });
  }

  const sortedNames = naturalSort(entries.map((e) => e.name));
  const nameToEntry = new Map(entries.map((e) => [e.name, e]));

  const frames: UploadedFrame[] = [];
  for (const name of sortedNames) {
    const entry = nameToEntry.get(name)!;
    const bitmap = await loadImageBitmap(entry.blob);
    frames.push({ name, bitmap });
  }
  return frames;
}
