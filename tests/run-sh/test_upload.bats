#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
  # Warm cache + refdata short-circuit
  mkdir -p "${FALCON_HOME}/data"
  touch "${FALCON_HOME}/data/.warm"
  mkdir -p "${FALCON_HOME}/data/LD" "${FALCON_HOME}/data/genes" "${FALCON_HOME}/data/V2G"
  touch "${FALCON_HOME}/data/LD/22.ld.sorted.gz" \
        "${FALCON_HOME}/data/genes/22.genes.loc" \
        "${FALCON_HOME}/data/V2G/cS2G.22.SGscore"
  # Real GWAS file with computed SHA + symlink
  mkdir -p "${BATS_TMPDIR}/inputs"
  printf "rsID\tCHROM\n" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  mkdir -p "${FALCON_HOME}/work/ds1"
  ln -sf "${BATS_TMPDIR}/inputs/gwas.tsv" "${FALCON_HOME}/work/ds1/gwas.tsv"
  # Results dir + manifest so upload has files to push and idempotency_check fires
  mkdir -p "${FALCON_HOME}/work/ds1/results"
  echo "fake gene results" > "${FALCON_HOME}/work/ds1/results/run1.wg.genes"
  echo "fake variants"     > "${FALCON_HOME}/work/ds1/results/run1.wg.variants"
  echo '{"schema_version":1}' > "${FALCON_HOME}/work/ds1/manifest.json"
  # Stub config with real SHA (NO put_fail by default)
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{ "token_valid": true,
  "dataset": {
    "dataset_name": "ds1", "gwas_filename": "gwas.tsv",
    "expected_gwas_sha256": "${SHA}",
    "sample_size": 100, "inf_heritability": 0.1, "chr_to_update": "22",
    "image": "sagehen03/falcon:latest",
    "web_app_base_url": "http://127.0.0.1:${STUB_PORT:-18080}"
  }}
EOF
  install_recording_docker
}
teardown() { stop_stub_server; }

@test "happy path uploads all files and exits 0" {
  run bash -c "FALCON_IDEMPOTENCY=u bash '${RUN_SH_PATH}' --upload-only dft_xxx"
  [ "$status" -eq 0 ]
}

@test "manifest in results/ is staged at work root as manifest.json" {
  # FALCON writes results/<base>.wg.manifest.json; nothing at the work root.
  rm -f "${FALCON_HOME}/work/ds1/manifest.json"
  echo '{"schema_version":1}' > "${FALCON_HOME}/work/ds1/results/run1.wg.manifest.json"
  run bash -c "FALCON_IDEMPOTENCY=u bash '${RUN_SH_PATH}' --upload-only dft_xxx"
  [ "$status" -eq 0 ]
  # Staged under the canonical name the server's finalize reads.
  [ -f "${FALCON_HOME}/work/ds1/manifest.json" ]
}

@test "PUT failure writes upload-retry.sh and exits 1" {
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{ "token_valid": true, "put_fail": true,
  "dataset": { "dataset_name": "ds1", "gwas_filename": "gwas.tsv",
    "expected_gwas_sha256": "${SHA}", "sample_size": 100, "inf_heritability": 0.1,
    "chr_to_update": "22", "image": "sagehen03/falcon:latest",
    "web_app_base_url": "http://127.0.0.1:${STUB_PORT:-18080}" } }
EOF
  run bash -c "FALCON_IDEMPOTENCY=u bash '${RUN_SH_PATH}' --upload-only dft_xxx"
  [ "$status" -eq 1 ]
  [ -f "${FALCON_HOME}/work/ds1/upload-retry.sh" ]
  grep -q "curl -X PUT" "${FALCON_HOME}/work/ds1/upload-retry.sh"
}
