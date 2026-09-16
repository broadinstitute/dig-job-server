// Decide whether a failed /api/auth/verify/ call means the stored token is
// unusable and must be discarded.
//
// The user service answers 401 for an expired or malformed JWT and 403 when
// the token was minted for a different group ("Token was not issued for
// group: ...") or the user is no longer a member. In every one of those cases
// retrying with the same token can never succeed, so the caller should drop
// it and fall back to the default login. Network failures and 5xx responses
// are transient: keep the token.
export function isVerifyRejection(error) {
  const status = error?.status ?? error?.response?.status;
  return status === 401 || status === 403;
}
