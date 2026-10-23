"""Tests for claude-move against a fake session tree. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "claude-move"
NOW = int(time.time() * 1000)


def write(p, **d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


class ClaudeMove(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.root = self.home / "sessions"
        self.a = self.root / "aaaa1111" / "org1"
        self.b = self.root / "bbbb2222" / "org2"
        self.b.mkdir(parents=True)
        write(self.a / "local_1.json", sessionId="local_1", title="recent", lastActivityAt=NOW - 1000)
        write(self.a / "local_2.json", sessionId="local_2", title="old", lastActivityAt=NOW - 10 * 86400 * 1000)
        write(self.a / "local_3.json", sessionId="local_3", title="archived", lastActivityAt=NOW, isArchived=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        env = dict(os.environ, CLAUDE_MOVE_HOME=str(self.home), CLAUDE_MOVE_ROOT=str(self.root),
                   CLAUDE_MOVE_LANG="en", CLAUDE_MOVE_SKIP_APP_CHECK="1")
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env)

    def test_list_marks_most_recent(self):
        r = self.run_tool("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("aaaa1111", r.stdout)
        self.assertIn("most recent", r.stdout)
        self.assertIn("1 empty folder", r.stdout)

    def test_dry_run_changes_nothing(self):
        r = self.run_tool("to", "bbbb", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("recent", r.stdout)
        self.assertEqual(list(self.b.iterdir()), [])

    def test_moves_recent_live_only_and_backs_up(self):
        r = self.run_tool("to", "bbbb")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in self.b.iterdir()), ["local_1.json"])
        self.assertTrue(any((self.root.parent / "claude-code-sessions-backups").iterdir()))
        self.assertTrue((self.a / "local_1.json").exists(), "source must never be deleted")

    def test_all_includes_old_but_not_archived(self):
        self.run_tool("to", "bbbb", "--all")
        self.assertEqual(sorted(p.name for p in self.b.iterdir()), ["local_1.json", "local_2.json"])

    def test_newer_target_is_kept(self):
        write(self.b / "local_1.json", sessionId="local_1", title="newer there", lastActivityAt=NOW)
        r = self.run_tool("to", "bbbb")
        self.assertIn("skip", r.stdout)
        self.assertEqual(json.loads((self.b / "local_1.json").read_text())["title"], "newer there")

    def test_archived_target_copy_is_replaced(self):
        write(self.b / "local_1.json", sessionId="local_1", title="stale", lastActivityAt=NOW, isArchived=True)
        self.run_tool("to", "bbbb")
        self.assertEqual(json.loads((self.b / "local_1.json").read_text())["title"], "recent")

    def test_labels(self):
        self.assertEqual(self.run_tool("name", "bbbb", "work").returncode, 0)
        r = self.run_tool("to", "work", "--dry-run")
        self.assertIn("to work", r.stdout)

    def test_unknown_account(self):
        r = self.run_tool("to", "zzzz")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No account matches", r.stderr)


if __name__ == "__main__":
    unittest.main()
