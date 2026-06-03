#!/usr/bin/env bats

load test_helper

setup() {
  start_stub_server
}

teardown() {
  stop_stub_server
}

@test "preflight exits 0 when all tools present" {
  run bash "${RUN_SH_PATH}" --preflight-only
  [ "$status" -eq 0 ]
}
