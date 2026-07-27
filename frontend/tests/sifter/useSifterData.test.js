import { describe, it, expect, vi } from "vitest";
import { createSifterLoader } from "../../composables/useSifterData.js";
import { resolveLdPopulation } from "../../utils/sifter/ldServer.js";

// Region uses `chr`; association RECORDS use `chromosome`. Both are correct.
const REGION = { chr: "10", start: 1, end: 1000 };
// The lead variant (lowest pValue) is deliberately NOT rows[0], so that a
// regression which reads undecorated rows[0] as a fallback lead cannot pass.
const ROWS = [
  { chromosome: "10", position: 100, reference: "C", alt: "T", pValue: 0.02, beta: 0.1 },
  { chromosome: "10", position: 200, reference: "A", alt: "G", pValue: 0.5, beta: 0.2 },
  { chromosome: "10", position: 300, reference: "G", alt: "A", pValue: 1e-9, beta: 0.4 },
];

function deps(over = {}) {
  return {
    fetchAssociations: vi.fn().mockResolvedValue(ROWS),
    fetchGenes: vi.fn().mockResolvedValue([{ name: "TCF7L2" }]),
    // Columnar, matching upstream fetchRecombinationRate
    fetchRecombination: vi.fn().mockResolvedValue({ position: [100], recomb_rate: [0.3] }),
    // Real field name is LDS (see ASSOCIATIONS_TABLE_FORMAT / ldServer.js) —
    // attaching "ldScore" here would silently defeat the status.ld === "ok" check.
    enrichWithLd: vi.fn().mockImplementation(async (rows) => rows.map((r) => ({ ...r, LDS: 0.9 }))),
    ...over,
  };
}

describe("createSifterLoader", () => {
  it("loads all four sources and reports ok", async () => {
    const d = deps();
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toHaveLength(3);
    expect(out.genes).toHaveLength(1);
    expect(out.recombination.position).toEqual([100]);
    expect(out.status).toEqual({
      associations: "ok", genes: "ok", recombination: "ok", ld: "ok",
    });
  });

  it("decorates rows before anything reads them", async () => {
    const out = await createSifterLoader(deps()).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    // rows[0] must carry decorated display-named fields, not just raw ones.
    expect(out.rows[0]["P-Value"]).toBe(0.02);
    expect(out.rows[0]["Variant ID"]).toBe("10:100_C/T");
    // The reference row is the true lead (lowest pValue), which is rows[2],
    // NOT rows[0] — an undecorated fallback would wrongly pick rows[0].
    expect(out.refRow["P-Value"]).toBe(1e-9);
    expect(out.refRow["Variant ID"]).toBe("10:300_G/A");
  });

  it("picks the lowest-pValue row as the LD reference, not rows[0]", async () => {
    const out = await createSifterLoader(deps()).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.refRow.position).toBe(300);
    expect(out.refRow.position).not.toBe(out.rows[0].position);
    expect(out.rows[2].position).toBe(300);
  });

  it("still renders when LD fails", async () => {
    const d = deps({ enrichWithLd: vi.fn().mockRejectedValue(new Error("ld down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toHaveLength(3);
    expect(out.status.ld).toBe("failed");
    expect(out.status.associations).toBe("ok");
  });

  it("marks status.ld failed when enrichment resolves but attaches no scores", async () => {
    // Mirrors the real ldServer behavior: fetchLdScoreMapForRefRow swallows its
    // own errors and enrichAssociationRowsWithLdScoresForRef returns the rows
    // unchanged, so the promise resolves normally with no LDS anywhere.
    const d = deps({ enrichWithLd: vi.fn().mockImplementation(async (rows) => rows) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toHaveLength(3);
    expect(out.rows.some((row) => row.LDS != null)).toBe(false);
    expect(out.status.ld).toBe("failed");
  });

  it("still renders when genes fail", async () => {
    const d = deps({ fetchGenes: vi.fn().mockRejectedValue(new Error("genes down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.genes).toEqual([]);
    expect(out.status.genes).toBe("failed");
    expect(out.rows).toHaveLength(3);
  });

  it("still renders when recombination throws", async () => {
    const d = deps({ fetchRecombination: vi.fn().mockRejectedValue(new Error("down")) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.recombination).toBeNull();
    expect(out.status.recombination).toBe("failed");
    expect(out.rows).toHaveLength(3);
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

  // A region can legitimately have no variants — an empty resolution is NOT
  // the same as a rejection and must not be treated as fatal.
  it("does not reject when associations resolve with an empty array", async () => {
    const d = deps({ fetchAssociations: vi.fn().mockResolvedValue([]) });
    const out = await createSifterLoader(d).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR",
    });
    expect(out.rows).toEqual([]);
    expect(out.status.associations).toBe("ok");
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
    const explicit = ROWS[1]; // pValue 0.5, so NOT the lead
    const out = await createSifterLoader(deps()).load({
      baseUrl: "b/", guid: "g", region: REGION, ancestry: "EUR", refRow: explicit,
    });
    expect(out.refRow).toBe(explicit);
  });
});
