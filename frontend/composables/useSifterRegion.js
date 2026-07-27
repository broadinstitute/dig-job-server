import { resolveGeneOrVariantToRegion } from "~/utils/sifter/searchUtils";

// Factory split out from the composable so it is unit-testable without Nuxt.
export function createSifterRegionResolver({ fetchImpl = fetch } = {}) {
  async function resolve(query, expandBp = 0) {
    const q = String(query || "").trim();
    if (!q) {
      throw new Error("Please enter a region or gene name.");
    }
    return resolveGeneOrVariantToRegion(q, { expandBp, fetchImpl });
  }
  return { resolve };
}

export function useSifterRegion() {
  return createSifterRegionResolver();
}
