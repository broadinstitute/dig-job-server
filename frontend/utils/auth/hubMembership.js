// GWAS-Hub membership, resolved against the KPN user service.
//
// The app already verifies the session token with
//   GET {userServiceUrl}/api/auth/verify/?group={userGroup}
// in UserStore.isUserLoggedIn(). GWAS-Hub is a shared workspace gated by a
// SECOND group (config.public.gwasHubGroup). Membership is answered by the same
// endpoint with that group instead.
//
// This module is deliberately pure: the network call is injected as `verify`
// so the status logic is unit-testable and, crucially, so a 401 from the hub
// check can never fall into UserStore.isUserLoggedIn()'s catch block, which
// clears the main authToken.

export const HUB_STATUS = Object.freeze({
    UNKNOWN: "unknown", // not checked yet this session
    MEMBER: "member",
    DENIED: "denied", // logged in, but not in the hub group (401/403)
    ERROR: "error", // network / 5xx; retryable, never shown as "denied"
});

export const hubVerifyUrl = (userServiceUrl, group) =>
    `${userServiceUrl}/api/auth/verify/?group=${encodeURIComponent(group)}`;

// MEMBER and DENIED are stable answers for the session; UNKNOWN and ERROR
// should be (re)checked.
export const shouldRecheckHub = (status, force = false) =>
    force || status === HUB_STATUS.UNKNOWN || status === HUB_STATUS.ERROR;

// A cached answer is only valid for the token it was resolved with. The token
// lives in localStorage, which is shared across tabs: signing out and back in
// as another account in a second tab swaps the token under this tab without
// touching its in-memory store. Comparing tokens makes that swap force a new
// verification instead of reusing the previous account's decision.
export const isHubCacheFresh = ({
    status,
    verifiedToken,
    token,
    force = false,
}) => !shouldRecheckHub(status, force) && verifiedToken === token;

const errorStatusCode = (error) =>
    error?.status ?? error?.response?.status ?? error?.statusCode;

/**
 * @param {object} opts
 * @param {boolean} opts.skipAuth  dev bypass (NUXT_PUBLIC_SKIP_AUTH)
 * @param {string|null} opts.token the session JWT, if any
 * @param {string} opts.group      the hub group name; empty disables the hub
 * @param {() => Promise<any>} opts.verify performs the verify request; must
 *                                  reject with an error carrying .status,
 *                                  .response.status or .statusCode on HTTP
 *                                  failure ($fetch does).
 * @returns {Promise<string>} one of HUB_STATUS
 */
export async function resolveHubStatus({ skipAuth, token, group, verify }) {
    if (skipAuth) {
        return HUB_STATUS.MEMBER;
    }
    if (!token || !group) {
        return HUB_STATUS.DENIED;
    }
    try {
        await verify();
        return HUB_STATUS.MEMBER;
    } catch (error) {
        const code = errorStatusCode(error);
        if (code === 401 || code === 403) {
            return HUB_STATUS.DENIED;
        }
        return HUB_STATUS.ERROR;
    }
}
