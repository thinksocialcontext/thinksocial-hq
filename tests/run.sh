#!/usr/bin/env bash
# Run every ThinkSocial HQ test. Safe: temp folders, a private tmux socket and a fake herdr only.
set -euo pipefail
cd "$(dirname "$0")/.."
export HQ_BACKEND=tmux HQ_TMUX_SOCKET="hqrun$$"   # never read or drive a real herdr or tmux session
python3 -m unittest discover -s tests -v
bash tests/test_hq.sh
bash tests/test_layout.sh
bash tests/test_privacy.sh
HQ_MEMORY_DIR=memory-seed python3 scripts/memory-sync --check
bash -n setup.sh && echo "ok  setup.sh parses"
