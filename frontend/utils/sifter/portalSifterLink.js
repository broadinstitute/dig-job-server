// Build the portal Variant Sifter URL for a GWAS-CE dataset. The dataset id is
// the portal's "access token" and travels as a plain `token` query parameter:
// the link survives a reload of the portal tab and can be shared. The portal
// side (dig-dug-portal kpVariantSifter.vue, applyUrlSearchParams) reads it.
//
// `ancestry` is optional; when given it is the portal's fallback ancestry for
// this dataset if token metadata has none. `region` is optional and the
// datasets page never sends one; it exists so a caller with a known locus can
// have the search auto-start.
export function buildPortalSifterUrl(portalUrl, { token, region, ancestry } = {}) {
  const id = String(token || "").trim();
  if (!id) throw new TypeError("token is required");
  const url = new URL(String(portalUrl || "")); // throws TypeError on garbage
  url.searchParams.set("token", id);
  if (typeof ancestry === "string" && ancestry) url.searchParams.set("ancestry", ancestry);
  if (region) url.searchParams.set("region", region);
  return url.toString();
}
