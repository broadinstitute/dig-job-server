// Whether a dataset row has a job still running, so the page should follow its
// job-status stream. `data.status` is only the most recently updated workflow
// row: a sifter run still RUNNING reads "sldsc SUCCEEDED" there once the S-LDSC
// it started has ended, so every workflow in `data.workflows` is checked too.
export function hasRunningJob(data) {
  if (data?.status?.includes("RUNNING")) return true;
  return Object.values(data?.workflows ?? {}).some((inner) =>
    Object.values(inner ?? {}).some((w) => w?.status === "RUNNING"),
  );
}
