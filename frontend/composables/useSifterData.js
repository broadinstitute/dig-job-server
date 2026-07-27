import { buildAssociationsUrl, fetchAllPages } from "~/utils/sifter/associationsApi";
import { fetchGenesTrackData } from "~/utils/sifter/genes";
// Upstream's own recombination fetcher, ported in Task 3. Returns columnar
// { position: [], recomb_rate: [] } or null — NOT an array of points.
import { fetchRecombinationRate } from "~/utils/sifter/plotShared";
import {
  pickLeadVariantRow,
  resolveLdPopulation,
  enrichAssociationRowsWithLdScoresForRef,
} from "~/utils/sifter/ldServer";
import { formatRegion } from "~/utils/sifter/searchUtils";
// Ported upstream functions read display-named fields ("P-Value", "Variant ID",
// "-log10(P-Value)"). Raw bioindex rows must be decorated before they touch any
// of them, or the lead-variant pick and LD lookup fail silently.
import { decorateAssociationRows } from "~/utils/sifter/decorateRows";

// Dependencies are injected so the failure-isolation rules are testable
// without touching the network.
export function createSifterLoader(deps = {}) {
  const {
    fetchAssociations = (baseUrl, guid, region) =>
      fetchAllPages(baseUrl, buildAssociationsUrl(baseUrl, guid, formatRegion(region))),
    fetchGenes = (region) => fetchGenesTrackData(region),
    fetchRecombination = (region) => fetchRecombinationRate(region),
    enrichWithLd = (rows, session, refRow, region) =>
      enrichAssociationRowsWithLdScoresForRef(rows, session, refRow, region),
  } = deps;

  // `explicitRef` overrides the lead-variant pick so the UI can reassign the
  // LD reference from the variant dot menu.
  async function load({ baseUrl, guid, region, ancestry, refRow: explicitRef = null }) {
    const status = {
      associations: "ok", genes: "ok", recombination: "ok", ld: "ok",
    };

    // Associations are fatal; the other two are not, so settle them together
    // and downgrade individually.
    const [assocResult, genesResult, recombResult] = await Promise.allSettled([
      fetchAssociations(baseUrl, guid, region),
      fetchGenes(region),
      fetchRecombination(region),
    ]);

    if (assocResult.status === "rejected") throw assocResult.reason;
    // Decorate immediately: everything downstream expects upstream's field names.
    let rows = decorateAssociationRows(assocResult.value);

    let genes = [];
    if (genesResult.status === "fulfilled") genes = genesResult.value;
    else status.genes = "failed";

    // Upstream returns null on failure or on an error payload, so a fulfilled
    // promise carrying null still counts as a failed source.
    let recombination = null;
    if (recombResult.status === "fulfilled" && recombResult.value) {
      recombination = recombResult.value;
    } else {
      status.recombination = "failed";
    }

    const refRow = explicitRef || pickLeadVariantRow(rows);
    const session = { population: resolveLdPopulation(ancestry), ancestry, region };

    if (refRow) {
      try {
        rows = await enrichWithLd(rows, session, refRow, region);
      } catch {
        status.ld = "failed";
      }
    } else {
      status.ld = "failed";
    }

    return { rows, genes, recombination, refRow, status };
  }

  return { load };
}

export function useSifterData() {
  return createSifterLoader();
}
