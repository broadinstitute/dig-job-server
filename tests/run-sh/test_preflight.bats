#!/usr/bin/env bats
load test_helper

setup() { start_stub_server; }
teardown() { stop_stub_server; }

@test "preflight fails when docker missing" {
  # construct a PATH that has everything EXCEPT docker
  mkdir -p "${BATS_TMPDIR}/no-docker-bin"
  ln -sf "$(command -v curl)" "${BATS_TMPDIR}/no-docker-bin/curl"
  ln -sf "$(command -v tar)" "${BATS_TMPDIR}/no-docker-bin/tar"
  ln -sf "$(command -v python3)" "${BATS_TMPDIR}/no-docker-bin/python3"
  ln -sf "$(command -v sha256sum || command -v shasum)" "${BATS_TMPDIR}/no-docker-bin/sha256sum"
  BASH_BIN="$(command -v bash)"
  run env PATH="${BATS_TMPDIR}/no-docker-bin" "${BASH_BIN}" "${RUN_SH_PATH}" --preflight-only
  [ "$status" -eq 1 ]
  [[ "$output" == *"docker"* ]]
  [[ "$output" == *"https://docs.docker.com/get-docker"* ]]
}

@test "preflight fails when python3 missing" {
  # construct a PATH that has docker but not python3
  mkdir -p "${BATS_TMPDIR}/fake-bin"
  ln -sf "$(command -v docker)" "${BATS_TMPDIR}/fake-bin/docker"
  ln -sf "$(command -v curl)" "${BATS_TMPDIR}/fake-bin/curl"
  ln -sf "$(command -v tar)" "${BATS_TMPDIR}/fake-bin/tar"
  ln -sf "$(command -v sha256sum || command -v shasum)" "${BATS_TMPDIR}/fake-bin/sha256sum"
  BASH_BIN="$(command -v bash)"
  run env PATH="${BATS_TMPDIR}/fake-bin" "${BASH_BIN}" "${RUN_SH_PATH}" --preflight-only
  [ "$status" -eq 1 ]
  [[ "$output" == *"python3"* ]]
}
