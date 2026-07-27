import { describe, it, expect } from "vitest";
import { createFakeCtx } from "../helpers/fakeCanvasContext.js";
import {
  getLdDotColor,
  renderPlotDot,
  normalizePlotMargin,
  VKS_LD_DOT_COLORS,
  VKS_DEFAULT_DOT_RADIUS,
} from "../../utils/sifter/plotShared.js";

describe("getLdDotColor", () => {
  it("bins r2 into six colours by floor(r2 * 5)", () => {
    expect(getLdDotColor(0)).toBe(VKS_LD_DOT_COLORS[0]);
    expect(getLdDotColor(0.25)).toBe(VKS_LD_DOT_COLORS[1]);
    expect(getLdDotColor(0.45)).toBe(VKS_LD_DOT_COLORS[2]);
    expect(getLdDotColor(0.65)).toBe(VKS_LD_DOT_COLORS[3]);
    expect(getLdDotColor(0.85)).toBe(VKS_LD_DOT_COLORS[4]);
    expect(getLdDotColor(1)).toBe(VKS_LD_DOT_COLORS[5]);
  });

  it("returns the transparent 'no data' colour for null or NaN", () => {
    expect(getLdDotColor(null)).toBe("#00000030");
    expect(getLdDotColor(undefined)).toBe("#00000030");
    expect(getLdDotColor(Number.NaN)).toBe("#00000030");
  });

  it("returns the 'no data' colour for out-of-range r2", () => {
    expect(getLdDotColor(1.5)).toBe("#00000030");
  });

  it("bins exactly at r2 = 0.2/0.4/0.6/0.8 into the bin the edge value enters, per floor(r2 * 5)", () => {
    // Binning is the entire colour contract; the bin edges are the values
    // most likely to be off-by-one, so pin them down exactly rather than
    // relying on the mid-bin cases above. floor(r2 * 5) puts each edge value
    // into the bin it *starts*, not the one below it.
    expect(getLdDotColor(0.2)).toBe(VKS_LD_DOT_COLORS[1]);
    expect(getLdDotColor(0.4)).toBe(VKS_LD_DOT_COLORS[2]);
    expect(getLdDotColor(0.6)).toBe(VKS_LD_DOT_COLORS[3]);
    expect(getLdDotColor(0.8)).toBe(VKS_LD_DOT_COLORS[4]);
  });
});

describe("normalizePlotMargin", () => {
  // Upstream's normalizePlotMargin (verbatim) is a 3-way branch, not a
  // "fill in missing sides" helper: falsy input gets full defaults; an
  // object that already has `.left` is returned as-is (sides are NOT
  // defaulted individually); anything else is assumed to be the legacy
  // `leftMargin`/`rightMargin`/... shape and gets remapped.
  it("returns full defaults for falsy input", () => {
    expect(normalizePlotMargin(null)).toEqual({
      left: 150,
      right: 40,
      top: 20,
      bottom: 100,
      bump: 11,
    });
  });

  it("passes through an object that already has `.left` unchanged", () => {
    const input = { left: 42 };
    const m = normalizePlotMargin(input);
    expect(m).toBe(input);
    expect(m.left).toBe(42);
    expect(m.top).toBeUndefined();
  });

  it("remaps the legacy *Margin keys when `.left` is absent", () => {
    const m = normalizePlotMargin({
      leftMargin: 1,
      rightMargin: 2,
      topMargin: 3,
      bottomMargin: 4,
      bump: 5,
    });
    expect(m).toEqual({ left: 1, right: 2, top: 3, bottom: 4, bump: 5 });
  });
});

describe("renderPlotDot", () => {
  it("draws at the default radius when none is given", () => {
    const ctx = createFakeCtx();
    renderPlotDot(ctx, 5, 6, "#123456");
    const arc = ctx.calls.find((c) => c.fn === "arc");
    expect(arc.args.slice(0, 3)).toEqual([5, 6, VKS_DEFAULT_DOT_RADIUS]);
    expect(ctx.fillStyle).toBe("#123456");
  });
});
