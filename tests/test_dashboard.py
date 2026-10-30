"""Smoke test for scripts/dashboard.py. Temp ledger and approvals, an isolated tmux socket, the committed examples."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        (t / "approvals").mkdir()
        (t / "approvals" / "go.md").write_text("---\ntitle: Approve the inbox agent\nfrom: clients\nstatus: waiting\n---\n")
        (t / "approvals" / "old.md").write_text("---\ntitle: Old thing\nstatus: approved\n---\n")
        # copies of the committed examples only, so private files on a working copy never change the result
        for rel in ("clients/INDEX.example.md", "clients/example-boutique", "inventory/examples", "inventory/drop/README.md",
                    "team/roster.example.csv", "team/qa/qa-log.example.csv", "growth/pipeline.example.md",
                    "ops/billing.example.csv", "ops/tools.md"):
            src, dst = ROOT / rel, t / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
        self.env = {**os.environ, "HQ_LEDGER_DIR": str(t / "work"), "HQ_APPROVALS_DIR": str(t / "approvals"),
                    "HQ_BACKEND": "tmux", "HQ_TMUX_SOCKET": f"hqtest{os.getpid()}", "HQ_STATE_SAMPLE": "0.2",
                    "HQ_MEMORY_DIR": str(t / "no-memory"), "HQ_CLIENTS_DIR": str(t / "clients"),
                    "HQ_INVENTORY_DIR": str(t / "inventory"), "HQ_TEAM_DIR": str(t / "team"),
                    "HQ_GROWTH_DIR": str(t / "growth"), "HQ_OPS_DIR": str(t / "ops")}
        subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger"), "start", "--key", "d1", "--agent", "growth",
                        "--space", "growth", "--title", "Plan the pipeline"], env=self.env, check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_once(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "dashboard.py"), "--once"],
                             env=self.env, capture_output=True, text=True, check=True)
        s = json.loads(out.stdout)
        self.assertEqual([a["title"] for a in s["approvals"]], ["Approve the inbox agent"])
        self.assertEqual(s["ledger"][0]["title"], "Plan the pipeline")
        self.assertEqual(s["per_space"]["growth"]["open"], 1)
        self.assertTrue(s["growth"]["sample"])
        self.assertEqual(s["growth"]["open_value"], 1500 + 2500 + 1800)  # won is not open
        self.assertTrue(s["memory"]["starter"])
        self.assertEqual(s["agents"], [])  # no tmux session on the isolated socket

    def test_server(self):
        port = free_port()
        proc = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "dashboard.py"), "--port", str(port)],
                                env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                self.fail("dashboard did not start")
            for text in ("ThinkSocial <span>HQ</span>", "Approve the inbox agent", "Plan the pipeline", "SAMPLE"):
                self.assertIn(text, body)
            pages = {"/clients": ["Example Boutique", "Open KB questions"],
                     "/client/example-boutique": ["Onboarding", "preorders", "scripts/ledger view --client example-boutique"],
                     "/inventory": ["INV-EX-1001", "low confidence 0.62", "no rule matches", "2026-10-26-INV-EX-1001.csv"],
                     "/team": ["VA Lead A (fake)", "example-boutique"],
                     "/growth": ["Sample Prospect Two (fake)", "package ready", "Plan the pipeline"],
                     "/ops": ["1Password", "example-boutique"],
                     "/memory": ["shopify-is-the-inventory-truth", "inventory"],
                     "/ledger?space=growth": ["Plan the pipeline"]}
            for path, wants in pages.items():
                page = urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5).read().decode()
                for want in wants:
                    self.assertIn(want, page, path)
            empty = urllib.request.urlopen(f"http://127.0.0.1:{port}/ledger?space=ops", timeout=5).read().decode()
            self.assertNotIn("Plan the pipeline", empty)
            for bad in ("/client/..%2f..%2fetc", "/client/_template", "/memory/..%2fREADME.md", "/nope"):
                with self.assertRaises(urllib.error.HTTPError, msg=bad) as caught:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}{bad}", timeout=5)
                caught.exception.close()
            api = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5).read())
            self.assertIn("inventory", api)
        finally:
            proc.terminate()
            proc.wait(5)


if __name__ == "__main__":
    unittest.main()
