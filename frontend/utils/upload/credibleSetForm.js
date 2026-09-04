// Decision logic and payload shaping for CredibleSetForm.vue and its hosts.
// Pure so Vitest covers it without mounting the component.
import { missingCredibleSetFields } from "./credibleSetFields";

/** Everything needed to call POST /api/credible-sets/validate. */
export function canValidate(model) {
  if (!model || !model.file) return false;
  if (!String(model.name || "").trim()) return false;
  // missingCredibleSetFields checks key presence with `in`, so a key mapped to
  // undefined/null (an unmapped column in the selector) would otherwise still
  // count as mapped. Drop those keys before asking what's missing.
  const colMap = Object.fromEntries(
    Object.entries(model.colMap || {}).filter(([, v]) => v != null),
  );
  return missingCredibleSetFields(colMap).length === 0;
}

/** Ready to upload: validatable AND the last validation passed. */
export function isReady(model) {
  return canValidate(model) && !!model.report?.ok;
}

/** The multipart body both the validate and create routes accept. */
export function buildFormData(model, FormDataImpl = FormData) {
  const fd = new FormDataImpl();
  fd.append("file", model.file, model.file.name);
  fd.append("name", String(model.name || "").trim());
  fd.append("col_map", JSON.stringify(model.colMap || {}));
  if (model.separator) fd.append("separator", model.separator);
  return fd;
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function summarizeReport(report) {
  return `Valid · ${plural(report.set_count, "set")} · ${plural(report.row_count, "variant")}`;
}

/** A one-line, user-facing reason from an axios error (409 string detail,
 *  400 validation-report detail, or a network failure). */
export function describeUploadError(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && Array.isArray(detail.errors) && detail.errors.length) {
    const first = detail.errors[0];
    return first.line ? `line ${first.line}: ${first.message}` : first.message;
  }
  return error?.message || "Upload failed";
}
