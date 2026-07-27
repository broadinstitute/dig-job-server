import { describe, it, expect } from "vitest";
import {
  computeVisibleRegion,
  clampRegionZoom,
  clampRegionViewArea,
  panRegionViewAreaFromDrag,
  VKS_REGION_ZOOM_MIN,
  VKS_REGION_ZOOM_MAX,
} from "../../utils/sifter/regionZoom.js";

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

  it("keeps the visible window inside the search region", () => {
    const shifted = computeVisibleRegion(SEARCH, 50, 100);
    expect(shifted.start).toBeGreaterThanOrEqual(SEARCH.start);
    expect(shifted.end).toBeLessThanOrEqual(SEARCH.end);
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
  it("moves the view area opposite to the drag direction", () => {
    const right = panRegionViewAreaFromDrag(0, 100, 1000);
    const left = panRegionViewAreaFromDrag(0, -100, 1000);
    expect(Math.sign(right)).toBe(-Math.sign(left));
  });

  it("does not move on a zero-width plot", () => {
    expect(panRegionViewAreaFromDrag(10, 50, 0)).toBe(10);
  });
});
