#!/usr/bin/env bash
# ThinkSocial HQ setup for WSL (Ubuntu). Safe to run again at any time.
# It asks before installing anything and never writes a secret into the repository.
#
#   ./setup.sh           check, ask, install what is missing, prepare the folders
#   ./setup.sh --check   only report what is installed; change nothing
#   ./setup.sh --yes     answer yes to every install question
#   ./setup.sh --list-folders   print the folders setup creates (used by the tests)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Every folder an agent writes into. Matches docs/layout.md; tests/test_layout.sh checks that.
FOLDERS=(
  memory work/briefs reports approvals
  clients clients/_template inventory team growth ops
  inventory/drop inventory/extracted inventory/master inventory/review/done
  inventory/clients inventory/rules inventory/tools
  team/sops team/qa team/checkins
  growth/research growth/proposals growth/outreach growth/docs
  ops/contracts
)
[[ "${1:-}" == --list-folders ]] && { printf '%s\n' "${FOLDERS[@]}"; exit 0; }
cd "$ROOT"
MODE=ask
case "${1:-}" in --check) MODE=check ;; --yes) MODE=yes ;; "") ;; *) echo "usage: ./setup.sh [--check|--yes]"; exit 2 ;; esac

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
status() { if have "$1"; then printf '  %-10s installed\n' "$1"; else printf '  %-10s missing\n' "$1"; fi; }
ask() {  # ask "question" -> 0 for yes
  [[ $MODE == yes ]] && return 0
  [[ $MODE == check ]] && return 1
  local reply; read -r -p "$1 [y/N] " reply; [[ "$reply" =~ ^[Yy] ]]
}

bold "ThinkSocial HQ setup"
if grep -qi microsoft /proc/version 2>/dev/null; then echo "  Running inside WSL. Good."
else echo "  Not WSL. That is fine on any Ubuntu or Debian machine."; fi

bold "1. What is installed"
for tool in git curl python3 tmux node npm claude gh herdr magick convert jq; do status "$tool"; done

bold "2. Basic tools (git, curl, Python, tmux, ImageMagick for sample ads, jq, unzip)"
need=()
for pair in git:git curl:curl python3:python3 tmux:tmux jq:jq unzip:unzip; do have "${pair%%:*}" || need+=("${pair##*:}"); done
have magick || have convert || need+=(imagemagick)
if (( ${#need[@]} )); then
  if ask "Install ${need[*]} with apt (needs your Ubuntu password)?"; then
    sudo apt-get update && sudo apt-get install -y "${need[@]}"
  else echo "  Skipped. Missing: ${need[*]}"; fi
else echo "  All present."; fi

bold "3. Node.js LTS (needed by some Claude Code tools and connectors)"
if have node; then echo "  Node $(node --version) present."
elif ask "Install Node.js LTS with nvm (official script from github.com/nvm-sh/nvm)?"; then
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh" && nvm install --lts
else echo "  Skipped."; fi

bold "4. Claude Code"
if have claude; then echo "  Claude Code present."
elif ask "Install Claude Code with the official installer (claude.ai/install.sh)?"; then
  curl -fsSL https://claude.ai/install.sh | bash
  echo "  Open a new terminal, run 'claude' once and sign in with your Claude account."
else echo "  Skipped. Install later from https://claude.com/claude-code"; fi

bold "5. GitHub CLI (optional, for backing this folder up to a private repository)"
if have gh; then echo "  gh present."
elif ask "Install the GitHub CLI with apt?"; then sudo apt-get install -y gh
else echo "  Skipped."; fi

bold "6. herdr (optional, recommended; tmux works without it)"
if have herdr; then
  echo "  herdr present."
  if ask "Let herdr see Claude Code's state (herdr integration install claude)?"; then herdr integration install claude; fi
elif ask "Install herdr from the official installer (herdr.dev, Apache 2.0)?"; then
  curl -fsSL https://herdr.dev/install.sh | sh
  echo "  Then run: herdr integration install claude"
else echo "  Skipped. scripts/hq will use tmux."; fi

if [[ $MODE == check ]]; then bold "Check only. Nothing was changed."; exit 0; fi

bold "7. Folders and private files"
if [[ ! -f .env ]]; then cp .env.example .env && chmod 600 .env && echo "  Created .env (private, ignored by git). Fill in keys only when you need them."
else echo "  .env already exists. Left alone."; fi
if [[ ! -f memory/MEMORY.md ]]; then mkdir -p memory && cp -n memory-seed/*.md memory/ && echo "  Copied the starter memories into memory/."
else echo "  memory/ already set up. Left alone."; fi
mkdir -p "${FOLDERS[@]}"
chmod +x scripts/hq scripts/ledger scripts/new-client scripts/memory-sync scripts/dashboard.py inventory/tools/*.py tests/*.sh 2>/dev/null
echo "  Folders ready: ${FOLDERS[*]}"

bold "8. Your private working files (made once, never committed)"
make_once() {  # make_once live example how: copy the example, or keep only its header
  local live="$1" example="$2" how="$3"
  if [[ -f "$live" ]]; then echo "  $live already exists. Left alone."; return; fi
  case "$how" in
    copy) cp "$example" "$live" ;;
    header) head -n 1 "$example" > "$live" ;;
    table) awk '{print} /^\| *---/{exit}' "$example" > "$live" ;;
  esac
  echo "  Made $live"
}
make_once clients/INDEX.md clients/INDEX.example.md copy
make_once team/roster.csv team/roster.example.csv header
make_once team/qa/qa-log.csv team/qa/qa-log.example.csv header
make_once growth/pipeline.md growth/pipeline.example.md table
make_once ops/billing.csv ops/billing.example.csv header
scripts/memory-sync >/dev/null && echo "  Each space's CLAUDE.md lists the memories tagged to it."

bold "9. Quick self test"
log="${TMPDIR:-/tmp}/thinksocial-hq-tests.log"
if bash tests/run.sh >"$log" 2>&1; then echo "  All tests passed."
else echo "  Some tests failed. See $log"; fi

bold "Done. Next:"
cat <<'NEXT'
  scripts/hq start                  open HQ, Clients, Inventory, Team, Growth (and Research) and Ops
  scripts/hq attach                 look at them (tmux), or use the herdr window
  scripts/new-client <slug>         make a folder for a new client
  docs/layout.md                    which workspace works in which folder
  python3 scripts/dashboard.py      the dashboard at http://localhost:8765
In the HQ window, try:  /status
NEXT
