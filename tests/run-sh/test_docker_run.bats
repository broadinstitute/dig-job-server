#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
  # Warm cache short-circuit
  mkdir -p "${FALCON_HOME}/data"
  touch "${FALCON_HOME}/data/.warm"
  # Refdata short-circuit
  mkdir -p "${FALCON_HOME}/data/LD" "${FALCON_HOME}/data/genes" "${FALCON_HOME}/data/V2G"
  touch "${FALCON_HOME}/data/LD/22.ld.sorted.gz" \
        "${FALCON_HOME}/data/genes/22.genes.loc" \
        "${FALCON_HOME}/data/V2G/cS2G.22.SGscore"
  # Real GWAS file + matching SHA
  mkdir -p "${BATS_TMPDIR}/inputs"
  printf "rsID\tCHROM\n" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  mkdir -p "${FALCON_HOME}/work/ds1"
  ln -sf "${BATS_TMPDIR}/inputs/gwas.tsv" "${FALCON_HOME}/work/ds1/gwas.tsv"
  # Stub config with real SHA
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
  install_recording_docker
}
teardown() { stop_stub_server; }

@test "docker run is invoked with expected mounts" {
  run bash -c "bash '${RUN_SH_PATH}' --falcon-only dft_xxx"
  [ "$status" -eq 0 ]
  grep -q "RAN.*--rm.*-v.*${FALCON_HOME}/data:/falcon-data:ro" "${RECORD}"
  grep -q "RAN.*-v.*${FALCON_HOME}/work/ds1:/work" "${RECORD}"
  grep -q "RAN.*sagehen03/falcon:latest run /work/config.ini" "${RECORD}"
  # Container runs as the host user so result files aren't root-owned.
  grep -q "RAN.*--user $(id -u):$(id -g)" "${RECORD}"
}

@test "second invocation prompts for re-run / upload-only / quit" {
  mkdir -p "${FALCON_HOME}/work/ds1/results"
  touch "${FALCON_HOME}/work/ds1/results/run1.wg.genes"
  run bash -c "FALCON_IDEMPOTENCY=q bash '${RUN_SH_PATH}' --falcon-only dft_xxx"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Run already complete"* ]]
}
