// Pure helpers for querying the gwas-ce bioindex. No Nuxt/DOM deps so they
// unit-test directly. The composable useBioindex() wires these to runtimeConfig.

// NB: deliberately no `limit` param. Bioindex suppresses the `continuation`
// token whenever a limit is supplied, so sending one truncates the region to a
// single page with no way to detect it -- the plot silently loses everything
// past the cut. Omitting it lets bioindex page naturally; fetchAllPages walks
// the continuations and maxPages is the only bound.
export function buildAssociationsUrl(baseUrl, guid, region) {
  const q = encodeURIComponent(`${guid},${region}`);
  return `${baseUrl}query/associations?q=${q}&fmt=row`;
}

// Follow bioindex `continuation` tokens until exhausted (or maxPages), returning
// the concatenated `data` records. `fetchImpl` is injectable for testing.
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
