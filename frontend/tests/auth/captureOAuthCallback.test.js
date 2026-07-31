import { describe, it, expect } from "vitest";
import {
  captureOAuthCallback,
  stripOAuthParams,
} from "../../utils/auth/captureOAuthCallback.js";

// Minimal stand-in for window.localStorage. Vitest runs with environment
// "node", so there is no real one, and injecting it keeps the unit under test
// free of globals.
const makeStorage = (initial = {}) => {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v);
    },
    removeItem: (k) => {
      delete data[k];
    },
  };
};

const SIGNED_OUT = { hasSignedOut: "true", isDefaultUser: "true" };

describe("successful callback", () => {
  it("stores the access token", () => {
    const storage = makeStorage();
    expect(
      captureOAuthCallback({ success: "true", access_token: "jwt-abc" }, storage),
    ).toBe(true);
    expect(storage.getItem("authToken")).toBe("jwt-abc");
  });

  // The user just authenticated explicitly, so the anonymous/default-user
  // session must not survive -- UserStore.tryDefaultLogin() keys off these two
  // flags, and leaving them set would let a default login stomp the real one.
  // stores/UserStore.js clears both on a credential login; the OAuth path in
  // pages/datasets/index.vue only cleared isDefaultUser. Match the credential
  // path, which is the correct one.
  it("clears the default-user and signed-out flags", () => {
    const storage = makeStorage(SIGNED_OUT);
    captureOAuthCallback({ success: "true", access_token: "jwt-abc" }, storage);
    expect(storage.getItem("isDefaultUser")).toBeNull();
    expect(storage.getItem("hasSignedOut")).toBeNull();
  });
});

describe("callbacks that must be ignored", () => {
  const untouched = (query) => {
    const storage = makeStorage(SIGNED_OUT);
    const captured = captureOAuthCallback(query, storage);
    expect(captured).toBe(false);
    expect(storage.getItem("authToken")).toBeNull();
    // A non-callback navigation must not disturb existing session state.
    expect(storage.getItem("hasSignedOut")).toBe("true");
    expect(storage.getItem("isDefaultUser")).toBe("true");
  };

  it("ignores an ordinary navigation with no query", () => untouched({}));
  it("ignores an undefined query", () => untouched(undefined));

  it("ignores a failed callback", () =>
    untouched({ success: "false", error: "User does not belong to group" }));

  it("ignores success without a token", () => untouched({ success: "true" }));

  it("ignores an empty token", () =>
    untouched({ success: "true", access_token: "" }));

  it("ignores success=true as a repeated param", () =>
    untouched({ success: ["true", "true"], access_token: "jwt-abc" }));

  // A repeated ?access_token= arrives as an array. Coercing it would store
  // "a,b" -- a token that is silently wrong rather than absent, which is the
  // worse failure because the user appears logged in until the first API call.
  it("ignores a repeated access_token rather than joining it", () =>
    untouched({ success: "true", access_token: ["jwt-a", "jwt-b"] }));
});

describe("robustness", () => {
  it("reports false when no storage is available", () => {
    expect(
      captureOAuthCallback({ success: "true", access_token: "jwt-abc" }, null),
    ).toBe(false);
  });
});

describe("stripOAuthParams", () => {
  it("removes every param the callback appends", () => {
    expect(
      stripOAuthParams({
        success: "true",
        access_token: "jwt-abc",
        created: "true",
        error: "nope",
      }),
    ).toEqual({});
  });

  // Stripping the whole query would silently discard app state -- e.g. the
  // ?redirect= that auth.global.js itself attaches when bouncing to /login.
  it("preserves unrelated params", () => {
    expect(
      stripOAuthParams({
        success: "true",
        access_token: "jwt-abc",
        redirect: "/datasets",
      }),
    ).toEqual({ redirect: "/datasets" });
  });

  it("does not mutate the input", () => {
    const query = { success: "true", access_token: "jwt-abc" };
    stripOAuthParams(query);
    expect(query).toEqual({ success: "true", access_token: "jwt-abc" });
  });

  it("handles an undefined query", () => {
    expect(stripOAuthParams(undefined)).toEqual({});
  });
});
