#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
  # Pre-seed the data dir so warm_cache_prompt short-circuits via the
  # empty-dir check (returns 0) without consuming stdin.
  mkdir -p "${FALCON_HOME}/data"
  touch "${FALCON_HOME}/data/.warm"
  # Compute a real SHA for a fixture file so resolve_gwas passes.
  mkdir -p "${BATS_TMPDIR}/inputs"
  printf "rsID\tCHROM\n" > "${BATS_TMPDIR}/inputs/gwas.tsv"
  SHA=$(sha256sum "${BATS_TMPDIR}/inputs/gwas.tsv" 2>/dev/null \
        || shasum -a 256 "${BATS_TMPDIR}/inputs/gwas.tsv")
  SHA="${SHA%% *}"
  # Pre-create the GWAS symlink so resolve_gwas doesn't prompt.
  mkdir -p "${FALCON_HOME}/work/ds1"
  ln -sf "${BATS_TMPDIR}/inputs/gwas.tsv" "${FALCON_HOME}/work/ds1/gwas.tsv"
  # Stub config with the computed SHA.
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
  # docker stub that records fetch-reference calls.
  mkdir -p "${BATS_TMPDIR}/recording-bin"
  rm -f "${BATS_TMPDIR}/docker-log"
  cat > "${BATS_TMPDIR}/recording-bin/docker" <<'EOS'
#!/usr/bin/env bash
case "$1" in
  info) exit 0 ;;
  image) if [ "$2" = "inspect" ]; then exit 0; fi ;;
  pull) exit 0 ;;
  run)
    if [[ "$*" == *"fetch-reference"* ]]; then
      echo "FETCH $*" >> "${RECORD:-${BATS_TMPDIR}/docker-log}"
    fi
    exit 0 ;;
esac
exit 0
EOS
  chmod +x "${BATS_TMPDIR}/recording-bin/docker"
  ln -sf "$(command -v curl)"        "${BATS_TMPDIR}/recording-bin/curl"
  ln -sf "$(command -v tar)"         "${BATS_TMPDIR}/recording-bin/tar"
  ln -sf "$(command -v python3)"     "${BATS_TMPDIR}/recording-bin/python3"
  ln -sf "$(command -v sha256sum || command -v shasum)" "${BATS_TMPDIR}/recording-bin/sha256sum"
  export PATH="${BATS_TMPDIR}/recording-bin:$PATH"
  export RECORD="${BATS_TMPDIR}/docker-log"
}
teardown() { stop_stub_server; }

@test "topup calls fetch-reference with the chrs from metadata" {
  run bash -c "bash '${RUN_SH_PATH}' --refdata-only dft_xxx"
  [ "$status" -eq 0 ]
  grep -q "FETCH.*--chrs 22" "${RECORD}"
}

@test "topup skips when all required chrs already on disk" {
  mkdir -p "${FALCON_HOME}/data/LD"
  touch "${FALCON_HOME}/data/LD/22.ld.sorted.gz"
  mkdir -p "${FALCON_HOME}/data/genes" && touch "${FALCON_HOME}/data/genes/22.genes.loc"
  mkdir -p "${FALCON_HOME}/data/V2G"   && touch "${FALCON_HOME}/data/V2G/cS2G.22.SGscore"
  # Make the absence-of-FETCH assertion deterministic: ensure the log file
  # exists (so a missing-file grep can't masquerade as success).
  : > "${RECORD}"
  run bash -c "bash '${RUN_SH_PATH}' --refdata-only dft_xxx"
  [ "$status" -eq 0 ]
  ! grep -q "FETCH" "${RECORD}"
}

@test "no FALCON_CHRS aborts non-interactively without fetching" {
  : > "${RECORD}"
  run bash -c "FALCON_CHRS= bash '${RUN_SH_PATH}' --refdata-only dft_xxx"
  [ "$status" -ne 0 ]
  [[ "$output" == *"FALCON_CHRS"* ]]
  ! grep -q "FETCH" "${RECORD}"
}
