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
                   CLAUDE_MOVE_DESKTOP_CONFIG=str(self.home / "desk"),
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

    def test_only_picks_by_title_even_if_old(self):
        r = self.run_tool("to", "bbbb", "--only", "old")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in self.b.iterdir()), ["local_2.json"])

    def test_lists_artifacts_that_stay_behind(self):
        write(self.a / "local_1.json", sessionId="local_1", title="recent", lastActivityAt=NOW,
              publishedArtifacts=[{"url": "https://claude.ai/artifact/XYZ", "title": "Canvas"}])
        r = self.run_tool("to", "bbbb", "--dry-run")
        self.assertIn("stay with the account that created them", r.stdout)
        self.assertIn("https://claude.ai/artifact/XYZ", r.stdout)

    def test_undo_restores_replaced_and_removes_added(self):
        write(self.b / "local_9.json", sessionId="local_9", title="theirs", lastActivityAt=NOW - 5)
        write(self.a / "local_9.json", sessionId="local_9", title="mine", lastActivityAt=NOW)
        self.run_tool("to", "bbbb")
        self.assertEqual(json.loads((self.b / "local_9.json").read_text())["title"], "mine")
        self.assertTrue((self.b / "local_1.json").exists())
        r = self.run_tool("undo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((self.b / "local_9.json").read_text())["title"], "theirs")
        self.assertFalse((self.b / "local_1.json").exists())
        self.assertTrue((self.a / "local_1.json").exists(), "source untouched")
        self.assertIn("No backups", self.run_tool("undo").stderr, "the same move is not undone twice")

    def test_undo_list(self):
        self.run_tool("to", "bbbb")
        r = self.run_tool("undo", "--list")
        self.assertIn("into bbbb2222", r.stdout)

    def test_import_cli_copies_once_with_side_folder(self):
        other = self.home / "other"
        proj = other / "projects" / "-work-app"
        (proj / "s1" / "subagents").mkdir(parents=True)
        (proj / "s1.jsonl").write_text(json.dumps({"type": "user", "message": {"content": "hello there"}}) + "\n")
        r = self.run_tool("import-cli", "--config", str(other), "--project=-work-app")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hello there", r.stdout)
        dest = self.home / "desk" / "projects" / "-work-app"
        self.assertTrue((dest / "s1.jsonl").exists())
        self.assertTrue((dest / "s1" / "subagents").is_dir())
        (dest / "s1.jsonl").write_text("kept")
        r = self.run_tool("import-cli", "--config", str(other), "--project=-work-app")
        self.assertIn("already there", r.stdout)
        self.assertEqual((dest / "s1.jsonl").read_text(), "kept", "never overwrites")

    def test_import_cli_project_path_is_encoded(self):
        other = self.home / "other"
        proj = other / "projects" / "-tmp-my-app"
        proj.mkdir(parents=True)
        (proj / "s2.jsonl").write_text("{}\n")
        r = self.run_tool("import-cli", "--config", str(other), "--project", "/tmp/my.app", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("s2", r.stdout)


if __name__ == "__main__":
    unittest.main()
