import { describe, it, expect, vi } from "vitest";
import {
  VKS_HANDOFF_READY_TYPE,
  VKS_HANDOFF_TOKEN_TYPE,
  HANDOFF_TIMEOUT_MS,
  portalSifterOrigin,
  buildPortalSifterUrl,
  createTokenHandoff,
} from "../../utils/sifter/portalHandoff.js";

const PORTAL = "https://dev.hugeamp.org/research.html?pageid=kp_variant_sifter_26&project=gwas-ce";
const ORIGIN = "https://dev.hugeamp.org";
const PAYLOAD = { token: "3e9b2a5c", dataset: "Vitamin D GWAS Albinana 2023", ancestry: "EUR" };

describe("message type constants", () => {
  // These strings are duplicated by hand in dig-dug-portal's
  // variantSifterTokenHandoff.js; a change here must be mirrored there.
  it("match the portal-side protocol", () => {
    expect(VKS_HANDOFF_READY_TYPE).toBe("vks:ready");
    expect(VKS_HANDOFF_TOKEN_TYPE).toBe("vks:gwas-ce-token");
  });
});

describe("portalSifterOrigin", () => {
  it("strips path and query down to the origin", () => {
    expect(portalSifterOrigin(PORTAL)).toBe(ORIGIN);
  });

  it("keeps a non-default port (local portal preview)", () => {
    expect(portalSifterOrigin("http://localhost:8080/research.html?pageid=x")).toBe("http://localhost:8080");
  });

  it("throws on garbage", () => {
    expect(() => portalSifterOrigin("not a url")).toThrow();
    expect(() => portalSifterOrigin("")).toThrow();
    expect(() => portalSifterOrigin("javascript:alert(1)")).toThrow();
  });
});

describe("buildPortalSifterUrl", () => {
  it("returns the configured page untouched when no region is given", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL));
    expect(url.origin).toBe(ORIGIN);
    expect(url.searchParams.get("pageid")).toBe("kp_variant_sifter_26");
    expect(url.searchParams.get("project")).toBe("gwas-ce");
    expect(url.searchParams.has("region")).toBe(false);
  });

  it("appends region while preserving the existing params", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { region: "4:72500000-72800000" }));
    expect(url.searchParams.get("pageid")).toBe("kp_variant_sifter_26");
    expect(url.searchParams.get("project")).toBe("gwas-ce");
    expect(url.searchParams.get("region")).toBe("4:72500000-72800000");
  });

  it("never carries a token, whatever the caller passes", () => {
    const out = buildPortalSifterUrl(PORTAL, { region: null, token: PAYLOAD.token });
    expect(out).not.toContain(PAYLOAD.token);
    expect(out).not.toContain("token");
  });
});

// A harness with fake window plumbing so the handoff can be driven synchronously.
function harness({ timeoutMs = HANDOFF_TIMEOUT_MS } = {}) {
  const listeners = new Map();
  const timers = new Map();
  let nextTimer = 1;
  const win = { postMessage: vi.fn() };
  const holder = { win: null };

  const addListener = vi.fn((type, fn) => listeners.set(type, fn));
  const removeListener = vi.fn((type, fn) => {
    if (listeners.get(type) === fn) listeners.delete(type);
  });
  const setTimer = vi.fn((fn, ms) => {
    const id = nextTimer++;
    timers.set(id, { fn, ms });
    return id;
  });
  const clearTimer = vi.fn((id) => timers.delete(id));

  const handoff = createTokenHandoff({
    getWin: () => holder.win,
    origin: ORIGIN,
    payload: PAYLOAD,
    timeoutMs,
    addListener,
    removeListener,
    setTimer,
    clearTimer,
  });
  // Mirrors the page: listener registered first, THEN the window is opened.
  holder.win = win;

  const fire = (event) => listeners.get("message")?.(event);
  const ready = (overrides = {}) =>
    fire({ origin: ORIGIN, source: win, data: { type: VKS_HANDOFF_READY_TYPE }, ...overrides });
  const fireTimeout = () => {
    for (const { fn } of timers.values()) fn();
  };

  return { win, holder, handoff, listeners, timers, fire, ready, fireTimeout,
           addListener, removeListener, setTimer, clearTimer };
}

describe("createTokenHandoff", () => {
  it("requires a getWin accessor and an origin", () => {
    expect(() => createTokenHandoff({ origin: ORIGIN, payload: PAYLOAD })).toThrow();
    expect(() => createTokenHandoff({ getWin: () => null, payload: PAYLOAD })).toThrow();
  });

  it("registers the listener before the window exists and arms the timeout", () => {
    const h = harness();
    expect(h.addListener).toHaveBeenCalledWith("message", expect.any(Function));
    expect(h.setTimer).toHaveBeenCalledWith(expect.any(Function), HANDOFF_TIMEOUT_MS);
    expect(h.win.postMessage).not.toHaveBeenCalled();
  });

  it("replies with the token payload to the exact origin on a valid ready", () => {
    const h = harness();
    h.ready();
    expect(h.win.postMessage).toHaveBeenCalledTimes(1);
    expect(h.win.postMessage).toHaveBeenCalledWith(
      { type: VKS_HANDOFF_TOKEN_TYPE, ...PAYLOAD },
      ORIGIN,
    );
  });

  it("ignores ready from another origin", () => {
    const h = harness();
    h.ready({ origin: "https://evil.example" });
    h.ready({ origin: "https://dev.hugeamp.org:8443" });
    expect(h.win.postMessage).not.toHaveBeenCalled();
    expect(h.listeners.has("message")).toBe(true); // still waiting
  });

  it("ignores ready from another window, even at the right origin", () => {
    const h = harness();
    h.ready({ source: { postMessage: vi.fn() } });
    expect(h.win.postMessage).not.toHaveBeenCalled();
    expect(h.listeners.has("message")).toBe(true);
  });

  it("ignores messages of another type or with no data", () => {
    const h = harness();
    h.ready({ data: { type: VKS_HANDOFF_TOKEN_TYPE } });
    h.ready({ data: { type: "something-else" } });
    h.ready({ data: null });
    h.ready({ data: "vks:ready" });
    expect(h.win.postMessage).not.toHaveBeenCalled();
  });

  it("ignores ready before the window has been opened", () => {
    const h = harness();
    const opened = h.win;
    h.holder.win = null;
    h.fire({ origin: ORIGIN, source: opened, data: { type: VKS_HANDOFF_READY_TYPE } });
    expect(opened.postMessage).not.toHaveBeenCalled();
  });

  it("is single-shot: removes the listener and clears the timer after replying", () => {
    const h = harness();
    h.ready();
    expect(h.removeListener).toHaveBeenCalledWith("message", expect.any(Function));
    expect(h.listeners.has("message")).toBe(false);
    expect(h.clearTimer).toHaveBeenCalledTimes(1);
    expect(h.timers.size).toBe(0);
    h.ready(); // a second ready must not post again
    expect(h.win.postMessage).toHaveBeenCalledTimes(1);
  });

  it("on timeout removes the listener and never posts", () => {
    const h = harness({ timeoutMs: 5 });
    expect(h.setTimer).toHaveBeenCalledWith(expect.any(Function), 5);
    h.fireTimeout();
    expect(h.listeners.has("message")).toBe(false);
    expect(h.win.postMessage).not.toHaveBeenCalled();
    h.ready(); // late ready after timeout is ignored
    expect(h.win.postMessage).not.toHaveBeenCalled();
  });

  it("cancel() removes the listener and clears the timer", () => {
    const h = harness();
    h.handoff.cancel();
    expect(h.listeners.has("message")).toBe(false);
    expect(h.timers.size).toBe(0);
    h.ready();
    expect(h.win.postMessage).not.toHaveBeenCalled();
    expect(() => h.handoff.cancel()).not.toThrow(); // idempotent
  });
});
