// Pull an access token out of an OAuth callback's query string and persist it.
//
// WHY THIS EXISTS, and why it is not in a page component:
//
// The user service's /gh-callback/ hands the browser back to whatever
// NUXT_PUBLIC_FINAL_REDIRECT_URI names -- for this app, the bare site root
// (https://gwas-ce.kpndataregistry.org). It arrives as
// `/?success=true&access_token=<jwt>`.
//
// The root is in auth.global.js's publicRoutes list, so the middleware used to
// return before reading anything, and the only code that captured the token
// lived in pages/datasets/index.vue's onMounted. That page is guarded, so an
// arriving user had no stored token yet, the middleware bounced them to
// /login, and the capture never ran. Net effect: GitHub sign-in appeared to
// do nothing. It was masked by UserStore.tryDefaultLogin(), which quietly
// signs visitors in as the default user, so the app still looked usable.
//
// Capturing in middleware -- ahead of the publicRoutes early-return -- makes
// this independent of which route the callback lands on, so changing
// NUXT_PUBLIC_FINAL_REDIRECT_URI cannot silently break sign-in again.
//
// `query` is a Nuxt route query; `storage` is window.localStorage (injected so
// this stays unit-testable under vitest's "node" environment).
// Returns true only when a token was actually stored.
export function captureOAuthCallback(query, storage) {
  if (!storage || !query) return false;

  // A repeated query param (?success=true&success=true) arrives as an array,
  // so compare strictly rather than coercing.
  if (query.success !== "true") return false;

  const token = query.access_token;
  // Same reasoning, and it matters more here: a repeated ?access_token= would
  // coerce to "jwt-a,jwt-b" -- a token that is wrong rather than missing, which
  // fails later and further from the cause.
  if (typeof token !== "string" || token === "") return false;

  storage.setItem("authToken", token);
  // The user authenticated explicitly, so any anonymous/default-user session is
  // over. UserStore keys tryDefaultLogin() off both flags; stores/UserStore.js
  // clears both after a credential login, so do the same here.
  storage.removeItem("isDefaultUser");
  storage.removeItem("hasSignedOut");
  return true;
}

// Query keys the user service appends to the callback redirect.
const OAUTH_QUERY_KEYS = ["success", "access_token", "created", "error"];

// Drop the OAuth params from a route query, preserving anything else the app
// put there. Used to clean the address bar after a capture so the JWT does not
// sit in browser history or leak through a Referer header.
export function stripOAuthParams(query) {
  const rest = { ...(query || {}) };
  for (const key of OAUTH_QUERY_KEYS) {
    delete rest[key];
  }
  return rest;
}
