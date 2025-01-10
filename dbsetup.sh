#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


main() {
    "$SCRIPT_DIR/docker_db/docker_db.sh" start
    alembic upgrade head
    python -m scripts.db_ops add-user "test-user" "password"
}

main
