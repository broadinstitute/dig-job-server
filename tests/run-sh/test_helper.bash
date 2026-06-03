RUN_SH_PATH="${BATS_TEST_DIRNAME}/build/run.sh"

start_stub_server() {
  python3 "${BATS_TEST_DIRNAME}/fixtures/stub_server.py" \
    --port "${STUB_PORT:-18080}" \
    --state-dir "${BATS_TMPDIR}" &
  STUB_PID=$!
  # Render run.sh with the stub base URL baked in
  mkdir -p "${BATS_TEST_DIRNAME}/build"
  sed "s|{{GWAS_CE_BASE_URL}}|http://127.0.0.1:${STUB_PORT:-18080}|" \
    "${BATS_TEST_DIRNAME}/../../static/run.sh.tmpl" \
    > "${RUN_SH_PATH}"
  chmod +x "${RUN_SH_PATH}"
  # Default the chr scope to 22 (matches the stubs' chr_to_update) so the
  # all-chrs confirm doesn't fire; the idempotency answer defaults to quit.
  # Individual tests override either as needed.
  export FALCON_CHRS="${FALCON_CHRS:-22}"
  export FALCON_IDEMPOTENCY="${FALCON_IDEMPOTENCY:-q}"
  # Wait for stub
  for _ in $(seq 1 20); do
    curl -fs "http://127.0.0.1:${STUB_PORT:-18080}/health" && return 0
    sleep 0.1
  done
  echo "stub never started" >&2
  return 1
}

stop_stub_server() {
  kill "${STUB_PID}" 2>/dev/null || true
  wait "${STUB_PID}" 2>/dev/null || true
}

mk_default_dataset_config() {
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

install_recording_docker() {
  export PATH="${BATS_TMPDIR}/recording-bin:$PATH"
  mkdir -p "${BATS_TMPDIR}/recording-bin"
  cat > "${BATS_TMPDIR}/recording-bin/docker" <<'EOS'
#!/usr/bin/env bash
case "$1" in
  info) exit 0 ;;
  image) if [ "$2" = "inspect" ]; then exit 1; fi ;;
  pull) echo "PULLED $2" >> "${BATS_TMPDIR}/docker-log"; exit 0 ;;
  run) echo "RAN $*" >> "${BATS_TMPDIR}/docker-log"; exit 0 ;;
esac
exit 0
EOS
  chmod +x "${BATS_TMPDIR}/recording-bin/docker"
  rm -f "${BATS_TMPDIR}/docker-log"
  export RECORD="${BATS_TMPDIR}/docker-log"
}
