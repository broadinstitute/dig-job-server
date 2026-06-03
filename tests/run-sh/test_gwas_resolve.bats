#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
  mkdir -p "${FALCON_HOME}/data"
  touch "${FALCON_HOME}/data/.warm"
  # Compute sha of a small fixture
  mkdir -p "${BATS_TMPDIR}/inputs"
  printf "rsID\tCHROM\n" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{ "token_valid": true,
  "dataset": {
    "dataset_name": "ds1",
    "gwas_filename": "gwas.tsv",
    "expected_gwas_sha256": "${SHA}",
    "sample_size": 100, "inf_heritability": 0.1, "chr_to_update": "22",
    "image": "sagehen03/falcon:latest",
    "web_app_base_url": "http://127.0.0.1:${STUB_PORT:-18080}"
  }}
EOF
}
teardown() { stop_stub_server; }

@test "GWAS path matching sha256 is accepted" {
  install_recording_docker
  run bash -c "FALCON_GWAS_PATH='${BATS_TMPDIR}/inputs/gwas.tsv' bash '${RUN_SH_PATH}' --gwas-only dft_xxx"
  [ "$status" -eq 0 ]
}

@test "GWAS path with wrong sha256 is rejected with helpful message" {
  install_recording_docker
  printf "different bytes" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  run bash -c "FALCON_GWAS_PATH='${BATS_TMPDIR}/inputs/gwas.tsv' bash '${RUN_SH_PATH}' --gwas-only dft_xxx"
  [ "$status" -eq 1 ]
  [[ "$output" == *"doesn't match"* ]]
  [[ "$output" == *"re-upload the GWAS"* ]]
}

@test "sha mismatch clears the symlink so the next run reprompts" {
  install_recording_docker
  printf "different bytes" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  run bash -c "FALCON_GWAS_PATH='${BATS_TMPDIR}/inputs/gwas.tsv' bash '${RUN_SH_PATH}' --gwas-only dft_xxx"
  [ "$status" -eq 1 ]
  # WORK_DIR is ${FALCON_HOME}/work/${DATASET_NAME} → ds1
  [ ! -e "${FALCON_HOME}/work/ds1/gwas.tsv" ]
}
