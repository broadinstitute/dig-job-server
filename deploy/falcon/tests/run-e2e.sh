#!/usr/bin/env bash
# Submit one real job-server dataset end to end and check the outputs exist.
set -Eeuo pipefail
USER_NAME="${1:-ngth}"
DATASET="${2:-Kurki2023_FinnGen_EU}"
REGION="${AWS_REGION:-us-east-1}"
ROOT="s3://dig-ldsc-server/userdata/${USER_NAME}/genetic/${DATASET}/falcon"

jid=$(aws batch submit-job --region "$REGION" \
  --job-name "falcon-e2e-$(echo "$DATASET" | tr -c 'a-zA-Z0-9' '-')" \
  --job-queue falcon-queue \
  --job-definition falcon-rs-dataset-job \
  --parameters "username=${USER_NAME},dataset=${DATASET}" \
  --query jobId --output text)
echo "submitted $jid"

st=""
MAX_POLLS=60
poll=0
while (( poll < MAX_POLLS )); do
  st=$(aws batch describe-jobs --region "$REGION" --jobs "$jid" \
       --query 'jobs[0].status' --output text)
  case "$st" in SUCCEEDED|FAILED) break ;; esac
  poll=$(( poll + 1 ))
  sleep 60
done
(( poll < MAX_POLLS )) || { echo "FAIL: job still $st after ${MAX_POLLS} polls (~${MAX_POLLS}min); giving up"; exit 1; }
echo "terminal: $st"
[ "$st" = SUCCEEDED ] || { echo "FAIL: job did not succeed"; exit 1; }

for f in out.wg.genes manifest.json; do
  aws s3 ls "$ROOT/$f" >/dev/null 2>&1 || { echo "FAIL: missing $f"; exit 1; }
done

MANIFEST="$(aws s3 cp --quiet "$ROOT/manifest.json" -)"
printf '%s' "$MANIFEST" | python3 -m json.tool

printf '%s' "$MANIFEST" | python3 -c '
import json, re, sys

manifest = json.load(sys.stdin)

sha = manifest.get("input_sha256", "")
assert re.fullmatch(r"[0-9a-f]{64}", sha), f"input_sha256 is not a sha256 hex digest: {sha!r}"

rate = manifest.get("falcon", {}).get("rsid_resolution_rate")
assert rate is not None and rate > 0.5, f"falcon.rsid_resolution_rate too low: {rate!r}"

print(f"input_sha256 ok, rsid_resolution_rate={rate}")
'
echo "PASS"
