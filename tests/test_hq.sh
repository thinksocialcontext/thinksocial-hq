#!/usr/bin/env bash
# Smoke test for scripts/hq. The tmux part uses its own tmux socket and plain shells as agents.
# The herdr part puts a fake herdr first on PATH that only logs its calls, so it never
# touches a real tmux or herdr session you already have open.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HQ_BACKEND=tmux HQ_TMUX_SOCKET="hqtest$$" HQ_TMUX_SESSION=hqtest HQ_AGENT_CMD="" HQ_STATE_SAMPLE=0.3 HQ_QUIET_SECONDS=2 HQ_YES=1
HQ="$ROOT/scripts/hq"
pass=0
ok() { echo "ok  $1"; pass=$((pass + 1)); }
fail() { echo "FAIL $1"; tmux -L "$HQ_TMUX_SOCKET" kill-server 2>/dev/null || true; exit 1; }
trap 'tmux -L "$HQ_TMUX_SOCKET" kill-server 2>/dev/null || true' EXIT

[[ "$("$HQ" backend)" == tmux ]] && ok backend || fail backend
"$HQ" list | grep -q "not running" && ok "list before start" || fail "list before start"
"$HQ" start | grep -q "HQ started" && ok start || fail start
"$HQ" start | grep -q "already running" && ok "start is idempotent" || fail "start is idempotent"
n="$("$HQ" list --json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
[[ "$n" == 7 ]] && ok "seven agents listed" || fail "seven agents listed ($n)"
"$HQ" list --json | python3 -c 'import json,sys; d={a["name"] for a in json.load(sys.stdin)}; assert d=={"hq","clients","inventory","team","growth","growth-research","ops"}, d' \
  && ok "agent names" || fail "agent names"
sleep 1
"$HQ" prompt inventory "pwd; echo HQ_MARK_\$((40+2))" >/dev/null && ok prompt || fail prompt
[[ "$("$HQ" wait inventory 20)" == idle ]] && ok "wait returns idle" || fail "wait returns idle"
out="$("$HQ" read inventory 30)"
grep -q "HQ_MARK_42" <<<"$out" && ok "read shows output" || fail "read shows output"
grep -q "/inventory$" <<<"$out" && ok "inventory runs in inventory/" || fail "inventory runs in inventory/"
"$HQ" prompt growth-research "pwd" >/dev/null; "$HQ" wait growth-research 20 >/dev/null
grep -q "/growth/research$" <<<"$("$HQ" read growth-research 30)" && ok "growth-research runs in growth/research/" || fail "growth-research runs in growth/research/"
"$HQ" prompt team "echo '> half typed'" >/dev/null; "$HQ" wait team 20 >/dev/null
if "$HQ" prompt team "echo nope" 2>/dev/null; then fail "refuses when input box has text"; else ok "refuses when input box has text"; fi
"$HQ" prompt ops "echo 'Do you want to proceed? (y/n)'" >/dev/null
[[ "$("$HQ" wait ops 20)" == blocked ]] && ok "wait sees a dialog" || fail "wait sees a dialog"
"$HQ" list --json | python3 -c 'import json,sys; d={a["name"]:a["state"] for a in json.load(sys.stdin)}; assert d["ops"]=="blocked", d' \
  && ok "list marks blocked" || fail "list marks blocked"
if "$HQ" prompt ops "echo hi" 2>/dev/null; then fail "refuses a blocked agent"; else ok "refuses a blocked agent"; fi
if "$HQ" read nobody 2>/dev/null; then fail "unknown agent"; else ok "unknown agent rejected"; fi
"$HQ" stop | grep -q stopped && ok stop || fail stop

# ---------- herdr backend, with a fake herdr ----------
FAKE="$(mktemp -d)"; trap 'tmux -L "$HQ_TMUX_SOCKET" kill-server 2>/dev/null || true; rm -rf "$FAKE"' EXIT
mkdir -p "$FAKE/bin"
cat >"$FAKE/bin/herdr" <<'FAKEHERDR'
#!/usr/bin/env python3
# Fake herdr: logs every call as one JSON line and keeps a tiny state file. Talks to nothing.
import json, os, sys
d = os.environ["FAKE_HERDR_DIR"]; st = os.path.join(d, "state.json"); a = sys.argv[1:]
with open(os.path.join(d, "calls.log"), "a") as f: f.write(json.dumps(a) + "\n")
s = json.load(open(st)) if os.path.exists(st) else {"ws": 0, "agents": []}
def opt(k): return a[a.index(k) + 1] if k in a else ""
out = {}
if a[:2] == ["status", "server"]: pass
elif a[:2] == ["agent", "list"]: out = {"result": {"agents": s["agents"]}}
elif a[:2] == ["workspace", "create"]:
    s["ws"] += 1; w = "w%d" % s["ws"]
    out = {"result": {"workspace": {"workspace_id": w, "label": opt("--label")}, "root_pane": {"pane_id": w + ":p1"}}}
elif a[:2] == ["tab", "create"]:
    w = opt("--workspace"); out = {"result": {"tab": {"tab_id": w + ":t2"}, "root_pane": {"pane_id": w + ":p2"}}}
elif a[:2] == ["agent", "start"]:
    p = opt("--pane"); s["agents"].append({"name": a[2], "pane_id": p, "workspace_id": p.split(":")[0], "agent_status": "idle"})
json.dump(s, open(st, "w")); print(json.dumps(out))
FAKEHERDR
chmod +x "$FAKE/bin/herdr"
H() { FAKE_HERDR_DIR="$FAKE" HQ_BACKEND=herdr PATH="$FAKE/bin:$PATH" "$HQ" "$@"; }
[[ "$(FAKE_HERDR_DIR="$FAKE" PATH="$FAKE/bin:$PATH" command -v herdr)" == "$FAKE/bin/herdr" ]] && ok "fake herdr is first on PATH" || fail "fake herdr is first on PATH"
H start | grep -q "HQ started in herdr" && ok "herdr start" || fail "herdr start"
python3 - "$FAKE/calls.log" "$ROOT" <<'CHECK' && ok "herdr: six workspaces, labels match folders, Research tab in Growth" || fail "herdr layout"
import json, sys
calls = [json.loads(l) for l in open(sys.argv[1])]; root = sys.argv[2]
def opt(c, k): return c[c.index(k) + 1]
ws = [(opt(c, "--label"), opt(c, "--cwd")) for c in calls if c[:2] == ["workspace", "create"]]
want = [("HQ", root), ("Clients", root + "/clients"), ("Inventory", root + "/inventory"), ("Team", root + "/team"),
        ("Growth", root + "/growth"), ("Ops", root + "/ops")]
assert ws == want, ws
assert all("--no-focus" in c for c in calls if c[1:2] == ["create"]), "every create must use --no-focus"
tabs = [c for c in calls if c[:2] == ["tab", "create"]]
assert len(tabs) == 1, tabs
t = tabs[0]
assert (opt(t, "--label"), opt(t, "--cwd"), opt(t, "--workspace")) == ("Research", root + "/growth/research", "w5"), t
starts = [(c[2], opt(c, "--pane")) for c in calls if c[:2] == ["agent", "start"]]
assert starts == [("hq", "w1:p1"), ("clients", "w2:p1"), ("inventory", "w3:p1"), ("team", "w4:p1"), ("growth", "w5:p1"),
                  ("ops", "w6:p1"), ("growth-research", "w5:p2")], starts
renames = [c[2:] for c in calls if c[:2] == ["pane", "rename"]]
assert renames == [["w1:p1", "HQ"], ["w2:p1", "Clients"], ["w3:p1", "Inventory"], ["w4:p1", "Team"], ["w5:p1", "Growth"],
                   ["w6:p1", "Ops"], ["w5:p2", "Research"]], renames
CHECK
: >"$FAKE/calls.log"
H start | grep -q "already running" && ok "herdr start is idempotent" || fail "herdr start is idempotent"
! grep -q '"create"' "$FAKE/calls.log" && ok "herdr: no duplicate workspaces or tabs" || fail "herdr: no duplicate workspaces or tabs"
python3 - "$FAKE/state.json" <<'DROP'
import json, sys
s = json.load(open(sys.argv[1])); s["agents"] = [a for a in s["agents"] if a["name"] != "growth-research"]; json.dump(s, open(sys.argv[1], "w"))
DROP
: >"$FAKE/calls.log"
H start >/dev/null
[[ "$(grep -c '"create"' "$FAKE/calls.log")" == 1 ]] && grep -q '"tab", "create", "--workspace", "w5"' "$FAKE/calls.log" \
  && ok "herdr: a missing Research tab is added back, nothing else" || fail "herdr: missing Research tab"
H list --json | python3 -c 'import json,sys; d={a["name"]:a["state"] for a in json.load(sys.stdin)}; assert len(d)==7 and d["growth-research"]=="idle", d' \
  && ok "herdr list reads agent_status" || fail "herdr list reads agent_status"
echo "hq smoke: $pass passed"
