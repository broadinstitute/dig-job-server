// Per-row sequence tokens so a background refresh (fired when an ingesting
// job finishes) never overwrites a newer local mutation (attach/delete) with
// a stale server snapshot. Pure so it is unit-testable without the page.
export function createRefreshGuard() {
  const seq = new Map();
  return {
    /** Start a refresh for `id`; returns the token to check before applying. */
    begin(id) {
      const next = (seq.get(id) || 0) + 1;
      seq.set(id, next);
      return next;
    },
    /** True when no newer refresh or mutation has happened since `token`. */
    isCurrent(id, token) {
      return seq.get(id) === token;
    },
    /** Record a local mutation so any in-flight refresh for `id` is discarded. */
    bump(id) {
      seq.set(id, (seq.get(id) || 0) + 1);
    },
  };
}
