#!/usr/bin/env bash
# Nothing private in the files git would commit: no paths from the machine this was built on,
# no real client or customer names, no email addresses except obviously fake ones, nothing credential shaped.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  mapfile -t files < <(git ls-files --cached --others --exclude-standard)
else
  mapfile -t files < <(find . -type f -not -path './.git/*' -not -path './work/*' -not -path './memory/*' | sed 's|^\./||')
fi
self="tests/test_privacy.sh"
bad=0
check() {  # check "description" pattern
  local hits
  hits="$(printf '%s\0' "${files[@]}" | grep -zv "^$self\$" | xargs -0 grep -nIE "$2" 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then echo "FAIL $1:"; echo "$hits" | head -5; bad=1; else echo "ok  no $1"; fi
}
check "home directory paths" '/home/[a-z]|/Users/[a-z]|C:\\Users'
# Real client names are never written in this public repo. List them one per line in
# tests/private-names.txt (gitignored) on the agency computer and this check uses them.
if [[ -s "$ROOT/tests/private-names.txt" ]]; then
  check "real client or testimonial names" "$(grep -v '^#' "$ROOT/tests/private-names.txt" | sed '/^$/d' | paste -sd'|')"
else
  echo "ok  no real client names (skipped: tests/private-names.txt not present)"
fi
check "credential shaped strings" 'shp(at|ss|ca|pa)_[0-9a-fA-F]{8}|sk-[A-Za-z0-9]{16}|EAA[A-Za-z0-9]{30}|xox[bp]-[0-9]'
# grep -E has no lookahead, so check email addresses with Python instead of the line above
python3 - "${files[@]}" <<'PY' || bad=1
import re, sys
pat = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[a-z]{2,}")
hits = []
for f in sys.argv[1:]:
    try: text = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError): continue
    for m in pat.finditer(text):
        if not re.search(r"@(example\.(com|org|net)|noreply\.)", m.group(0)):
            hits.append(f"{f}: {m.group(0)}")
print("ok  no real email addresses" if not hits else "FAIL email addresses:\n" + "\n".join(hits[:5]))
sys.exit(1 if hits else 0)
PY
exit $bad
