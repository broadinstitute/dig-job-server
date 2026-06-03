#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{
  "token_valid": true,
  "dataset": {
    "dataset_name": "ds1",
    "gwas_filename": "gwas.tsv",
    "expected_gwas_sha256": "aaa",
    "sample_size": 100,
    "inf_heritability": 0.1,
    "chr_to_update": "22",
    "image": "sagehen03/falcon:latest",
    "web_app_base_url": "http://127.0.0.1:${STUB_PORT:-18080}"
  }
}
EOF
}
teardown() { stop_stub_server; }

@test "metadata fetch prints dataset_name" {
  run bash "${RUN_SH_PATH}" --metadata-only dft_xxxxx
  [ "$status" -eq 0 ]
  [[ "$output" == *"ds1"* ]]
}

@test "expired token exits 1 with click-again message" {
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{"token_valid": false, "dataset": {}}
EOF
  run bash "${RUN_SH_PATH}" --metadata-only dft_xxxxx
  [ "$status" -eq 1 ]
  [[ "$output" == *"click Run FALCON again"* ]]
}

@test "transient 503 is retried and ultimately succeeds" {
  # Inject 2 transient failures before the real response
  python3 - <<EOF
import json, pathlib
p = pathlib.Path("${BATS_TMPDIR}/stub_config.json")
cfg = json.loads(p.read_text())
cfg["fail_count"] = 2
p.write_text(json.dumps(cfg))
EOF
  run bash "${RUN_SH_PATH}" --metadata-only dft_xxxxx
  [ "$status" -eq 0 ]
  [[ "$output" == *"ds1"* ]]
}

@test "persistent 5xx fails after retries with actionable message" {
  python3 - <<EOF
import json, pathlib
p = pathlib.Path("${BATS_TMPDIR}/stub_config.json")
cfg = json.loads(p.read_text())
cfg["fail_count"] = 99
p.write_text(json.dumps(cfg))
EOF
  run bash "${RUN_SH_PATH}" --metadata-only dft_xxxxx
  [ "$status" -eq 1 ]
  [[ "$output" == *"Couldn't reach"* ]]
}
