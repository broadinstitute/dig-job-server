import { buildAssociationsUrl, fetchAllPages } from "~/utils/bioindex";

// Query the gwas-ce bioindex for one dataset's associations in a region.
// Direct browser -> bioindex (approach B); no auth header (obfuscation-only).
export function useBioindex() {
  const config = useRuntimeConfig();
  const baseUrl = config.public.bioindexUrl;

  async function queryAssociations({ guid, region }) {
    if (!baseUrl) throw new Error("NUXT_PUBLIC_BIOINDEX_URL is not configured");
    const firstUrl = buildAssociationsUrl(baseUrl, guid, region);
    return fetchAllPages(baseUrl, firstUrl);
  }

  return { queryAssociations };
}
