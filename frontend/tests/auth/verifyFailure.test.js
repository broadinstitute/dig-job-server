import { describe, it, expect } from "vitest";
import { isVerifyRejection } from "../../utils/auth/verifyFailure.js";

describe("isVerifyRejection", () => {
  it("treats a 401 ($fetch shape) as a rejection", () => {
    expect(isVerifyRejection({ status: 401 })).toBe(true);
  });

  it("treats a 403 ($fetch shape) as a rejection", () => {
    expect(isVerifyRejection({ status: 403 })).toBe(true);
  });

  it("treats a 403 (axios shape) as a rejection", () => {
    expect(isVerifyRejection({ response: { status: 403 } })).toBe(true);
  });

  it("does not treat a 500 as a rejection", () => {
    expect(isVerifyRejection({ status: 500 })).toBe(false);
  });

  it("does not treat an empty error as a rejection", () => {
    expect(isVerifyRejection({})).toBe(false);
  });

  it("does not throw on an undefined error", () => {
    expect(isVerifyRejection(undefined)).toBe(false);
  });
});
