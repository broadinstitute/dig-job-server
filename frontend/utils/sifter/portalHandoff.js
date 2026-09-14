// Hand the GWAS-CE dataset id (the portal's "access token") to the portal's
// Variant Sifter WITHOUT putting it in a URL. The datasets page opens the portal
// page, waits for the sifter shell to post a `ready` message from that window,
// then replies with the token addressed to the portal origin only. The token
// never touches the address bar, browser history, Referer headers or server logs.
//
// The message shapes here mirror dig-dug-portal's
//   src/components/researchPortal/customComponents/kpVariantSifter/variantSifterTokenHandoff.js
// Keep the two in step by hand: there is no shared package between the repos.
export const VKS_HANDOFF_READY_TYPE = "vks:ready";
export const VKS_HANDOFF_TOKEN_TYPE = "vks:gwas-ce-token";

export const HANDOFF_TIMEOUT_MS = 60000;

/** The origin the portal page is served from; postMessage targets exactly this. */
export function portalSifterOrigin(portalUrl) {
  const url = new URL(String(portalUrl || "")); // throws TypeError on garbage
  if (!/^https?:$/.test(url.protocol)) {
    throw new TypeError(`portal sifter URL must be http(s): ${portalUrl}`);
  }
  return url.origin;
}

/** The page to open. `region` is optional and the datasets page never sends one;
 *  it exists so a caller with a known locus can have the search auto-start. */
export function buildPortalSifterUrl(portalUrl, { region } = {}) {
  const url = new URL(String(portalUrl || ""));
  if (region) {
    url.searchParams.set("region", region);
  }
  return url.toString();
}

/**
 * Register for the portal's `ready` message and answer it with the token.
 *
 * Must be created BEFORE `window.open` so the listener exists when the child
 * posts, which is why the child window arrives via `getWin()` rather than a
 * value. Accepts only a `ready` whose origin is exactly `origin` and whose
 * source is exactly the opened window; anything else is ignored. Single-shot:
 * cleans up after replying, on timeout, or on cancel(). A timeout is silent --
 * the portal then behaves as if opened directly (empty token field).
 */
export function createTokenHandoff({
  getWin,
  origin,
  payload,
  timeoutMs = HANDOFF_TIMEOUT_MS,
  addListener = (type, fn) => window.addEventListener(type, fn),
  removeListener = (type, fn) => window.removeEventListener(type, fn),
  setTimer = (fn, ms) => setTimeout(fn, ms),
  clearTimer = (id) => clearTimeout(id),
}) {
  if (typeof getWin !== "function") throw new TypeError("getWin accessor is required");
  if (!origin) throw new TypeError("origin is required");

  let done = false;
  let timer = null;

  function cleanup() {
    if (done) return;
    done = true;
    removeListener("message", onMessage);
    if (timer !== null) {
      clearTimer(timer);
      timer = null;
    }
  }

  function onMessage(event) {
    if (done) return;
    const win = getWin();
    if (!win || event.origin !== origin || event.source !== win) return;
    if (!event.data || event.data.type !== VKS_HANDOFF_READY_TYPE) return;
    win.postMessage({ type: VKS_HANDOFF_TOKEN_TYPE, ...payload }, origin);
    cleanup();
  }

  addListener("message", onMessage);
  timer = setTimer(cleanup, timeoutMs);

  return { cancel: cleanup };
}
