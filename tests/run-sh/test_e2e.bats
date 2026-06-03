#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
  install_recording_docker
  # Seed a real GWAS file with a known sha
  mkdir -p "${BATS_TMPDIR}/inputs"
  printf "rsID\tCHROM\nrs1\t22\n" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  cat > "${BATS_TMPDIR}/stub_config.json" <<EOF
{ "token_valid": true,
  "dataset": { "dataset_name": "ds1", "gwas_filename": "gwas.tsv",
    "expected_gwas_sha256": "${SHA}", "sample_size": 100,
    "inf_heritability": 0.1, "chr_to_update": "22",
    "image": "sagehen03/falcon:latest",
    "web_app_base_url": "http://127.0.0.1:${STUB_PORT:-18080}" } }
EOF
  # docker stub must also create a results dir so the upload step finds files
  cat > "${BATS_TMPDIR}/recording-bin/docker" <<EOS
#!/usr/bin/env bash
case "\$1" in
  info) exit 0 ;;
  image) if [ "\$2" = "inspect" ]; then exit 0; fi ;;
  pull) exit 0 ;;
  run)
    if [[ "\$*" == *"run /work/config.ini"* ]]; then
      # ${FALCON_HOME} is intentionally unquoted: it expands now (at setup
      # time) so the resolved path is baked into the stub; \$host defers to
      # run-time inside the stub.
      host="${FALCON_HOME}/work/ds1"
      mkdir -p "\$host/results"
      echo "ran" > "\$host/results/run1.wg.genes"
      echo '{"schema_version":1}' > "\$host/manifest.json"
    fi
    exit 0 ;;
esac
exit 0
EOS
  chmod +x "${BATS_TMPDIR}/recording-bin/docker"
}
teardown() { stop_stub_server; }

@test "end-to-end happy path exits 0" {
  # Pre-create the GWAS at the expected work-dir path so no prompt is needed
  mkdir -p "${FALCON_HOME}/work/ds1"
  ln -sf "${BATS_TMPDIR}/inputs/gwas.tsv" "${FALCON_HOME}/work/ds1/gwas.tsv"
  # Pre-create reference data so warm-cache prompt + topup short-circuit
  mkdir -p "${FALCON_HOME}/data/LD" "${FALCON_HOME}/data/genes" "${FALCON_HOME}/data/V2G"
  touch "${FALCON_HOME}/data/LD/22.ld.sorted.gz"
  touch "${FALCON_HOME}/data/genes/22.genes.loc"
  touch "${FALCON_HOME}/data/V2G/cS2G.22.SGscore"

  run bash "${RUN_SH_PATH}" dft_xxx
  [ "$status" -eq 0 ]
  [[ "$output" == *"Results uploaded"* ]]
}

@test "missing token argument exits 2 with usage message" {
  run bash "${RUN_SH_PATH}"
  [ "$status" -eq 2 ]
  [[ "$output" == *"missing dataset token"* ]]
}
