import { describe, it, expect, vi } from "vitest";
import { createSifterLoader } from "../../composables/useSifterData.js";
import { resolveLdPopulation } from "../../utils/sifter/ldServer.js";

// Region uses `chr`; association RECORDS use `chromosome`. Both are correct.
const REGION = { chr: "10", start: 1, end: 1000 };
const ROWS = [
  { chromosome: "10", position: 100, reference: "C", alt: "T", pValue: 1e-9, beta: 0.4 },
  { chromosome: "10", position: 200, reference: "A", alt: "G", pValue: 0.02, beta: 0.1 },
];

function deps(over = {}) {
  return {
    fetchAssociations: vi.fn().mockResolvedValue(ROWS),
    fetchGenes: vi.fn().mockResolvedValue([{ name: "TCF7L2" }]),
    // Columnar, matching upstream fetchRecombinationRate
    fetchRecombination: vi.fn().mockResolvedValue({ position: [100], recomb_rate: [0.3] }),
    enrichWithLd: vi.fn().mockImplementation(async (rows) => rows.map((r) => ({ ...r, ldScore: 0.9 }))),
    ...over,
  };
}

describe("createSifterLoader", () => {
  it("loads all four sources and reports ok", async () => {
    const d = deps();
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toHaveLength(2);
    expect(out.genes).toHaveLength(1);
    expect(out.recombination.position).toEqual([100]);
    expect(out.status).toEqual({
      associations: "ok", genes: "ok", recombination: "ok", ld: "ok",
    });
  });

  it("picks the lowest-pValue row as the LD reference", async () => {
    const out = await createSifterLoader(deps()).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.refRow.position).toBe(100);
  });

  it("still renders when LD fails", async () => {
    const d = deps({ enrichWithLd: vi.fn().mockRejectedValue(new Error("ld down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toHaveLength(2);
    expect(out.status.ld).toBe("failed");
    expect(out.status.associations).toBe("ok");
  });

  it("still renders when genes fail", async () => {
    const d = deps({ fetchGenes: vi.fn().mockRejectedValue(new Error("genes down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.genes).toEqual([]);
    expect(out.status.genes).toBe("failed");
    expect(out.rows).toHaveLength(2);
  });

  it("still renders when recombination throws", async () => {
    const d = deps({ fetchRecombination: vi.fn().mockRejectedValue(new Error("down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.recombination).toBeNull();
    expect(out.status.recombination).toBe("failed");
    expect(out.rows).toHaveLength(2);
  });

  // Upstream's fetchRecombinationRate resolves with null rather than throwing
  // when the API returns an error payload — that must count as failed too.
  it("treats a resolved null recombination result as failed", async () => {
    const d = deps({ fetchRecombination: vi.fn().mockResolvedValue(null) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.recombination).toBeNull();
    expect(out.status.recombination).toBe("failed");
  });

  it("rejects when associations fail - the only fatal source", async () => {
    const d = deps({ fetchAssociations: vi.fn().mockRejectedValue(new Error("bioindex down")) });
    await expect(
      createSifterLoader(d).load({ baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR" }),
    ).rejects.toThrow("bioindex down");
  });

  it("defaults a missing ancestry to ALL", async () => {
    const d = deps();
    await createSifterLoader(d).load({ baseUrl: "b/", guid: "g", region: REGION, ancestry: null });
    const session = d.enrichWithLd.mock.calls[0][1];
    // fetchLdScoreMapForRefRow calls resolveLdPopulation(session.ancestry) itself,
    // so the ancestry on the session is what actually drives the LD query.
    expect(session.population).toBe("ALL");
    expect(resolveLdPopulation(session.ancestry)).toBe("ALL");
  });

  it("prefers an explicitly supplied LD reference over the lead variant", async () => {
    const explicit = ROWS[1]; // pValue 0.02, so NOT the lead
    const out = await createSifterLoader(deps()).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR", refRow: explicit,
    });
    expect(out.refRow).toBe(explicit);
  });
});
