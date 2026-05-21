// Reusable presigned-PUT-to-S3 with progress. Returns a single function
// that takes (url, blob, { onProgress }) and PUTs the blob.
//
// Why a composable: the existing GWAS upload (pages/upload/index.vue) does
// this inline with axios; we want the same pattern for FALCON's
// many-files-in-parallel upload without duplicating the option soup.
import axios from "axios";

export function usePresignedS3Upload() {
  /**
   * PUT a blob to a presigned URL. Returns once S3 has 200'd.
   * @param {string} url  presigned PUT URL from the server
   * @param {Blob|File} blob  the bytes to upload
   * @param {{ onProgress?: (pct: number) => void }} [opts]
   */
  async function putToPresigned(url, blob, opts = {}) {
    const { onProgress } = opts;
    await axios.put(url, blob, {
      // NB: do NOT send Authorization here — the presigned URL IS the auth.
      // Sending an Authorization header makes S3 ignore the signature and reject.
      headers: {},
      transformRequest: [(data) => data],  // keep blob unmodified
      onUploadProgress(evt) {
        if (!onProgress || !evt.total) return;
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      },
    });
  }

  return { putToPresigned };
}
