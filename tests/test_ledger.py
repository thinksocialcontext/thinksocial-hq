"""Tests for scripts/ledger. Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "scripts" / "ledger"
SPACES = [("hq", ""), ("clients", "clients"), ("inventory", "inventory"), ("team", "team"), ("growth", "growth"),
          ("growth-research", "growth/research"), ("ops", "ops")]


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "HQ_LEDGER_DIR": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def run_ledger(self, *args, ok=True):
        out = subprocess.run([sys.executable, str(LEDGER), *args], capture_output=True, text=True, env=self.env)
        if ok:
            self.assertEqual(out.returncode, 0, out.stderr)
        return out

    def start(self, key="k1", title="Draft holiday batch"):
        return self.run_ledger("start", "--key", key, "--agent", "ads", "--title", title).stdout.strip()

    def test_full_lifecycle(self):
        brief = Path(self.tmp.name) / "brief.md"
        brief.write_text("Goal: six stills.\n")
        job = self.run_ledger("start", "--key", "b1", "--agent", "ads", "--title", "Holiday batch",
                              "--brief", str(brief), "--project", "ads").stdout.strip()
        self.assertRegex(job, r"^job_[0-9a-f]{12}$")
        self.run_ledger("event", job, "--state", "running", "--note", "Building stills.")
        self.run_ledger("artifact", job, "ads/batches/x/sheet.jpg", "--note", "contact sheet")
        self.run_ledger("event", job, "--state", "waiting_approval", "--note", "Sent to owner.")
        self.run_ledger("finish", job, "--status", "done", "--outcome", "Six stills approved.")
        data = json.loads(self.run_ledger("show", job, "--json").stdout)
        self.assertEqual(data["status"], "done")
        self.assertEqual(len(data["artifacts"]), 1)
        self.assertEqual([e["state"] for e in data["events"]],
                         ["dispatched", "running", "waiting_approval", "done"])
        md = (Path(self.tmp.name) / data["file"]).read_text()
        self.assertIn("# Holiday batch", md)
        self.assertIn("Goal: six stills.", md)
        self.assertIn("Six stills approved.", md)
        journal = (Path(self.tmp.name) / ".ledger" / "events.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(l)["type"] for l in journal], ["start", "event", "artifact", "event", "finish"])

    def test_start_is_idempotent(self):
        self.assertEqual(self.start("same"), self.start("same"))
        self.assertEqual(len(json.loads(self.run_ledger("recent", "--json").stdout)), 1)

    def test_artifact_deduplicates(self):
        job = self.start()
        self.run_ledger("artifact", job, "a.png")
        self.run_ledger("artifact", job, "a.png")
        self.assertEqual(len(json.loads(self.run_ledger("show", job, "--json").stdout)["artifacts"]), 1)

    def test_finished_job_is_closed(self):
        job = self.start()
        self.run_ledger("finish", job, "--status", "failed", "--outcome", "Rate limited.")
        out = self.run_ledger("event", job, "--state", "running", "--note", "again", ok=False)
        self.assertNotEqual(out.returncode, 0)
        # repeating the identical finish is harmless
        self.run_ledger("finish", job, "--status", "failed", "--outcome", "Rate limited.")
        out = self.run_ledger("finish", job, "--status", "done", "--outcome", "x", ok=False)
        self.assertNotEqual(out.returncode, 0)

    def test_rejects_bad_states(self):
        job = self.start()
        self.assertNotEqual(self.run_ledger("event", job, "--state", "done", "--note", "x", ok=False).returncode, 0)
        self.assertNotEqual(self.run_ledger("finish", job, "--status", "running", "--outcome", "x", ok=False).returncode, 0)
        self.assertNotEqual(self.run_ledger("event", "job_nothere00000", "--state", "running", "--note", "x",
                                            ok=False).returncode, 0)

    def test_refuses_secrets(self):
        job = self.start()
        for note in ("token: abc123", "key shpat_" + "0123456789abcdef", "password=hunter2"):
            out = self.run_ledger("event", job, "--state", "running", "--note", note, ok=False)
            self.assertNotEqual(out.returncode, 0, note)
            self.assertIn("credential", out.stderr)

    def run_in(self, folder, *args, ok=True):
        out = subprocess.run([sys.executable, str(LEDGER), *args], capture_output=True, text=True, env=self.env,
                             cwd=str(ROOT / folder))
        if ok:
            self.assertEqual(out.returncode, 0, out.stderr)
        return out

    def test_space_and_client_come_from_the_folder(self):
        cases = {"": ("hq", ""), "inventory": ("inventory", ""), "inventory/tools": ("inventory", ""),
                 "growth/research": ("growth-research", ""), "clients": ("clients", ""),
                 "clients/example-boutique": ("clients", "example-boutique"),
                 "clients/example-boutique/kb": ("clients", "example-boutique"),
                 "inventory/clients/example-boutique": ("inventory", "example-boutique"),
                 "team": ("team", ""), "ops": ("ops", "")}
        for i, (folder, (space, client)) in enumerate(cases.items()):
            job = self.run_in(folder, "start", "--key", f"f{i}", "--agent", "x", "--title", f"From {folder or 'root'}").stdout.strip()
            data = json.loads(self.run_ledger("show", job, "--json").stdout)
            self.assertEqual((data["space"], data["client"]), (space, client), folder)
            self.assertEqual(data["folder"], dict(SPACES)[space] or ".")

    def test_flags_override_and_filters(self):
        a = self.run_ledger("start", "--key", "a", "--agent", "clients", "--title", "Onboard", "--space", "clients",
                            "--client", "example-boutique").stdout.strip()
        self.run_ledger("start", "--key", "b", "--agent", "inventory", "--title", "Invoices", "--space", "inventory")
        only = json.loads(self.run_ledger("recent", "--client", "example-boutique", "--json").stdout)
        self.assertEqual([j["id"] for j in only], [a])
        self.assertEqual(only[0]["space"], "clients")
        inv = json.loads(self.run_ledger("recent", "--space", "inventory", "--json").stdout)
        self.assertEqual([j["title"] for j in inv], ["Invoices"])
        view = self.run_ledger("view", "--client", "example-boutique").stdout
        self.assertIn("| Onboard |", view)
        self.assertNotIn("Invoices", view)
        self.assertIn("space: clients", self.run_ledger("show", a).stdout)
        out = self.run_ledger("start", "--key", "c", "--agent", "x", "--title", "t", "--space", "sales", ok=False)
        self.assertNotEqual(out.returncode, 0)
        out = self.run_ledger("start", "--key", "d", "--agent", "x", "--title", "t", "--client", "Bad Slug", ok=False)
        self.assertNotEqual(out.returncode, 0)

    def test_recent_orders_newest_first(self):
        a = self.start("a", "First")
        b = self.start("b", "Second")
        self.run_ledger("event", a, "--state", "running", "--note", "touched")
        ids = [j["id"] for j in json.loads(self.run_ledger("recent", "--json").stdout)]
        self.assertEqual(ids[0], a)
        self.assertIn(b, ids)


if __name__ == "__main__":
    unittest.main()
