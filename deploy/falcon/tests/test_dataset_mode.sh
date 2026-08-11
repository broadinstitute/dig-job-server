#!/usr/bin/env bash
#
# Dataset mode vs. config mode, at the entrypoint's argument-parsing boundary.
# No AWS calls: every case here is rejected before the script would touch S3.
#
#   bash deploy/falcon/tests/test_dataset_mode.sh <image>
set -Eeuo pipefail
IMG="${1:?usage: test_dataset_mode.sh <image>}"
fail() { echo "FAIL: $*" >&2; exit 1; }

# Argument parsing only -- no AWS calls. Missing dataset must be rejected.
out=$(docker run --rm --entrypoint falcon-batch "$IMG" --username u 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || fail "missing --dataset should fail"
echo "$out" | grep -q -- "--dataset" || fail "error should name --dataset"

# Config mode must still work: a local config with no s3:// values.
out=$(docker run --rm --entrypoint falcon-batch "$IMG" /nonexistent.ini 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || fail "missing config should fail"
echo "$out" | grep -qi "config not found" || fail "config mode regressed: $out"

# A flag with no value must die cleanly, not abort on an unbound variable.
out=$(docker run --rm --entrypoint falcon-batch "$IMG" --username 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || fail "bare --username should fail"
echo "$out" | grep -q "requires a value" || fail "expected a clean die, got: $out"
echo "$out" | grep -q "unbound variable" && fail "leaked an unbound-variable abort: $out"

out=$(docker run --rm --entrypoint falcon-batch "$IMG" --username u --dataset 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || fail "trailing --dataset should fail"
echo "$out" | grep -q "requires a value" || fail "expected a clean die, got: $out"
echo "$out" | grep -q "unbound variable" && fail "leaked an unbound-variable abort: $out"

echo "PASS"
