"""scripts/new-client builds a client space from the templates, in a temp copy of the repository."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class NewClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "work", "memory", "__pycache__"))
        index = self.repo / "clients" / "INDEX.md"
        if index.exists():
            index.unlink()
        shutil.copy(self.repo / "clients" / "INDEX.example.md", index)

    def tearDown(self):
        self.tmp.cleanup()

    def run_new(self, *args):
        return subprocess.run([sys.executable, str(self.repo / "scripts" / "new-client"), *args],
                              capture_output=True, text=True)

    def test_makes_every_folder_and_fills_the_template(self):
        out = self.run_new("willow-and-pine", "--name", "Willow and Pine", "--holding-replies", "yes")
        self.assertEqual(out.returncode, 0, out.stderr)
        c = self.repo / "clients" / "willow-and-pine"
        for rel in ("profile.md", "onboarding.md", "CLAUDE.md", "kb/brand-voice.md", "kb/faq.md", "kb/policies.md",
                    "kb/knowledge-base.md", "kb/questions.md", "inbox-agent/prompt.md", "ads", "reports",
                    "approvals", "notes"):
            self.assertTrue((c / rel).exists(), rel)
        profile = (c / "profile.md").read_text()
        self.assertIn("name: Willow and Pine", profile)
        self.assertIn("slug: willow-and-pine", profile)
        self.assertIn("holding_replies: yes", profile)
        for rel in ("profile.md", "CLAUDE.md", "inbox-agent/prompt.md", "kb/questions.md", "onboarding.md"):
            text = (c / rel).read_text()
            for key in ("CLIENT_NAME", "SLUG", "START_DATE", "HOLDING_REPLIES"):
                self.assertNotIn("{{" + key + "}}", text, rel)
        prompt = (c / "inbox-agent" / "prompt.md").read_text()
        self.assertIn("clients/willow-and-pine/kb/brand-voice.md", prompt)
        self.assertIn("{{INBOX_ADDRESS}}", prompt)  # left for onboarding to fill
        inv = self.repo / "inventory" / "clients" / "willow-and-pine"
        self.assertTrue((inv / "preference.json").is_file())
        self.assertTrue((inv / "last").is_dir() and (inv / "sheets").is_dir())
        self.assertIn('"client": "willow-and-pine"', (self.repo / "inventory" / "rules" / "willow-and-pine.json").read_text())
        self.assertIn("| [Willow and Pine](willow-and-pine/profile.md) |", (self.repo / "clients" / "INDEX.md").read_text())
        claude = (c / "CLAUDE.md").read_text()
        self.assertIn("../../memory/MEMORY.md", claude)
        self.assertIn("ledger view --client willow-and-pine", claude)
        self.assertIn("No memory is tagged `client: willow-and-pine` yet", claude)  # memory-sync ran

    def test_refuses_to_overwrite_and_bad_slugs(self):
        self.assertEqual(self.run_new("willow-and-pine").returncode, 0)
        profile = self.repo / "clients" / "willow-and-pine" / "profile.md"
        profile.write_text("edited by a person\n")
        again = self.run_new("willow-and-pine")
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(profile.read_text(), "edited by a person\n")
        for bad in ("Willow", "_template", "a", "../x", "willow pine"):
            self.assertNotEqual(self.run_new(bad).returncode, 0, bad)
        self.assertNotEqual(self.run_new("example-boutique").returncode, 0)


if __name__ == "__main__":
    unittest.main()
