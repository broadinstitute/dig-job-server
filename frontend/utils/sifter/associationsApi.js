// The ONLY module that knows the associations index name or composes an
// associations query URL. The bioindex layout for uploaded GWAS is migrating
// from one shared `associations` index keyed by GUID-as-phenotype to one index
// per dataset; flipping ASSOCIATIONS_INDEX_LAYOUT is the whole cutover.
//
// Under the per-dataset layout the guid stays in `q` even though it is
// redundant, so the record schema, the pipeline, and the query shape are all
// unchanged and only the index name varies.
export const ASSOCIATIONS_INDEX_LAYOUT = "per-dataset";

export function associationsIndexName(guid, layout = ASSOCIATIONS_INDEX_LAYOUT) {
  return layout === "per-dataset" ? `associations-${guid}` : "associations";
}

// NB: deliberately no `limit` param. Bioindex suppresses the `continuation`
// token whenever a limit is supplied, so sending one truncates the region to a
// single page with no way to detect it.
export function buildAssociationsUrl(baseUrl, guid, region, layout = ASSOCIATIONS_INDEX_LAYOUT) {
  const index = associationsIndexName(guid, layout);
  const q = encodeURIComponent(`${guid},${region}`);
  return `${baseUrl}query/${index}?q=${q}&fmt=row`;
}

export async function fetchAllPages(baseUrl, firstUrl, { fetchImpl = fetch, maxPages = 50 } = {}) {
  const records = [];
  let url = firstUrl;
  let pages = 0;
  while (url) {
    const res = await fetchImpl(url);
    if (!res.ok) throw new Error(`bioindex query failed: ${res.status}`);
    const body = await res.json();
    records.push(...(body.data || []));
    pages += 1;
    url =
      body.continuation && pages < maxPages
        ? `${baseUrl}cont?token=${encodeURIComponent(body.continuation)}`
        : null;
  }
  return records;
}
