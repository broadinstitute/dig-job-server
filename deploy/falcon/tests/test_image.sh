#!/usr/bin/env bash
set -Eeuo pipefail
IMG="${1:?usage: test_image.sh <image>}"
fail() { echo "FAIL: $*" >&2; exit 1; }

docker run --rm --entrypoint python3 "$IMG" --version >/dev/null 2>&1 \
  || fail "python3 not on PATH"
docker run --rm --entrypoint python3 "$IMG" -c \
  'import falcon_prep.cli' >/dev/null 2>&1 \
  || fail "converter not importable"
for d in genes V2G annotations; do
  docker run --rm --entrypoint test "$IMG" -d "/opt/falcon-ref/$d" \
    || fail "missing bundled reference: $d"
done
docker run --rm --entrypoint test "$IMG" -f /opt/falcon-ref/genes/21.genes.loc \
  || fail "genes/21.genes.loc missing"
echo "PASS"
