import { describe, it, expect, vi } from "vitest";
import {
    HUB_STATUS,
    hubVerifyUrl,
    shouldRecheckHub,
    isHubCacheFresh,
    resolveHubStatus,
} from "../../utils/auth/hubMembership.js";

const ok = () => vi.fn().mockResolvedValue({ user: { username: "u" } });
const failWith = (error) => vi.fn().mockRejectedValue(error);

const base = { skipAuth: false, token: "jwt-abc", group: "gwas-hub" };

describe("hubVerifyUrl", () => {
    it("targets the verify endpoint with the hub group", () => {
        expect(hubVerifyUrl("https://users.example.org", "gwas-hub")).toBe(
            "https://users.example.org/api/auth/verify/?group=gwas-hub",
        );
    });

    it("encodes the group", () => {
        expect(hubVerifyUrl("https://u", "a b&c")).toBe(
            "https://u/api/auth/verify/?group=a%20b%26c",
        );
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
        const verify = ok();
        const status = await resolveHubStatus({
            ...base,
            skipAuth: true,
            token: null,
            verify,
        });
        expect(status).toBe(HUB_STATUS.MEMBER);
        expect(verify).not.toHaveBeenCalled();
    });

    it("denies when there is no session token", async () => {
        const verify = ok();
        expect(
            await resolveHubStatus({ ...base, token: null, verify }),
        ).toBe(HUB_STATUS.DENIED);
        expect(verify).not.toHaveBeenCalled();
    });

    // An unconfigured hub group must never be sent as ?group= (the user
    // service would reject or, worse, match nothing and answer 200).
    it("denies when the hub group is not configured", async () => {
        const verify = ok();
        expect(await resolveHubStatus({ ...base, group: "", verify })).toBe(
            HUB_STATUS.DENIED,
        );
        expect(verify).not.toHaveBeenCalled();
    });

    it("is a member when verify succeeds", async () => {
        const verify = ok();
        expect(await resolveHubStatus({ ...base, verify })).toBe(
            HUB_STATUS.MEMBER,
        );
        expect(verify).toHaveBeenCalledTimes(1);
    });

    it("is denied on 401 or 403, whichever shape the error takes", async () => {
        for (const error of [
            { status: 401 },
            { status: 403 },
            { response: { status: 403 } },
            { statusCode: 401 },
        ]) {
            expect(
                await resolveHubStatus({ ...base, verify: failWith(error) }),
            ).toBe(HUB_STATUS.DENIED);
        }
    });

    // Outages must not be presented as "you are not a member".
    it("is error (retryable) on 5xx or network failure", async () => {
        expect(
            await resolveHubStatus({ ...base, verify: failWith({ status: 500 }) }),
        ).toBe(HUB_STATUS.ERROR);
        expect(
            await resolveHubStatus({
                ...base,
                verify: failWith(new Error("network")),
            }),
        ).toBe(HUB_STATUS.ERROR);
    });
});
