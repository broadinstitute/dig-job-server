// frontend/utils/falcon/pako.js
// Helper for gzipped LD files (.gz). pako is already a dep of this project.
import pako from "pako";

export async function readGzippedText(file) {
  const buf = await file.arrayBuffer();
  const bytes = new Uint8Array(buf);
  return pako.ungzip(bytes, { to: "string" });
}
