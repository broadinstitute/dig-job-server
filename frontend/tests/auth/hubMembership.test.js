import { describe, it, expect, vi } from "vitest";
import {
    HUB_STATUS,
    hubVerifyUrl,
    hasHubRole,
    shouldRecheckHub,
    isHubCacheFresh,
    resolveHubStatus,
} from "../../utils/auth/hubMembership.js";

const ROLE = "gwas-hub-user";

// Shape of `user` in the KPN user-service verify response (observed live):
// roles and permissions are both string arrays.
const memberUser = {
    username: "member",
    roles: ["gwas-ce-user", ROLE],
    permissions: ["run-analysis"],
};
const plainUser = {
    username: "plain",
    roles: ["gwas-ce-user"],
    permissions: ["run-analysis"],
};

const resolving = (user) => vi.fn().mockResolvedValue(user);
const failWith = (error) => vi.fn().mockRejectedValue(error);

const base = { skipAuth: false, token: "jwt-abc", role: ROLE };

describe("hubVerifyUrl", () => {
    it("targets the verify endpoint with the given group", () => {
        expect(hubVerifyUrl("https://users.example.org", "gwas-ce")).toBe(
            "https://users.example.org/api/auth/verify/?group=gwas-ce",
        );
    });

    it("encodes the group", () => {
        expect(hubVerifyUrl("https://u", "a b&c")).toBe(
            "https://u/api/auth/verify/?group=a%20b%26c",
        );
    });
});

describe("hasHubRole", () => {
    it("matches the role in roles", () => {
        expect(hasHubRole(memberUser, ROLE)).toBe(true);
    });

    it("matches the role in permissions too", () => {
        expect(
            hasHubRole({ roles: [], permissions: [ROLE] }, ROLE),
        ).toBe(true);
    });

    it("is false without the role", () => {
        expect(hasHubRole(plainUser, ROLE)).toBe(false);
    });

    it("is false for a missing user, missing lists, or empty role", () => {
        expect(hasHubRole(null, ROLE)).toBe(false);
        expect(hasHubRole({ username: "x" }, ROLE)).toBe(false);
        expect(hasHubRole(memberUser, "")).toBe(false);
    });

    // The login response's user object has no roles at all; only the verify
    // response does. Never treat that as membership.
    it("is false for a login-shaped user without role lists", () => {
        expect(hasHubRole({ id: 6, username: "member" }, ROLE)).toBe(false);
    });
});

describe("shouldRecheckHub", () => {
    it("rechecks unknown and error, caches member and denied", () => {
        expect(shouldRecheckHub(HUB_STATUS.UNKNOWN)).toBe(true);
        expect(shouldRecheckHub(HUB_STATUS.ERROR)).toBe(true);
        expect(shouldRecheckHub(HUB_STATUS.MEMBER)).toBe(false);
        expect(shouldRecheckHub(HUB_STATUS.DENIED)).toBe(false);
    });

    it("always rechecks when forced", () => {
        expect(shouldRecheckHub(HUB_STATUS.MEMBER, true)).toBe(true);
        expect(shouldRecheckHub(HUB_STATUS.DENIED, true)).toBe(true);
    });
});

describe("isHubCacheFresh", () => {
    const cached = (status, verifiedToken = "jwt-A") => ({
        status,
        verifiedToken,
    });

    it("reuses a stable answer for the same token", () => {
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.MEMBER), token: "jwt-A" })).toBe(true);
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.DENIED), token: "jwt-A" })).toBe(true);
    });

    // Account switched in another tab: member A's decision must not be
    // reused for nonmember B's token, and vice versa.
    it("does not reuse an answer resolved for a different token", () => {
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.MEMBER), token: "jwt-B" })).toBe(false);
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.DENIED), token: "jwt-B" })).toBe(false);
    });

    it("does not reuse an answer once the token is gone", () => {
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.MEMBER), token: null })).toBe(false);
    });

    it("never reuses unknown or error, even for the same token", () => {
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.UNKNOWN), token: "jwt-A" })).toBe(false);
        expect(isHubCacheFresh({ ...cached(HUB_STATUS.ERROR), token: "jwt-A" })).toBe(false);
    });

    it("never reuses when forced", () => {
        expect(
            isHubCacheFresh({ ...cached(HUB_STATUS.MEMBER), token: "jwt-A", force: true }),
        ).toBe(false);
    });
});

describe("resolveHubStatus", () => {
    it("treats the skipAuth dev bypass as a member without calling verify", async () => {
        const verify = resolving(plainUser);
        const { status } = await resolveHubStatus({
            ...base,
            skipAuth: true,
            token: null,
            verify,
        });
        expect(status).toBe(HUB_STATUS.MEMBER);
        expect(verify).not.toHaveBeenCalled();
    });

    it("denies when there is no session token", async () => {
        const verify = resolving(memberUser);
        const { status } = await resolveHubStatus({ ...base, token: null, verify });
        expect(status).toBe(HUB_STATUS.DENIED);
        expect(verify).not.toHaveBeenCalled();
    });

    // An unconfigured role must fail closed rather than match everyone.
    it("denies when the hub role is not configured", async () => {
        const verify = resolving(memberUser);
        const { status } = await resolveHubStatus({ ...base, role: "", verify });
        expect(status).toBe(HUB_STATUS.DENIED);
        expect(verify).not.toHaveBeenCalled();
    });

    it("is a member when the verified user holds the role", async () => {
        const verify = resolving(memberUser);
        const result = await resolveHubStatus({ ...base, verify });
        expect(result.status).toBe(HUB_STATUS.MEMBER);
        expect(result.user).toBe(memberUser);
        expect(verify).toHaveBeenCalledTimes(1);
    });

    it("is denied when the verified user lacks the role", async () => {
        const result = await resolveHubStatus({
            ...base,
            verify: resolving(plainUser),
        });
        expect(result.status).toBe(HUB_STATUS.DENIED);
        expect(result.user).toBe(plainUser);
    });

    it("is denied when verify resolves with no user", async () => {
        const { status } = await resolveHubStatus({
            ...base,
            verify: resolving(undefined),
        });
        expect(status).toBe(HUB_STATUS.DENIED);
    });

    it("is denied on 401 or 403, whichever shape the error takes", async () => {
        for (const error of [
            { status: 401 },
            { status: 403 },
            { response: { status: 403 } },
            { statusCode: 401 },
        ]) {
            const { status } = await resolveHubStatus({
                ...base,
                verify: failWith(error),
            });
            expect(status).toBe(HUB_STATUS.DENIED);
        }
    });

    // Outages must not be presented as "you are not a member".
    it("is error (retryable) on 5xx or network failure", async () => {
        expect(
            (await resolveHubStatus({ ...base, verify: failWith({ status: 500 }) }))
                .status,
        ).toBe(HUB_STATUS.ERROR);
        expect(
            (
                await resolveHubStatus({
                    ...base,
                    verify: failWith(new Error("network")),
                })
            ).status,
        ).toBe(HUB_STATUS.ERROR);
    });
});
