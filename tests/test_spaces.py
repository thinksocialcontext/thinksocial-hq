"""Every space is tied together: herdr workspace, folder, CLAUDE.md, memory and the ledger.

For every row of the docs/layout.md table this proves:
  * setup creates the folder (or it is the repository root)
  * the folder has a CLAUDE.md that tells its agent to read memory/MEMORY.md and to use scripts/ledger,
    and that lists the memories tagged to the space
  * scripts/hq opens a herdr workspace (or the Growth Research tab) with the same label, rooted at that
    folder (run against a fake herdr on PATH; the real herdr is never called)
  * the ledger knows the space with the same folder
  * a ledger job started from that folder, with no --space flag, shows on that space's dashboard page
    and not on another space's page; a job started in a client folder shows on that client's page
"""
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dashboard  # noqa: E402

sys.path.pop(0)

FAKE_HERDR = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_HERDR_DIR"]; st = os.path.join(d, "state.json"); a = sys.argv[1:]
with open(os.path.join(d, "calls.log"), "a") as f: f.write(json.dumps(a) + "\n")
s = json.load(open(st)) if os.path.exists(st) else {"ws": 0, "agents": []}
def opt(k): return a[a.index(k) + 1] if k in a else ""
out = {}
if a[:2] == ["agent", "list"]: out = {"result": {"agents": s["agents"]}}
elif a[:2] == ["workspace", "create"]:
    s["ws"] += 1; w = "w%d" % s["ws"]
    out = {"result": {"workspace": {"workspace_id": w}, "root_pane": {"pane_id": w + ":p1"}}}
elif a[:2] == ["tab", "create"]:
    w = opt("--workspace"); out = {"result": {"tab": {"tab_id": w + ":t2"}, "root_pane": {"pane_id": w + ":p2"}}}
elif a[:2] == ["agent", "start"]:
    p = opt("--pane"); s["agents"].append({"name": a[2], "pane_id": p, "workspace_id": p.split(":")[0], "agent_status": "idle"})
json.dump(s, open(st, "w")); print(json.dumps(out))
'''


def layout_rows():
    """(label, folder, agent) from the docs/layout.md table; folder "" is the repository root."""
    doc = (ROOT / "docs" / "layout.md").read_text()
    rows = re.findall(r"^\| ([^|]+?) \| `([^`]+)`[^|]*\| `([\w-]+)` \|", doc, re.M)
    return [(label.strip(), folder.strip("./").rstrip("/"), agent) for label, folder, agent in rows]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SpacesTest(unittest.TestCase):
    def test_layout_has_every_space(self):
        agents = [r[2] for r in layout_rows()]
        self.assertEqual(agents, ["hq", "clients", "inventory", "team", "growth", "growth-research", "ops"])

    def test_folder_and_claude_md(self):
        made = set(subprocess.run(["bash", str(ROOT / "setup.sh"), "--list-folders"], capture_output=True, text=True,
                                  check=True).stdout.split())
        sync = subprocess.run([sys.executable, str(ROOT / "scripts" / "memory-sync"), "--list"], capture_output=True,
                              text=True, check=True, env={**os.environ, "HQ_MEMORY_DIR": str(ROOT / "memory-seed")}).stdout
        for label, folder, agent in layout_rows():
            with self.subTest(space=agent):
                if folder:
                    self.assertIn(folder, made, f"setup.sh does not create {folder}")
                claude = ROOT / folder / "CLAUDE.md"
                self.assertTrue(claude.is_file(), f"{claude} missing")
                text = claude.read_text()
                self.assertIn("memory/MEMORY.md", text, f"{folder or 'root'} CLAUDE.md must point at the memory index")
                self.assertIn("scripts/ledger", text, f"{folder or 'root'} CLAUDE.md must point at the ledger")
                self.assertIn("<!-- memories:start", text)
                # every memory tagged to this space (or all) is listed in its CLAUDE.md
                for line in sync.splitlines():
                    name, space = line.split()[0], re.search(r"space=(\S+)", line).group(1).split(",")
                    if agent in space or "all" in space:
                        self.assertIn(f"memory/{name}", text, f"{name} is tagged {agent} but not listed")

    def test_herdr_workspaces_match_the_layout(self):
        tmp = tempfile.mkdtemp()
        try:
            (Path(tmp) / "bin").mkdir()
            fake = Path(tmp) / "bin" / "herdr"
            fake.write_text(FAKE_HERDR)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            env = {**os.environ, "FAKE_HERDR_DIR": tmp, "HQ_BACKEND": "herdr", "PATH": f"{tmp}/bin:{os.environ['PATH']}"}
            subprocess.run([str(ROOT / "scripts" / "hq"), "start"], env=env, check=True, capture_output=True)
            calls = [json.loads(l) for l in (Path(tmp) / "calls.log").read_text().splitlines()]
        finally:
            shutil.rmtree(tmp)

        def opt(c, k):
            return c[c.index(k) + 1]
        workspaces = {opt(c, "--label"): (opt(c, "--cwd"), f"w{i}") for i, c in
                      enumerate((c for c in calls if c[:2] == ["workspace", "create"]), 1)}
        tabs = {opt(c, "--label"): (opt(c, "--cwd"), opt(c, "--workspace")) for c in calls if c[:2] == ["tab", "create"]}
        started = {c[2]: opt(c, "--pane") for c in calls if c[:2] == ["agent", "start"]}
        for label, folder, agent in layout_rows():
            with self.subTest(space=agent):
                where = str(ROOT / folder) if folder else str(ROOT)
                if " / " in label:  # a tab inside a workspace
                    parent, tab = [x.strip() for x in label.split("/")]
                    self.assertEqual(tabs[tab][0], where)
                    self.assertEqual(tabs[tab][1], workspaces[parent][1], f"{tab} tab is not in the {parent} workspace")
                    self.assertTrue(started[agent].startswith(workspaces[parent][1] + ":"))
                else:
                    self.assertEqual(workspaces[label][0], where, f"herdr workspace {label} is not rooted at {folder}")
                    self.assertTrue(started[agent].startswith(workspaces[label][1] + ":"))
        self.assertEqual(len(workspaces) + len(tabs), len(layout_rows()))

    def test_ledger_spaces_match_the_layout(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger"), "spaces"], capture_output=True,
                             text=True, check=True).stdout
        spaces = dict(line.split("\t") for line in out.splitlines())
        for label, folder, agent in layout_rows():
            self.assertEqual(spaces.get(agent), folder or ".", agent)
            self.assertIn(agent, dashboard.SPACE_PAGES, f"no dashboard page shows the {agent} space")

    def test_a_job_written_from_a_space_shows_on_its_page(self):
        tmp = tempfile.TemporaryDirectory()
        t = Path(tmp.name)
        env = {**os.environ, "HQ_LEDGER_DIR": str(t / "work"), "HQ_APPROVALS_DIR": str(t / "approvals"),
               "HQ_BACKEND": "tmux", "HQ_TMUX_SOCKET": f"hqspaces{os.getpid()}", "HQ_STATE_SAMPLE": "0.1"}
        titles = {}
        for i, (label, folder, agent) in enumerate(layout_rows()):
            title = f"Job from the {agent} space"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger"), "start", "--key", f"space-{i}",
                            "--agent", agent, "--title", title], cwd=str(ROOT / folder), env=env, check=True,
                           capture_output=True)
            titles[agent] = title
        client_title = "Job from inside the example client folder"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger"), "start", "--key", "client-job", "--agent",
                        "clients", "--title", client_title], cwd=str(ROOT / "clients" / "example-boutique"), env=env,
                       check=True, capture_output=True)
        port = free_port()
        proc = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "dashboard.py"), "--port", str(port)],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def get(path):
            for _ in range(80):
                try:
                    return urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5).read().decode()
                except OSError:
                    time.sleep(0.1)
            self.fail("dashboard did not start")
        try:
            pages = {agent: get(dashboard.SPACE_PAGES[agent]) for agent in titles}
            for agent, title in titles.items():
                with self.subTest(space=agent):
                    page = pages[agent]
                    start = page.index('id="work"')
                    work = page[start:page.index("</section>", start)]  # the page's own "Work in this space" section
                    self.assertIn(title, work, f"{agent} job missing from {dashboard.SPACE_PAGES[agent]}")
                    for other, other_title in titles.items():
                        if dashboard.SPACE_PAGES[other] != dashboard.SPACE_PAGES[agent]:
                            self.assertNotIn(other_title, work, f"{other} job leaked onto the {agent} page")
            start = pages["clients"].index('id="work"')
            self.assertIn(client_title, pages["clients"][start:pages["clients"].index("</section>", start)])
            client_page = get("/client/example-boutique")
            self.assertIn(client_title, client_page)
            self.assertNotIn(titles["inventory"], client_page)
            view = subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger"), "view", "--client",
                                   "example-boutique"], env=env, capture_output=True, text=True, check=True).stdout
            self.assertIn(client_title, view)
            self.assertNotIn(titles["clients"], view)
        finally:
            proc.terminate()
            proc.wait(5)
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
