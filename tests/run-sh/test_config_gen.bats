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
    "sumstats_columns": { "sumstats-chr-col": "CHR", "sumstats-id-col": "ID", "sumstats-se-col": "SE", "sumstats-z-col": "None" },
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

@test "config.ini contains server-supplied values" {
  run bash -c "bash '${RUN_SH_PATH}' --config-only dft_xxx"
  [ "$status" -eq 0 ]
  local cfg="${FALCON_HOME}/work/ds1/config.ini"
  [ -f "$cfg" ]
  grep -q "^sample-size *= *100"        "$cfg"
  grep -q "^inf-heritability *= *0.1"   "$cfg"
  grep -q "^chr-to-update *= *22"       "$cfg"
  grep -q "^dataset-name *= *ds1"       "$cfg"
  grep -q "^web-app-base-url *="        "$cfg"
}

@test "config.ini uses col_map-derived sumstats columns, not the old hardcoded names" {
  run bash -c "bash '${RUN_SH_PATH}' --config-only dft_xxx"
  [ "$status" -eq 0 ]
  local cfg="${FALCON_HOME}/work/ds1/config.ini"
  grep -q "^sumstats-chr-col = CHR$" "$cfg"
  grep -q "^sumstats-id-col = ID$"   "$cfg"
  grep -q "^sumstats-se-col = SE$"   "$cfg"
  grep -q "^sumstats-z-col = None$"  "$cfg"
  ! grep -q "CHROM" "$cfg"
  ! grep -q "rsID"  "$cfg"
  grep -q "^s2g-rsid-col" "$cfg"
}
