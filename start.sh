#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export LD_LIBRARY_PATH="$PWD/kdl_local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec python3 app.py "$@"
