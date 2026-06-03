#!/usr/bin/env bats
load test_helper

setup() {
  start_stub_server
  mk_default_dataset_config
  export FALCON_HOME="${BATS_TMPDIR}/falcon-home"
  rm -rf "$FALCON_HOME"
}
teardown() { stop_stub_server; }

@test "setup creates ~/falcon/{data,work}" {
  install_recording_docker
  run bash -c "bash '${RUN_SH_PATH}' --setup-only dft_xxxxx"
  [ "$status" -eq 0 ]
  [ -d "${FALCON_HOME}/data" ]
  [ -d "${FALCON_HOME}/work" ]
}

@test "setup pulls docker image when missing" {
  install_recording_docker
  run bash -c "bash '${RUN_SH_PATH}' --setup-only dft_xxxxx"
  [ "$status" -eq 0 ]
  grep -q "PULLED sagehen03/falcon:latest" "${BATS_TMPDIR}/docker-log"
}
