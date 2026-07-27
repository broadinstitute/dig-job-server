import { describe, it, expect } from "vitest";
import {
  computeVisibleRegion,
  clampRegionZoom,
  clampRegionViewArea,
  panRegionViewAreaFromDrag,
  VKS_REGION_ZOOM_MIN,
  VKS_REGION_ZOOM_MAX,
} from "../../utils/sifter/regionZoom.js";
import {
  computeRegionWidth,
  computeVisibleWindowWidth,
} from "../../utils/sifter/regionPan.js";

const SEARCH = { chr: "10", start: 114700000, end: 114800000 };

describe("computeVisibleRegion", () => {
  it("returns the full search region at zoom 0", () => {
    expect(computeVisibleRegion(SEARCH, 0, 0)).toEqual(SEARCH);
  });

  it("narrows the window as zoom increases", () => {
    const zoomed = computeVisibleRegion(SEARCH, 50, 0);
    const fullWidth = SEARCH.end - SEARCH.start;
    expect(zoomed.end - zoomed.start).toBeLessThan(fullWidth);
    // Region objects use `chr`, not `chromosome` (see task context /
    // searchUtils.js); computeVisibleRegion returns { chr, start, end }.
    expect(zoomed.chr).toBe("10");
  });

  it("pins the exact zoom arithmetic at a centered view area", () => {
    expect(computeVisibleRegion(SEARCH, 50, 0)).toEqual({
      chr: "10",
      start: 114725000,
      end: 114775000,
    });
  });

  it("pins the exact window for a positive regionViewArea (pan shift applied)", () => {
    expect(computeVisibleRegion(SEARCH, 50, 100)).toEqual({
      chr: "10",
      start: 114750000,
      end: 114800000,
    });
  });

  it("pins the exact window for a negative regionViewArea (pan shift applied)", () => {
    expect(computeVisibleRegion(SEARCH, 50, -100)).toEqual({
      chr: "10",
      start: 114700000,
      end: 114750000,
    });
  });

  it("produces different windows for positive vs negative view areas", () => {
    const positive = computeVisibleRegion(SEARCH, 50, 100);
    const negative = computeVisibleRegion(SEARCH, 50, -100);
    expect(positive).not.toEqual(negative);
  });
});

describe("clamping", () => {
  it("clamps zoom to its range", () => {
    expect(clampRegionZoom(-10)).toBe(VKS_REGION_ZOOM_MIN);
    expect(clampRegionZoom(1e6)).toBe(VKS_REGION_ZOOM_MAX);
  });

  it("clamps view area to -100..100", () => {
    expect(clampRegionViewArea(-500)).toBe(-100);
    expect(clampRegionViewArea(500)).toBe(100);
  });
});

describe("panRegionViewAreaFromDrag", () => {
  it("pins the exact scaled shift for a rightward drag", () => {
    expect(panRegionViewAreaFromDrag(0, 100, 1000)).toBe(-20);
  });

  it("pins the exact scaled shift for a leftward drag", () => {
    expect(panRegionViewAreaFromDrag(0, -100, 1000)).toBe(20);
  });

  it("does not move on a zero-width plot", () => {
    expect(panRegionViewAreaFromDrag(10, 50, 0)).toBe(10);
  });

  it("does not move on a non-finite delta", () => {
    expect(panRegionViewAreaFromDrag(10, NaN, 1000)).toBe(10);
  });
});

describe("computeRegionWidth", () => {
  it("returns 0 for a null region", () => {
    expect(computeRegionWidth(null)).toBe(0);
  });

  it("returns 0 for a non-positive distance", () => {
    expect(computeRegionWidth({ start: 100, end: 100 })).toBe(0);
    expect(computeRegionWidth({ start: 100, end: 50 })).toBe(0);
  });

  it("returns end - start for a valid region", () => {
    expect(computeRegionWidth(SEARCH)).toBe(100000);
  });
});

describe("computeVisibleWindowWidth", () => {
  it("returns 0 for a null region", () => {
    expect(computeVisibleWindowWidth(null, 50)).toBe(0);
  });

  it("returns 0 for a non-positive distance region", () => {
    expect(computeVisibleWindowWidth({ start: 100, end: 100 }, 50)).toBe(0);
  });

  it("returns the full distance at zoom <= 0", () => {
    expect(computeVisibleWindowWidth(SEARCH, 0)).toBe(100000);
  });

  it("pins the exact zoomed width", () => {
    expect(computeVisibleWindowWidth(SEARCH, 50)).toBe(50000);
  });
});
