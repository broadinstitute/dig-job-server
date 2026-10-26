import { describe, it, expect } from "vitest";
import { hasRunningJob } from "../../utils/datasets/runningJob.js";

const wf = (statuses) =>
  Object.fromEntries(
    Object.entries(statuses).map(([m, status]) => [m, { [m]: { status } }]),
  );

describe("hasRunningJob", () => {
  it("is true when the row's latest status is RUNNING", () => {
    expect(hasRunningJob({ status: "RUNNING variant-sifter" })).toBe(true);
  });

  it("is true when another workflow is RUNNING behind a finished latest status", () => {
    // The sifter's own S-LDSC ended last, so `status` hides the running sifter.
    const data = {
      status: "sldsc SUCCEEDED",
      workflows: wf({ sldsc: "SUCCEEDED", "variant-sifter": "RUNNING" }),
    };
    expect(hasRunningJob(data)).toBe(true);
  });

  it("is false when nothing is running", () => {
    const data = {
      status: "variant-sifter SUCCEEDED",
      workflows: wf({ sldsc: "FAILED", "variant-sifter": "SUCCEEDED" }),
    };
    expect(hasRunningJob(data)).toBe(false);
  });

  it("is false for a row with no status or workflows", () => {
    expect(hasRunningJob({})).toBe(false);
    expect(hasRunningJob({ status: null, workflows: {} })).toBe(false);
  });
});
