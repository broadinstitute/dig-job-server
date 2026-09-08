import { describe, it, expect } from "vitest";
import { createRefreshGuard } from "../../utils/credibleSets/refreshGuard.js";

describe("createRefreshGuard", () => {
  it("returns strictly increasing tokens per id, and isCurrent is true only for the latest token", () => {
    const guard = createRefreshGuard();
    const t1 = guard.begin("row-1");
    const t2 = guard.begin("row-1");
    expect(t2).toBeGreaterThan(t1);
    expect(guard.isCurrent("row-1", t1)).toBe(false);
    expect(guard.isCurrent("row-1", t2)).toBe(true);
  });

  it("makes an earlier token stale once bump is called after begin", () => {
    const guard = createRefreshGuard();
    const token = guard.begin("row-1");
    expect(guard.isCurrent("row-1", token)).toBe(true);
    guard.bump("row-1");
    expect(guard.isCurrent("row-1", token)).toBe(false);
  });

  it("keeps ids independent: bumping one id does not invalidate another id's token", () => {
    const guard = createRefreshGuard();
    const tokenA = guard.begin("row-a");
    const tokenB = guard.begin("row-b");
    guard.bump("row-a");
    expect(guard.isCurrent("row-a", tokenA)).toBe(false);
    expect(guard.isCurrent("row-b", tokenB)).toBe(true);
  });
});
