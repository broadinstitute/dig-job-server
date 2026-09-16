// GWAS-Hub membership, resolved from the KPN user service.
//
// Tokens are bound to the group they were minted for at login (gwas-ce);
// verifying one against any other group answers 403 "Token was not issued
// for group". Membership therefore cannot be a second group. Instead the
// standard verify response
//   GET {userServiceUrl}/api/auth/verify/?group={userGroup}
// carries `user.roles` and `user.permissions`, and a hub member is a user
// holding the configured role (config.public.gwasHubRole, e.g.
// "gwas-hub-user", alongside the existing "gwas-ce-user").
//
// This module is deliberately pure: the network call is injected as `verify`
// so the status logic is unit-testable and, crucially, so a failure here can
// never fall into UserStore.isUserLoggedIn()'s catch block, which clears the
// main authToken.

export const HUB_STATUS = Object.freeze({
    UNKNOWN: "unknown", // not checked yet this session
    MEMBER: "member",
    DENIED: "denied", // signed in, but without the hub role
    ERROR: "error", // network / 5xx; retryable, never shown as "denied"
});

export const hubVerifyUrl = (userServiceUrl, group) =>
    `${userServiceUrl}/api/auth/verify/?group=${encodeURIComponent(group)}`;

// True when the verified user carries the hub role, either as a role or as a
// permission (the user service exposes both lists; admins may use either).
export const hasHubRole = (user, role) => {
    if (!user || !role) {
        return false;
    }
    const has = (list) => Array.isArray(list) && list.includes(role);
    return has(user.roles) || has(user.permissions);
};

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
 * @param {string} opts.role       the hub role name; empty disables the hub
 * @param {() => Promise<object>} opts.verify performs the verify request and
 *                                  resolves with the user object (roles,
 *                                  permissions); must reject with an error
 *                                  carrying .status, .response.status or
 *                                  .statusCode on HTTP failure ($fetch does).
 * @returns {Promise<{status: string, user: object|null}>}
 */
export async function resolveHubStatus({ skipAuth, token, role, verify }) {
    if (skipAuth) {
        return { status: HUB_STATUS.MEMBER, user: null };
    }
    if (!token || !role) {
        return { status: HUB_STATUS.DENIED, user: null };
    }
    try {
        const user = await verify();
        return {
            status: hasHubRole(user, role)
                ? HUB_STATUS.MEMBER
                : HUB_STATUS.DENIED,
            user: user ?? null,
        };
    } catch (error) {
        const code = errorStatusCode(error);
        if (code === 401 || code === 403) {
            return { status: HUB_STATUS.DENIED, user: null };
        }
        return { status: HUB_STATUS.ERROR, user: null };
    }
}
