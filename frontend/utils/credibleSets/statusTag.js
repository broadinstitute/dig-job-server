// How each server-derived credible-set status renders. The rule that produces
// the status lives server-side (job_server/credible_sets.py::derive_status);
// the page only draws it.
export const STATUS_TAGS = {
  pending: {
    severity: "secondary", label: "Pending", icon: "pi pi-clock",
    tooltip: "Run Variant Sifter on this dataset to index the credible set",
  },
  indexing: {
    severity: "warn", label: "Indexing", icon: "pi pi-spin pi-spinner",
    tooltip: "Indexing in progress",
  },
  indexed: {
    severity: "success", label: "Indexed", icon: "pi pi-check",
    tooltip: "Available in the Variant Sifter",
  },
  failed: {
    severity: "danger", label: "Failed", icon: "pi pi-times",
    tooltip: "Indexing failed — open the log or retry",
  },
};

export function statusTag(status) {
  return STATUS_TAGS[status] ?? STATUS_TAGS.pending;
}

export function hasFailed(credibleSets) {
  return (credibleSets || []).some((c) => c.status === "failed");
}
