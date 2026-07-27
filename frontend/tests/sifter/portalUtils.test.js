import { describe, it, expect } from "vitest";
import { createFakeCtx } from "../helpers/fakeCanvasContext.js";
import { renderDot, renderStar, renderDashedLine } from "../../utils/sifter/_portal/plotUtils.js";
import { parseVariant, gaitVariant } from "../../utils/sifter/_portal/variantUtils.js";

describe("fake canvas context", () => {
  it("records every drawing call in order", () => {
    const ctx = createFakeCtx();
    ctx.beginPath();
    ctx.arc(1, 2, 3, 0, 6);
    ctx.fill();
    expect(ctx.calls.map((c) => c.fn)).toEqual(["beginPath", "arc", "fill"]);
    expect(ctx.calls[1].args).toEqual([1, 2, 3, 0, 6]);
  });
});

describe("renderDot", () => {
  it("draws an arc at the given point with the given colour", () => {
    const ctx = createFakeCtx();
    renderDot(ctx, 10, 20, "#ff0000", 9);
    expect(ctx.fillStyle).toBe("#ff0000");
    const arc = ctx.calls.find((c) => c.fn === "arc");
    expect(arc.args.slice(0, 3)).toEqual([10, 20, 9]);
    expect(ctx.calls.some((c) => c.fn === "fill")).toBe(true);
  });

  it("defaults the radius to 8 when width is falsy", () => {
    const ctx = createFakeCtx();
    renderDot(ctx, 0, 0, "#000");
    expect(ctx.calls.find((c) => c.fn === "arc").args[2]).toBe(8);
  });
});

describe("renderDashedLine", () => {
  it("sets a dash pattern, strokes, then resets the dash", () => {
    const ctx = createFakeCtx();
    renderDashedLine(ctx, 0, 0, 10, 10);
    const dashCalls = ctx.calls.filter((c) => c.fn === "setLineDash");
    expect(dashCalls[0].args[0]).toEqual([20, 10]);
    expect(dashCalls[1].args[0]).toEqual([]);
    expect(ctx.strokeStyle).toBe("#FFAA00");
  });
});

describe("renderStar", () => {
  it("closes a path and both strokes and fills", () => {
    const ctx = createFakeCtx();
    renderStar(ctx, 50, 50, 5, 10, 6, "#111", "#222");
    const fns = ctx.calls.map((c) => c.fn);
    expect(fns).toContain("closePath");
    expect(fns).toContain("stroke");
    expect(fns).toContain("fill");
    expect(ctx.fillStyle).toBe("#222");
  });
});

describe("variant id conversion", () => {
  it("converts a bioindex varId to the GEM form the LD server wants", () => {
    expect(gaitVariant("10:114758349:C:T")).toBe("10:114758349_C/T");
  });

  it("normalises a varId and upper-cases alleles", () => {
    expect(parseVariant("10:114758349:c:t")).toBe("10:114758349:C:T");
  });

  it("passes an rsID through untouched", () => {
    expect(parseVariant("rs7903146")).toBe("rs7903146");
  });
});
