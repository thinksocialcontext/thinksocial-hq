#!/usr/bin/env bash
# The folders named in docs/layout.md must all be created by ./setup.sh, and scripts/hq
# must start each agent in the folder the layout table gives it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$ROOT" <<'PY'
import re, subprocess, sys
root = sys.argv[1]
doc = open(f"{root}/docs/layout.md").read()
made = set(subprocess.run(["bash", f"{root}/setup.sh", "--list-folders"], capture_output=True, text=True, check=True).stdout.split())
# folders in backticks that end in a slash, from the table and the prose
named = {m.strip("./").rstrip("/") for m in re.findall(r"`([\w./-]+/)`", doc)}
named.discard("")
# folders from the tree diagram, rebuilt from indentation
tree = doc.split("```")[1].splitlines()
stack = []
for line in tree:
    m = re.match(r"^([│ ]*)(?:├── |└── )([\w.-]+)/", line)
    if not m: continue
    depth = len(m.group(1)) // 4
    stack = stack[:depth] + [m.group(2)]
    named.add("/".join(stack))
# folders that ship in the repository instead of being made by setup
shipped = {"clients/_template", "clients/example-boutique"}
for f in shipped:
    assert __import__("os").path.isdir(f"{root}/{f}"), f"{f} should ship in the repository"
missing = sorted(f for f in named - shipped if f not in made and not any(x.startswith(f + "/") for x in made))
assert not missing, f"setup.sh does not create: {missing}"
print(f"ok  setup.sh creates all {len(named)} folders named in docs/layout.md")
hq = open(f"{root}/scripts/hq").read()
rows = re.findall(r"^\| ([^|]+?) \| `([^`]+)`[^|]*\| `([\w-]+)` \|", doc, re.M)
assert len(rows) == 7, rows
for label, folder, agent in rows:
    folder = folder.strip("./").rstrip("/")
    want = '"$ROOT"' if not folder else f'"$ROOT/{folder}"'
    assert re.search(rf"^\s*{re.escape(agent)}\) echo {re.escape(want)} ;;", hq, re.M), (agent, folder)
    tab = label.split("/")[-1].strip()
    assert re.search(rf"{re.escape(agent)}\) echo {re.escape(tab)} ;;", hq), (agent, tab)
print("ok  scripts/hq folders and labels match the docs/layout.md table")
PY
