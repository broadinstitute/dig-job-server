import { resolveGeneOrVariantToRegion } from "~/utils/sifter/searchUtils";

// The KP Variant Sifter this page is ported from is a locus-scale tool: users
// arrive from a gene or variant, and its region-expand tops out at ±150 kb,
// so a very wide region is simply unreachable in its UI. We match that here.
// The cap is sized so no legitimate gene search is ever rejected: the largest
// human genes (CNTNAP2 ~2.3 Mb, DMD ~2.2 Mb) plus the maximum ±150 kb expand
// (adding up to 300 kb total) still fit comfortably under 3 Mb, while
// genuinely wide free-text regions (e.g. `1:1-50000000`) are rejected.
export const MAX_REGION_SPAN_BP = 3_000_000;

// Factory split out from the composable so it is unit-testable without Nuxt.
export function createSifterRegionResolver({ fetchImpl = fetch } = {}) {
  async function resolve(query, expandBp = 0) {
    const q = String(query || "").trim();
    if (!q) {
      throw new Error("Please enter a region or gene name.");
    }
    let region;
    try {
      region = await resolveGeneOrVariantToRegion(q, { expandBp, fetchImpl });
    } catch (e) {
      // resolveGeneOrVariantToRegion already throws friendly, distinct
      // messages for a non-ok response ("Gene lookup failed (HTTP ...)") and
      // an empty result ("No gene or region found ..."); pass those through
      // unchanged. Anything else (a rejected fetch itself — e.g. a network
      // failure) surfaces as a raw `TypeError: Failed to fetch` if left
      // unwrapped, so wrap it consistently with the other lookup failures.
      if (/^(Gene lookup failed|No gene or region found)/.test(e?.message || "")) {
        throw e;
      }
      throw new Error(`Gene lookup failed: ${e?.message || "network error"}`);
    }
    if (region) {
      // Checked AFTER resolution and expand so a gene's bounds plus its
      // expand are measured as one span; a gene symbol has no span until
      // it's looked up, so this can't run any earlier.
      const spanBp = region.end - region.start;
      if (spanBp > MAX_REGION_SPAN_BP) {
        const spanMb = (spanBp / 1_000_000).toFixed(1);
        const capMb = (MAX_REGION_SPAN_BP / 1_000_000).toFixed(1);
        throw new Error(
          `Region spans ${spanMb} Mb; the sifter shows locus-scale views up to ${capMb} Mb. Search a gene or narrow the region.`
        );
      }
    }
    return region;
  }
  return { resolve };
}

export function useSifterRegion() {
  return createSifterRegionResolver();
}
