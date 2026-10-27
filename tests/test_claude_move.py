"""Tests for claude-move against a fake session tree. Run: python3 -m unittest discover tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path

FIVE_H = 5 * 3600
TOOL = Path(__file__).resolve().parents[1] / "claude-move"
NOW = int(time.time() * 1000)
WIN = sys.platform == "win32"
os.environ["PYTHONIOENCODING"] = "utf-8"  # the tool prints "·" and Chinese; read it the same everywhere
SCRIPT = ".cmd" if WIN else ".command"  # what the terminal buttons write


def py_cmd(code, *args):
    """A shell command running Python code, quoted so that both sh and cmd.exe read it the same way."""
    return " ".join([f'"{sys.executable}"', "-c", f'"{code}"'] + [f'"{a}"' for a in args])


NOOP = py_cmd("pass")
touch_cmd = lambda p: py_cmd("import sys, pathlib; pathlib.Path(sys.argv[1]).touch()", p)
append_cmd = lambda p: py_cmd("import sys; open(sys.argv[1], 'a', encoding='utf-8').write(sys.stdin.read())", p)


def stub(path, code):
    """A fake claude written in Python, behind a launcher the tool runs like an executable (a .cmd on Windows)."""
    src = path.with_suffix(".py")
    src.write_text("import json, os, sys, time, pathlib\nsys.stdout.reconfigure(encoding='utf-8')\n" + code, encoding="utf-8")
    if WIN:
        exe = path.with_suffix(".cmd")
        exe.write_text(f'@"{sys.executable}" "{src}" %*\r\n')
        return exe
    path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{src}" "$@"\n')
    path.chmod(0o755)
    return path


def load_tool(name="cm"):
    import importlib.machinery, importlib.util
    loader = importlib.machinery.SourceFileLoader(name, str(TOOL))
    spec = importlib.util.spec_from_loader(name, loader)
    cm = importlib.util.module_from_spec(spec)
    loader.exec_module(cm)
    return cm


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
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, encoding="utf-8", env=env)

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
        self.assertEqual(json.loads((self.b / "local_1.json").read_text(encoding="utf-8"))["title"], "newer there")

    def test_archived_target_copy_is_replaced(self):
        write(self.b / "local_1.json", sessionId="local_1", title="stale", lastActivityAt=NOW, isArchived=True)
        self.run_tool("to", "bbbb")
        self.assertEqual(json.loads((self.b / "local_1.json").read_text(encoding="utf-8"))["title"], "recent")

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
        self.assertEqual(json.loads((self.b / "local_9.json").read_text(encoding="utf-8"))["title"], "mine")
        self.assertTrue((self.b / "local_1.json").exists())
        r = self.run_tool("undo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((self.b / "local_9.json").read_text(encoding="utf-8"))["title"], "theirs")
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
        self.assertEqual((dest / "s1.jsonl").read_text(encoding="utf-8"), "kept", "never overwrites")

    def test_import_cli_project_path_is_encoded(self):
        other = self.home / "other"
        proj = other / "projects" / "-tmp-my-app"
        proj.mkdir(parents=True)
        (proj / "s2.jsonl").write_text("{}\n")
        if WIN:  # an absolute path there starts with the drive: C:\\tmp\\my.app is C--tmp-my-app
            proj.rename(other / "projects" / "".join(c if c.isalnum() else "-" for c in os.path.abspath("/tmp/my.app")))
        r = self.run_tool("import-cli", "--config", str(other), "--project", "/tmp/my.app", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("s2", r.stdout)


if __name__ == "__main__":
    unittest.main()


def iso(sec):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(sec))


def reply(sid, sec, msg_id, model="claude-opus-5-5", out=1000, entry="claude-desktop"):
    return {"type": "assistant", "sessionId": sid, "timestamp": iso(sec), "entrypoint": entry, "requestId": "r" + msg_id,
            "message": {"id": msg_id, "model": model, "usage": {"input_tokens": 0, "output_tokens": out}}}


def limit_hit(sid, sec, kind, resets, entry="claude-desktop"):
    return {"type": "assistant", "sessionId": sid, "timestamp": iso(sec), "entrypoint": entry, "apiError": "usage_limit_reached",
            "apiErrorParams": {"rate_limit_info": {"status": "rejected", "resetsAt": resets, "rateLimitType": kind}},
            "message": {"id": "err" + str(sec), "model": "<synthetic>", "usage": {"input_tokens": 0, "output_tokens": 0}}}


class Usage(unittest.TestCase):
    """usage attributes desktop replies by who was signed in (from the app log), CLI replies by config folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.root = self.home / "sessions"
        self.desk = self.home / "desk"
        self.now = time.time()
        a, b = "aaaaaaaa-0000-0000-0000-000000000001", "bbbbbbbb-0000-0000-0000-000000000002"
        self.a, self.b = a, b
        # the same session sits in both lists, as after a move
        for acct in (a, b):
            write(self.root / acct / "org" / "local_1.json", sessionId="local_1", cliSessionId="s1",
                  lastActivityAt=int(self.now * 1000))
        switch = self.now - 3600
        self.log = log = self.home / ("logs" if WIN else "Library/Logs/Claude") / "main.log"
        log.parent.mkdir(parents=True)
        stamp = lambda s: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s))
        log.write_text(f"{stamp(self.now - 86400)} [info] [oauth-v2] lookup orgId=x cacheKey=acct:{a}|y:x:https:/\n"
                       f"{stamp(switch)} [info] [oauth-v2] lookup orgId=x cacheKey=acct:{b}|y:x:https:/\n")
        lines = [reply("s1", self.now - 7200, "m1"), reply("s1", self.now - 7200, "m1"),  # duplicate block
                 limit_hit("s1", self.now - 7000, "five_hour", int(self.now + 3600)),
                 reply("s1", self.now - 600, "m2", out=2000),
                 reply("s9", self.now - 300, "m3", out=100000, entry="cli")]
        t = self.desk / "projects" / "-p" / "s1.jsonl"
        t.parent.mkdir(parents=True)
        t.write_text("".join(json.dumps(x) + "\n" for x in lines))
        self.transcript = t

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, stdin=None, **env_extra):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(CLAUDE_MOVE_HOME=str(self.home), CLAUDE_MOVE_ROOT=str(self.root), CLAUDE_MOVE_DESKTOP_CONFIG=str(self.desk),
                   CLAUDE_MOVE_LANG="en", CLAUDE_MOVE_NOTIFY_CMD=NOOP)
        env.update(env_extra)
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, encoding="utf-8", env=env,
                              input=stdin)

    def test_attribution_cooling_and_pick(self):
        self.run_tool("name", "aaaa", "first")
        self.run_tool("name", "bbbb", "second")
        r = self.run_tool("usage")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = {ln.split()[0]: ln for ln in r.stdout.splitlines() if ln.split()}
        # m1 ($0.125, once despite the duplicate) and the limit hit happened while "first" was signed in
        self.assertIn("cooling", lines["first"])
        self.assertIn("5-hour limit used up", lines["first"])
        self.assertIn("available", lines["second"])
        self.assertIn("5h $0", lines["first"])
        self.assertIn("$0 at API prices", lines["first"])
        self.assertIn("CLI, account unknown", r.stdout)
        self.assertIn("switch to: second", r.stdout)

    def test_cache_is_incremental(self):
        self.run_tool("usage")
        with open(self.transcript, "a") as fh:
            fh.write(json.dumps(reply("s1", self.now - 60, "m4", out=200000)) + "\n")
        r = self.run_tool("usage")
        line = next(ln for ln in r.stdout.splitlines() if ln.startswith("bbbbbbbb"))
        self.assertIn("5h $5", line)  # 2000 + 200000 output tokens at opus prices = $5.05

    def test_html_panel(self):
        r = self.run_tool("usage", "--html", "--no-open")
        self.assertEqual(r.returncode, 0, r.stderr)
        page = (self.home / ".config/claude-move/usage.html").read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", page)
        self.assertIn("prefers-color-scheme:dark", page)

    def test_heatmap_by_day_and_project(self):
        import re
        cm = load_tool("cmh")
        tree = cm.project_dir_name("/u/code/shop/.claude/worktrees/brave-x1")
        self.assertEqual(cm.project_of(tree, "/u/code/shop/.claude/worktrees/brave-x1/src"), "shop")  # a worktree is its repo
        self.assertEqual(cm.project_of(cm.project_dir_name("/u/code/shop"), "/u/code/shop/tests"), "shop")  # not the subfolder
        self.assertIsNone(cm.project_of(tree, "/tmp/scratch"))
        r = self.run_tool("usage", "--html", "--no-open")
        self.assertEqual(r.returncode, 0, r.stderr)
        page = (self.home / ".config/claude-move/usage.html").read_text(encoding="utf-8")
        heat = json.loads(re.search(r"const D = (\{.*?\}), S = D\.T;", page, re.S).group(1))["heat"]
        self.assertEqual(len(heat["proj"]), 182)
        self.assertIn("", heat["cal"])  # the CLI reply no account could be matched to
        recent = heat["proj"][-1] or heat["proj"][-2]
        self.assertEqual(list(recent), ["p"])  # no cwd recorded: named after its projects/ folder
        self.assertGreater(sum(sum(v) for v in heat["cal"].values()), 2)

    def test_menu_bar(self):
        lim = self.home / ".config/claude-move/limits.json"
        lim.parent.mkdir(parents=True, exist_ok=True)
        lim.write_text(json.dumps({self.b: {"at": self.now, "rows": [
            {"kind": "weekly_all", "percent": 96, "resets_at": self.now + 86400},
            {"kind": "session", "percent": 10, "resets_at": self.now - 60}]}}))
        lines = self.run_tool("bar").stdout.splitlines()
        self.assertEqual(lines[0], "● 96% | color=#e8352a")  # the account the app is signed into, red past 95
        self.assertTrue(lines[2].startswith("● bbbbbbbb  week 96% |"), lines[2])
        self.assertNotIn("5h", lines[2])  # a window that has reset since is left out
        if not WIN:
            d = self.home / "plugins"
            self.run_tool("bar", "install", "--dir", str(d))
            self.assertTrue(os.access(d / "claude-move.1m.sh", os.X_OK))
            self.run_tool("bar", "uninstall", "--dir", str(d))
            self.assertFalse((d / "claude-move.1m.sh").exists())

    def test_week_summary_once(self):
        from datetime import date, datetime, timedelta
        monday = date.today() - timedelta(days=date.today().weekday() + 7)
        wed = datetime(monday.year, monday.month, monday.day, 12) + timedelta(days=2)
        f = self.desk / "projects" / "-q" / "s7.jsonl"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(reply("s7", wed.timestamp(), "m7", out=100000, entry="cli")) + "\n")
        out = self.home / "notes"
        for _ in range(2):
            self.run_tool("usage", CLAUDE_MOVE_NOTIFY_CMD=append_cmd(out))
        sent = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("Last week")]
        self.assertEqual(len(sent), 1)
        self.assertIn("$2", sent[0])
        self.assertIn("busiest on Wed", sent[0])

    def test_watch_records_official_limits_and_restores_old_status_line(self):
        cfg = self.home / "cli"
        cfg.mkdir()
        (cfg / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        (cfg / "settings.json").write_text(json.dumps({"theme": "dark", "statusLine": {"type": "command", "command": "echo old"}}))
        r = self.run_tool("watch", "install", CLAUDE_CONFIG_DIR=str(cfg))
        self.assertEqual(r.returncode, 0, r.stderr)
        cmd = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))["statusLine"]["command"]
        self.assertIn("watch record", cmd)
        payload = json.dumps({"rate_limits": {"five_hour": {"used_percentage": 23.5, "resets_at": 1},
                                              "seven_day": {"used_percentage": 41.2, "resets_at": 2}}})
        r = self.run_tool("watch", "record", stdin=payload, CLAUDE_CONFIG_DIR=str(cfg))
        self.assertEqual(r.stdout.strip(), "old")  # the previous status line still shows
        saved = json.loads((self.home / ".config/claude-move/limits.json").read_text(encoding="utf-8"))
        self.assertEqual([(r["kind"], r["percent"]) for r in saved[self.b]["rows"]], [("weekly_all", 41.2), ("session", 23.5)])
        r = self.run_tool("usage")
        self.assertIn("official: week 41% · 5h 24%", r.stdout)
        self.run_tool("watch", "uninstall", CLAUDE_CONFIG_DIR=str(cfg))
        s = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(s["statusLine"]["command"], "echo old")
        self.assertEqual(s["theme"], "dark")

    def test_watch_record_never_fails(self):
        r = self.run_tool("watch", "record", stdin="not json")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_refresh_reads_official_usage_report(self):
        # one signed-in CLI folder per account; a stub `claude` answers /usage the way the CLI's stream-json does
        good, bad = self.home / ".claude-second", self.home / ".claude-old"
        for c, acct in ((good, self.b), (bad, self.a)):
            c.mkdir()
            (c / ".claude.json").write_text(json.dumps({"oauthAccount": {
                "accountUuid": acct, "organizationType": "claude_max", "organizationRateLimitTier": "default_claude_max_20x"}}))
        soon = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now + 7200))
        report = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "usage"}]},
                  "usage_report": {"session": {}, "rate_limits": {"limits": [
                      {"kind": "session", "group": "session", "percent": 100, "resets_at": soon, "severity": "error", "is_active": True},
                      {"kind": "weekly_all", "group": "weekly", "percent": 41, "resets_at": soon, "severity": "ok", "is_active": True},
                      {"kind": "weekly_scoped", "group": "weekly", "percent": 12, "resets_at": soon,
                       "scope": {"model": {"display_name": "Opus"}}, "severity": "ok", "is_active": True}]}}}
        exe = stub(self.home / "claude", f"print({json.dumps(report)!r} if os.environ.get('CLAUDE_CONFIG_DIR') == {str(good)!r} "
                                         "else 'Not logged in · Please run /login')\n")
        self.run_tool("name", "bbbb", "second")
        r = self.run_tool("usage", "--refresh", CLAUDE_MOVE_CLAUDE=str(exe))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("~/.claude-second: second  week 41% · week · Opus 12% · 5h 100%", r.stdout)
        self.assertIn("~/.claude-old: no plan usage", r.stdout)
        line = next(ln for ln in r.stdout.splitlines() if ln.startswith("second"))
        self.assertIn("Max 20x", line)
        self.assertIn("cooling", line)  # 5-hour meter at 100% counts as cooling until it resets
        self.assertIn("official: week 41% · week · Opus 12% · 5h 100%", line)
        page_r = self.run_tool("usage", "--html", "--no-open")
        self.assertEqual(page_r.returncode, 0, page_r.stderr)
        self.assertIn("week · Opus", (self.home / ".config/claude-move/usage.html").read_text(encoding="utf-8"))


    @unittest.skipIf(WIN, "checks the sh script; test_windows_scripts covers the .cmd one")
    def test_term_runs_claude_with_that_login(self):
        c = self.home / ".claude-second"
        c.mkdir()
        (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        (self.home / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))  # stale profile
        self.run_tool("name", "bbbb", "second")
        r = self.run_tool("term", "second", CLAUDE_MOVE_TERM_CMD=NOOP, CLAUDE_MOVE_CLAUDE="/opt/x/claude")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CLAUDE_CONFIG_DIR=~/.claude-second claude", r.stdout)
        script = self.home / ".config/claude-move/term/claude-second.command"
        self.assertEqual(script.read_text(encoding="utf-8").splitlines()[2:], [f"export CLAUDE_CONFIG_DIR={c}", "exec /opt/x/claude"])
        self.assertTrue(os.access(script, os.X_OK))
        # the CLI folder's newest transcript names the project (inside a worktree), so the window starts there
        proj = self.home / "app"
        (proj / ".claude/worktrees/w1").mkdir(parents=True)
        (c / "projects/-app").mkdir(parents=True)
        (c / "projects/-app/s.jsonl").write_text(json.dumps({"type": "summary"}) + "\n"
                                                + json.dumps({"type": "user", "cwd": str(proj / ".claude/worktrees/w1")}) + "\n")
        r = self.run_tool("term", "second", "--rc", CLAUDE_MOVE_TERM_CMD=NOOP, CLAUDE_MOVE_CLAUDE="/opt/x/claude")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--remote-control second", r.stdout)
        lines = (self.home / ".config/claude-move/term/claude-second-rc.command").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[1], f"cd {proj} 2>/dev/null || cd ~ || exit 1")
        self.assertEqual(lines[3], "exec /opt/x/claude --remote-control second")
        r = self.run_tool("term", "aaaa", CLAUDE_MOVE_TERM_CMD=NOOP)  # has sessions, but no CLI login
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No CLI login", r.stderr)


def usage_answer(session, week, opus, resets):
    """What `claude -p /usage --output-format stream-json` prints: its usage_report, with a per-model meter."""
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(resets))
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "usage"}]},
            "usage_report": {"session": {}, "rate_limits": {"limits": [
                {"kind": "session", "group": "session", "percent": session, "resets_at": at},
                {"kind": "weekly_all", "group": "weekly", "percent": week, "resets_at": at},
                {"kind": "weekly_scoped", "group": "weekly", "percent": opus, "resets_at": at,
                 "scope": {"model": {"id": "claude-opus-5", "display_name": "Opus"}}}]}}}


class Firstmate(unittest.TestCase):
    """quota-snapshot writes official numbers in quota-axi's cache format; fm-pin sets which login firstmate's crews use."""
    setUp, tearDown, run_tool = Usage.setUp, Usage.tearDown, Usage.run_tool

    def prepare(self):
        self.first, self.second = self.home / ".claude-first", self.home / ".claude-second"
        for c, acct in ((self.first, self.a), (self.second, self.b)):
            c.mkdir()
            (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": acct}}))
        self.fm = self.home / "firstmate"
        (self.fm / "bin").mkdir(parents=True)
        (self.fm / "bin/fm-spawn.sh").write_text("")
        self.answers = self.home / "answers.json"
        self.answer(self.second, usage_answer(12, 20, 33.5, self.now + 7200))
        # a fake claude: each config folder answers /usage with what answers.json says for it, or is signed out
        self.exe = stub(self.home / "claude", f"a = json.load(open({str(self.answers)!r})).get(os.environ.get('CLAUDE_CONFIG_DIR', ''))\n"
                                              "print(json.dumps(a) if a else 'Not logged in · Please run /login')\n")
        self.snap = self.home / ".cache/claude-move/quota-axi-snapshot.json"
        self.pin = self.fm / "config/claude-account"
        self.env = dict(CLAUDE_MOVE_CLAUDE=str(self.exe), CLAUDE_MOVE_FM_HOME=str(self.fm))
        self.run_tool("name", "aaaa", "first")
        self.run_tool("name", "bbbb", "second")

    def answer(self, cfg, a):
        cur = json.loads(self.answers.read_text(encoding="utf-8")) if self.answers.exists() else {}
        cur[str(cfg)] = a
        self.answers.write_text(json.dumps(cur), encoding="utf-8")

    def test_snapshot_format_follows_the_pin(self):
        self.prepare()
        r = self.run_tool("quota-snapshot", **self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fm-pin", r.stderr)  # nothing pinned and no --account: it does not guess
        self.assertFalse(self.snap.exists())
        r = self.run_tool("fm-pin", "second", **self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.pin.read_text(encoding="utf-8"), f"{self.second}\n")
        self.assertIn("Crews started from now on use it", r.stdout)
        at = json.loads((self.home / ".config/claude-move/limits.json").read_text(encoding="utf-8"))[self.b]["at"]
        iso = lambda s: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s))
        resets = iso(int(self.now + 7200))
        self.assertEqual(json.loads(self.snap.read_text(encoding="utf-8")), {"schemaVersion": 3, "providers": [{
            "provider": "claude", "label": "Claude", "source": "cli", "windows": [
                {"id": "five_hour", "label": "session", "kind": "session", "percentUsed": 12, "percentRemaining": 88,
                 "resetsAt": resets, "windowSeconds": 18000},
                {"id": "seven_day", "label": "week", "kind": "weekly", "percentUsed": 20, "percentRemaining": 80,
                 "resetsAt": resets, "windowSeconds": 604800},
                {"id": "model:claude-opus-5", "label": "Opus week", "kind": "model", "percentUsed": 33.5, "percentRemaining": 66.5,
                 "resetsAt": resets, "windowSeconds": 604800}],
            "state": {"status": "fresh", "stale": False, "sourcesTried": ["cli"], "refreshedAt": iso(at)}}]})
        if not WIN:
            self.assertEqual(self.snap.stat().st_mode & 0o777, 0o600)
        self.assertEqual(sorted(p.name for p in self.snap.parent.iterdir() if "quota-axi" in p.name), [self.snap.name])  # no temp left
        log = (self.home / ".cache/claude-move/quota-snapshot.log").read_text(encoding="utf-8")
        self.assertIn(f"second (bbbbbbbb) five_hour=12% seven_day=20% refreshedAt={iso(at)}", log)
        # a refresh follows the pin, and names its account and both numbers
        self.answer(self.second, usage_answer(15, 22, 34, self.now + 7200))
        r = self.run_tool("quota-snapshot", "--refresh", **self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("second · 5h 15% · week 22%", r.stdout)
        st = self.run_tool("quota-snapshot", "status", **self.env).stdout
        self.assertIn(f"firstmate's crews: second (~/.claude-second)", st)
        self.assertIn("Scheduled refresh: off", st)
        # fm-pin without an account lists the logins, the pinned one marked
        lines = self.run_tool("fm-pin", **self.env).stdout.splitlines()
        self.assertTrue(any(ln.startswith("* second") for ln in lines), lines)
        self.assertTrue(any(ln.startswith("  first") and "no official %" in ln for ln in lines), lines)

    def test_no_data_keeps_the_old_file(self):
        self.prepare()
        self.snap.parent.mkdir(parents=True)
        old = json.dumps({"schemaVersion": 3, "providers": [{"provider": "claude", "windows": [],
                                                              "state": {"refreshedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 60))}}]})
        self.snap.write_text(old, encoding="utf-8")
        r = self.run_tool("quota-snapshot", "--account", "first", "--refresh", **self.env)  # signed out: no plan usage
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("without plan usage", r.stdout)
        self.assertEqual(self.snap.read_text(encoding="utf-8"), old)
        # numbers an hour old while /usage keeps failing: firstmate gets no quota rather than old quota
        limits = self.home / ".config/claude-move/limits.json"
        limits.write_text(json.dumps({self.a: {"at": self.now - 7200, "src": "usage", "rows": [
            {"kind": "weekly_all", "percent": 50, "resets_at": self.now + 86400}]}}))
        self.snap.write_text(old.replace(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 60)),
                                         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 7200))), encoding="utf-8")
        r = self.run_tool("quota-snapshot", "--account", "first", "--refresh", **self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.snap.exists())
        self.assertTrue(self.snap.with_name(self.snap.name + ".stale").exists())
        self.assertIn("moved to", r.stdout)

    def test_fm_pin_checks_the_login(self):
        self.prepare()
        self.assertNotEqual(self.run_tool("fm-pin", "second", CLAUDE_MOVE_FM_HOME=str(self.home / "nope"), CLAUDE_MOVE_CLAUDE=str(self.exe)).returncode, 0)
        r = self.run_tool("fm-pin", "first", **self.env)  # signed out
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.pin.exists())
        self.answer(self.first, usage_answer(100, 40, 10, self.now + 3600))
        r = self.run_tool("fm-pin", "first", **self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cooling", r.stderr)
        self.assertFalse(self.pin.exists())
        self.assertEqual(self.run_tool("fm-pin", "first", "--force", **self.env).returncode, 0)
        self.assertEqual(self.pin.read_text(encoding="utf-8"), f"{self.first}\n")
        self.assertNotEqual(self.run_tool("fm-pin", "nobody", **self.env).returncode, 0)

    def test_status_line_keeps_the_snapshot_fresh_and_hints_a_switch(self):
        self.prepare()
        self.assertEqual(self.run_tool("fm-pin", "second", **self.env).returncode, 0)
        limits = self.home / ".config/claude-move/limits.json"
        cur = json.loads(limits.read_text(encoding="utf-8"))
        cur[self.a] = {"at": self.now, "src": "usage", "rows": [{"kind": "weekly_all", "percent": 30, "resets_at": self.now + 86400}]}
        limits.write_text(json.dumps(cur))
        conf = self.home / ".config/claude-move/snapshot.json"
        c = json.loads(conf.read_text(encoding="utf-8"))
        c["at"] = self.now - 120  # the last write was two minutes ago
        conf.write_text(json.dumps(c))
        sent = self.home / "sent"
        line = json.dumps({"rate_limits": {"five_hour": {"used_percentage": 91, "resets_at": int(self.now + 3600)},
                                           "seven_day": {"used_percentage": 25, "resets_at": int(self.now + 86400)}}})
        r = self.run_tool("watch", "record", stdin=line, CLAUDE_CONFIG_DIR=str(self.second), CLAUDE_MOVE_NOTIFY_CMD=append_cmd(sent), **self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        ws = {w["id"]: w["percentUsed"] for w in json.loads(self.snap.read_text(encoding="utf-8"))["providers"][0]["windows"]}
        self.assertEqual(ws, {"five_hour": 91, "seven_day": 25, "model:claude-opus-5": 33.5})  # per-model meter kept from /usage
        self.assertIn("first has 70% left this week: claude-move fm-pin first", sent.read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform == "darwin", "a launchd agent")
    def test_schedule_writes_a_launch_agent(self):
        import plistlib
        self.prepare()
        agents = self.home / "agents"
        env = dict(self.env, CLAUDE_MOVE_AGENTS=str(agents), CLAUDE_MOVE_LAUNCHCTL=NOOP)
        r = self.run_tool("quota-snapshot", "schedule", "--every", "5", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        p = plistlib.loads((agents / "com.github.layla-nl.claude-move.quota-snapshot.plist").read_bytes())
        self.assertEqual(p["ProgramArguments"][-2:], ["quota-snapshot", "--refresh"])
        self.assertEqual(p["StartInterval"], 300)
        self.assertEqual(p["EnvironmentVariables"]["CLAUDE_MOVE_CLAUDE"], str(self.exe))
        self.assertIn("every 5 min", self.run_tool("quota-snapshot", "status", **env).stdout)
        self.run_tool("quota-snapshot", "unschedule", **env)
        self.assertEqual(list(agents.iterdir()), [])

    def test_panel_crew_tool(self):
        self.prepare()
        Panel.start(self, **self.env)
        api = lambda name, body=None: json.loads(Panel.call(self, "/api/" + name, body)[1])
        page = Panel.call(self, f"/?t={self.token}", token=False)[1]
        self.assertIn("data-open=t-crew", page)
        self.assertNotIn('class="crewmark"', page)
        r = api("crew")
        self.assertTrue(r["found"])
        self.assertEqual({a["name"]: a["pinned"] for a in r["accounts"]}, {"first": False, "second": False})
        self.assertFalse(api("crew", {"do": "pin", "acct": self.a})["ok"])  # signed out
        self.assertEqual(Panel.call(self, "/api/crew", {"do": "pin", "acct": "nobody"})[0], 400)
        self.assertTrue(api("crew", {"do": "pin", "acct": self.b})["ok"])
        self.assertEqual(self.pin.read_text(encoding="utf-8"), f"{self.second}\n")
        self.assertTrue(api("crew", {"do": "snapshot"})["ok"])
        self.assertTrue(self.snap.exists())
        self.assertIn('class="crewmark"', Panel.call(self, f"/?t={self.token}", token=False)[1])


def said(kind, text, sec, **extra):
    content = text if kind == "user" and isinstance(text, (str, list)) else [{"type": "text", "text": text}]
    return dict({"type": kind, "timestamp": iso(sec), "cwd": extra.pop("cwd", ""), "message": {"role": kind, "content": content}}, **extra)


class Terminal(unittest.TestCase):
    """find searches what was said in every CLI login's transcripts; resume, ps and tmux work on terminal sessions."""
    setUp, tearDown, run_tool = Usage.setUp, Usage.tearDown, Usage.run_tool
    S1, S2 = "1111aaaa-0000-0000-0000-000000000001", "2222bbbb-0000-0000-0000-000000000002"

    def prepare(self):
        self.first, self.second = self.home / ".claude-first", self.home / ".claude-second"
        for c, acct in ((self.first, self.a), (self.second, self.b)):
            c.mkdir()
            (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": acct}}))
        self.run_tool("name", "aaaa", "first")
        self.run_tool("name", "bbbb", "second")
        self.proj = self.home / "proj"
        self.proj.mkdir()
        cwd = str(self.proj)
        self.t1 = self.first / "projects/-proj" / f"{self.S1}.jsonl"
        self.t1.parent.mkdir(parents=True)
        lines = [said("user", "Fix the 登录 page", self.now - 900, cwd=cwd),
                 said("assistant", "The login form now checks the password.", self.now - 890, cwd=cwd),
                 said("user", [{"type": "tool_result", "content": "toolword in a file"}], self.now - 880, cwd=cwd),
                 said("user", "metaword", self.now - 870, cwd=cwd, isMeta=True),
                 said("user", "<command-name>/clear</command-name> wrapword", self.now - 860, cwd=cwd),
                 {"type": "custom-title", "customTitle": "Login fixes", "sessionId": self.S1}]
        self.t1.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
        t2 = self.second / "projects/-proj" / f"{self.S2}.jsonl"
        t2.parent.mkdir(parents=True)
        t2.write_text(json.dumps(said("user", "Something unrelated", self.now - 100, cwd=cwd)) + "\n", encoding="utf-8")

    def tmux_stub(self, pane_pid):
        self.tlog = self.home / "tmux.log"
        return stub(self.home / "tmux", f"a = sys.argv[1:]\nopen({str(self.tlog)!r}, 'a').write(json.dumps(a) + '\\n')\n"
                    f"out = {{'list-panes': '{pane_pid}\\tw:1.0', 'list-windows': 'w:1\\t1\\t1\\t\\tzsh\\nw:3\\t1\\t0\\t\\tfm-crew',"
                    " 'list-sessions': 'w', 'list-clients': '100\\t/dev/ttys001', 'new-window': 'w:2'}\n"
                    "print(out.get(a[0], ''))\n")

    def tmux_calls(self):
        return [json.loads(x) for x in self.tlog.read_text(encoding="utf-8").splitlines()] if self.tlog.exists() else []

    def test_find_reads_what_was_said_and_resume_opens_it(self):
        self.prepare()
        r = self.run_tool("find", "登录", CLAUDE_MOVE_TMUX="0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Login fixes", r.stdout)
        self.assertIn("first", r.stdout)
        self.assertIn("claude-move resume 1111aaaa", r.stdout)
        self.assertIn("1 terminal sessions", r.stdout)
        self.assertIn("password", self.run_tool("find", "LOGIN", "form", CLAUDE_MOVE_TMUX="0").stdout)  # any case, all words
        for word in ("toolword", "metaword", "wrapword"):  # tool output and the CLI's own notes are not what was said
            self.assertIn("No terminal session", self.run_tool("find", word, CLAUDE_MOVE_TMUX="0").stdout)
        self.assertIn("No terminal session", self.run_tool("find", "login", "unrelated", CLAUDE_MOVE_TMUX="0").stdout)
        self.assertIn("No terminal session", self.run_tool("find", "50%_", CLAUDE_MOVE_TMUX="0").stdout)  # LIKE wildcards are literal
        # the index only reads what is new; a rewritten file is read again
        with open(self.t1, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(said("user", "newword later", self.now - 10, cwd=str(self.proj))) + "\n")
        self.assertIn("Login fixes", self.run_tool("find", "newword", CLAUDE_MOVE_TMUX="0").stdout)
        self.assertIn("unrelated", self.run_tool("find", "unrelated", "--account", "second", CLAUDE_MOVE_TMUX="0").stdout)
        self.assertIn("No terminal session", self.run_tool("find", "unrelated", "--account", "first", CLAUDE_MOVE_TMUX="0").stdout)
        self.assertEqual(oct(os.stat(self.home / ".cache/claude-move/search.db").st_mode & 0o777), "0o600") if not WIN else None

        env = dict(CLAUDE_MOVE_TERM_CMD=NOOP, CLAUDE_MOVE_CLAUDE="/opt/x/claude")
        r = self.run_tool("resume", "1111", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("as first", r.stdout)
        script = (self.home / f".config/claude-move/term/resume-1111aaaa{SCRIPT}").read_text(encoding="utf-8")
        self.assertIn(str(self.first), script)
        self.assertIn(f"--resume {self.S1}", script)
        self.assertIn(str(self.proj), script)
        # --to copies it to the other login first; the first keeps its own
        r = self.run_tool("resume", "1111", "--to", "second", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.second / "projects/-proj" / f"{self.S1}.jsonl").exists())
        self.assertTrue(self.t1.exists())
        self.assertIn(str(self.second), (self.home / f".config/claude-move/term/resume-1111aaaa{SCRIPT}").read_text(encoding="utf-8"))
        self.assertNotEqual(self.run_tool("resume", "9999", **env).returncode, 0)
        # a session that is running is not started twice
        write(self.first / "sessions" / f"{os.getpid()}.json", pid=os.getpid(), sessionId=self.S1, cwd=str(self.proj),
              status="busy", name="login work", startedAt=int(self.now * 1000))
        r = self.run_tool("resume", "1111", **env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already running", r.stderr)
        self.assertIn("running (pid", self.run_tool("find", "登录", CLAUDE_MOVE_TMUX="0").stdout)

    @unittest.skipIf(WIN, "tmux")
    def test_ps_and_tmux(self):
        self.prepare()
        write(self.first / "sessions" / f"{os.getpid()}.json", pid=os.getpid(), sessionId=self.S1, cwd=str(self.proj),
              status="busy", name="login work", startedAt=int(self.now * 1000))
        write(self.second / "sessions" / "999999.json", pid=999999, sessionId=self.S2, status="idle")  # ended
        (self.first / "sessions" / f"{os.getpid()}.abc.key").write_text("not read")
        tm = str(self.tmux_stub(os.getpid()))
        r = self.run_tool("ps", CLAUDE_MOVE_TMUX=tm)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 Claude Code sessions running, 1 busy", r.stdout)
        self.assertIn("w:1.0", r.stdout)
        self.assertIn("login work", r.stdout)
        rows = json.loads(self.run_tool("ps", "--json", CLAUDE_MOVE_TMUX=tm).stdout)
        self.assertEqual([(x["name"], x["status"], x["tmux"]) for x in rows], [("first", "busy", "w:1.0")])
        r = self.run_tool("ps", "--go", "1111", CLAUDE_MOVE_TMUX=tm)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(["switch-client", "-c", "/dev/ttys001", "-t", "w:1.0"], self.tmux_calls())
        self.assertNotEqual(self.run_tool("ps", "--go", "nope", CLAUDE_MOVE_TMUX=tm).returncode, 0)
        # windows nobody named get the account and session; firstmate's own names stay
        self.tlog.unlink()
        self.assertEqual(self.run_tool("tmux", "line", CLAUDE_MOVE_TMUX=tm).stdout.strip(), "first 1 ●1")
        calls = self.tmux_calls()
        self.assertIn(["rename-window", "-t", "w:1", "● first·login work"], calls)
        self.assertFalse([c for c in calls if "w:3" in c])
        self.run_tool("tmux", "menu", CLAUDE_MOVE_TMUX=tm)
        menu = [c for c in self.tmux_calls() if c[0] == "display-menu"][0]
        self.assertIn("switch-client -t w:1.0", menu)
        # term opens a tmux window when tmux is running
        r = self.run_tool("term", "first", CLAUDE_MOVE_TMUX=tm, CLAUDE_MOVE_CLAUDE="/opt/x/claude")
        self.assertIn("tmux window w:2", r.stdout)
        self.assertTrue([c for c in self.tmux_calls() if c[0] == "new-window" and "first" in c])
        # the ~/.tmux.conf block: shown, added after a backup, taken out again
        conf = self.home / ".tmux.conf"
        conf.write_text("set -g history-limit 5000\n", encoding="utf-8")
        self.assertIn("status-right", self.run_tool("tmux", "conf", CLAUDE_MOVE_TMUX=tm).stdout)
        self.assertEqual(conf.read_text(encoding="utf-8"), "set -g history-limit 5000\n")
        r = self.run_tool("tmux", "conf", "--install", CLAUDE_MOVE_TMUX=tm)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = conf.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("set -g history-limit 5000\n# >>> claude-move"))
        self.assertIn("tmux line", text)
        self.assertEqual(len(list((self.home / ".config/claude-move/backups").glob("tmux.conf-*"))), 1)
        self.assertIn("already has it", self.run_tool("tmux", "conf", "--install", CLAUDE_MOVE_TMUX=tm).stdout)
        self.run_tool("tmux", "conf", "--remove", CLAUDE_MOVE_TMUX=tm)
        self.assertEqual(conf.read_text(encoding="utf-8"), "set -g history-limit 5000\n")
        self.assertIn(["set-option", "-gu", "mouse"], self.tmux_calls())


class Plan(unittest.TestCase):
    def test_plan_names(self):
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader("cm", str(TOOL))
        spec = importlib.util.spec_from_loader("cm", loader)
        cm = importlib.util.module_from_spec(spec)
        loader.exec_module(cm)
        self.assertEqual(cm.plan_name({"organizationType": "claude_max", "organizationRateLimitTier": "default_claude_max_5x"}), "Max 5x")
        self.assertEqual(cm.plan_name({"organizationType": "claude_pro", "organizationRateLimitTier": "default_claude_pro"}), "Pro")
        self.assertEqual(cm.plan_name({}), "")


class Panel(unittest.TestCase):
    """panel: token-gated local server; the switch button checks who is signed in, then quits, moves, reopens."""
    setUp, tearDown, run_tool = Usage.setUp, Usage.tearDown, Usage.run_tool
    S1, S2 = Terminal.S1, Terminal.S2

    def start(self, *extra, **env_extra):
        import re
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(CLAUDE_MOVE_HOME=str(self.home), CLAUDE_MOVE_ROOT=str(self.root), CLAUDE_MOVE_DESKTOP_CONFIG=str(self.desk),
                   CLAUDE_MOVE_LANG="en", CLAUDE_MOVE_SKIP_APP_CHECK="1",
                   CLAUDE_MOVE_QUIT_CMD=touch_cmd(self.home / "quit"), CLAUDE_MOVE_OPEN_CMD=touch_cmd(self.home / "open"),
                   CLAUDE_MOVE_TERM_CMD=touch_cmd(self.home / "term"),
                   CLAUDE_MOVE_UPDATE_URL=(self.home / "rel.json").as_uri(), CLAUDE_MOVE_NOTIFY_CMD=NOOP)
        env.update(env_extra)
        self.proc = subprocess.Popen([sys.executable, str(TOOL), "panel", "--no-open", *extra], stdout=subprocess.PIPE, text=True,
                                     encoding="utf-8", env=env)
        self.addCleanup(lambda: (self.proc.kill(), self.proc.wait(), self.proc.stdout.close()))
        line = self.proc.stdout.readline()
        m = re.search(r"http://127\.0\.0\.1:(\d+)/\?t=(\S+)", line)
        self.port, self.token = int(m.group(1)), m.group(2)

    def call(self, path, body=None, token=True, host=None):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Token"] = self.token
        if host:
            headers["Host"] = host
        c.request("POST" if body is not None else "GET", path, json.dumps(body) if body is not None else None, headers)
        r = c.getresponse()
        return r.status, r.read().decode()

    def test_panel_switch_flow(self):
        # a third account the app is signed into now, with an empty list (just opened the Code tab)
        c = "cccccccc-0000-0000-0000-000000000003"
        (self.root / c / "org").mkdir(parents=True)
        log = self.log
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.now - 10))
        log.write_text(log.read_text(encoding="utf-8") + f"{stamp} [info] [oauth-v2] lookup orgId=x cacheKey=acct:{c}|y:x:https:/\n")
        self.start()
        self.assertEqual(self.call("/state", token=False)[0], 403)
        self.assertEqual(self.call("/state", host="evil.example:80")[0], 403)
        code, page = self.call(f"/?t={self.token}", token=False)
        self.assertEqual(code, 200)
        self.assertIn('id="go"', page)
        state = json.loads(self.call("/state")[1])
        self.assertEqual(state["signed"]["acct"], c)
        self.assertTrue(state["source"]["acct"] in (self.a, self.b))
        # refuses an account the app is not signed into
        r = json.loads(self.call("/switch", {"to": self.a})[1])
        self.assertFalse(r["ok"])
        self.assertFalse((self.home / "quit").exists())
        r = json.loads(self.call("/switch", {"to": c})[1])
        self.assertTrue(r["ok"], r["log"])
        self.assertTrue((self.home / "quit").exists() and (self.home / "open").exists())
        self.assertTrue((self.root / c / "org" / "local_1.json").exists())

    def test_panel_terminal_only_for_signed_in_cli(self):
        c = self.home / ".claude-second"
        c.mkdir()
        (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        self.start()
        page = self.call(f"/?t={self.token}", token=False)[1]
        self.assertIn(f'data-term="{self.b}" data-rc="1"', page)
        copy = (f"$env:CLAUDE_CONFIG_DIR=&#x27;{c}&#x27;; claude --remote-control &#x27;bbbbbbbb&#x27;" if WIN
                else "CLAUDE_CONFIG_DIR=~/.claude-second claude --remote-control bbbbbbbb")
        self.assertIn(f'data-copy="{copy}"', page)
        self.assertEqual(self.call("/terminal", {"acct": self.a})[0], 404)  # no CLI login for this one
        self.assertEqual(self.call("/terminal", {"acct": ""})[0], 404)
        self.assertFalse((self.home / "term").exists())
        self.assertEqual(self.call("/terminal", {"acct": self.b}, token=False)[0], 403)
        code, body = self.call("/terminal", {"acct": self.b})
        self.assertEqual(code, 200, body)
        self.assertTrue((self.home / "term").exists())
        self.assertIn(f"CLAUDE_CONFIG_DIR={c}", (self.home / f".config/claude-move/term/claude-second{SCRIPT}").read_text(encoding="utf-8"))
        self.assertEqual(self.call("/terminal", {"acct": self.b, "rc": True})[0], 200)
        self.assertIn("--remote-control bbbbbbbb", (self.home / f".config/claude-move/term/claude-second-rc{SCRIPT}").read_text(encoding="utf-8"))
        self.assertIn('id="auto"', page)
        self.assertEqual(self.call("/terminal", {"acct": self.b, "auto": True})[0], 200)
        auto = (self.home / f".config/claude-move/term/claude-second-auto{SCRIPT}").read_text(encoding="utf-8")
        self.assertIn(f"run --config {c} {self.b}", auto)

    def test_panel_tools(self):
        c = self.home / ".claude-second"
        c.mkdir()
        (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        sid = "0b7a6f3e-0000-4000-8000-000000000001"
        write(c / "projects/-p" / f"{sid}.jsonl", type="user", message={"content": "fix the login page"})
        (self.home / "rel.json").write_text(json.dumps({"tag_name": "v9.9.9", "html_url": "https://example.invalid/r"}))
        self.start()
        api = lambda path, body=None: json.loads(self.call("/api/" + path, body)[1])
        page = self.call(f"/?t={self.token}", token=False)[1]
        for needle in ('id="t-move"', 'id="t-undo"', 'id="t-doc"', f'data-rename="{self.a}"', f'data-login="{self.a}"',
                       f'data-rec="{self.b}" data-on="0"'):
            self.assertIn(needle, page)
        self.assertEqual({a["acct"] for a in api("accounts")["accounts"]}, {self.a, self.b})
        # names: checked and saved; unknown accounts refused
        self.assertTrue(api("name", {"acct": self.a, "label": "work"})["ok"])
        self.assertFalse(api("name", {"acct": self.a, "label": "x" * 40})["ok"])
        self.assertEqual(self.call("/api/name", {"acct": "nope", "label": "x"})[0], 400)
        self.assertEqual(json.loads((self.home / ".config/claude-move/accounts.json").read_text(encoding="utf-8"))[self.a], "work")
        # move: preview, then the ticked session only, then undo it
        self.assertEqual([s["id"] for s in api("sessions?acct=" + self.a)["sessions"]], ["local_1"])
        r = api("move", {"from": self.a, "to": self.b, "range": "all", "dry": True})
        self.assertIn("Dry run", r["log"])
        self.assertEqual(api("backups")["backups"], [])  # a preview writes nothing
        r = api("move", {"from": self.a, "to": self.b, "range": "pick", "only": ["local_1", "local_bogus"]})
        self.assertTrue(r["ok"], r["log"])
        backups = api("backups")["backups"]
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.call("/api/undo", {"name": "../etc"})[0], 400)
        self.assertTrue(api("undo", {"name": backups[0]["name"]})["ok"])
        self.assertTrue(api("backups")["backups"][0]["undone"])
        # status line recorder on and off in that login's own settings.json
        self.assertTrue(api("watch", {"acct": self.b, "on": True})["ok"])
        self.assertIn("watch record", json.loads((c / "settings.json").read_text(encoding="utf-8"))["statusLine"]["command"])
        api("watch", {"acct": self.b, "on": False})
        self.assertNotIn("statusLine", json.loads((c / "settings.json").read_text(encoding="utf-8")))
        self.assertEqual(self.call("/api/watch", {"acct": self.a, "on": True})[0], 400)  # no CLI login
        # add a CLI login: the official sign-in in a Terminal window; the new account is named once it shows up
        self.assertFalse(api("login", {"name": "a b"})["ok"])
        self.assertTrue(api("login", {"name": "new"})["ok"])
        self.assertIn("auth login --claudeai", (self.home / f".config/claude-move/term/login-claude-new{SCRIPT}").read_text(encoding="utf-8"))
        n = "dddddddd-0000-0000-0000-000000000004"
        (self.home / ".claude-new/.claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": n}}))
        self.call("/state")
        self.assertEqual(json.loads((self.home / ".config/claude-move/accounts.json").read_text(encoding="utf-8"))[n], "new")
        self.assertFalse(api("login", {"name": "new"})["ok"])  # already signed in
        # notifications
        self.assertFalse(api("notify", {"on": True, "levels": "80,200"})["ok"])
        self.assertTrue(api("notify", {"on": True, "levels": "95, 80"})["ok"])
        self.assertEqual(api("notify")["levels"], [80, 95])
        # CLI sessions into the desktop app's folder, once
        rows = api("cli-sessions?acct=" + self.b)["sessions"]
        self.assertEqual([(x["id"], x["title"], x["in_desk"]) for x in rows], [(sid, "fix the login page", False)])
        self.assertIn("Copied 1", api("import", {"acct": self.b, "ids": [sid, "../../x"]})["log"])
        self.assertTrue((self.desk / "projects/-p" / f"{sid}.jsonl").exists())
        self.assertIn("Copied 0", api("import", {"acct": self.b, "ids": [sid]})["log"])
        # runs, doctor, update
        write(self.home / ".config/claude-move/runs" / f"{sid}.json", sid=sid, pid=999999, cfg=str(c), acct=self.b,
              started=self.now, ended=None, switches=[{"at": self.now, "from": self.a, "to": self.b}])
        run = api("runs")["runs"][0]
        self.assertEqual((run["title"], run["running"], run["switches"][0]["from"]), ("fix the login page", False, "work"))
        self.assertTrue(any(i["fix"] for i in api("doctor")["items"]))
        up = api("update")
        self.assertTrue(up["newer"], up)
        self.assertIn("9.9.9", up["log"])
        self.assertEqual(self.call("/api/accounts", token=False)[0], 403)

    @unittest.skipUnless(shutil.which("node"), "needs node to parse the page script")
    def test_panel_search_sessions(self):
        write(self.root / self.a / "org" / "local_7.json", sessionId="local_7", title="Fix the 登录 page",
              lastActivityAt=int(self.now * 1000))
        self.start()
        code, out = self.call("/api/search?" + urllib.parse.urlencode({"q": "登录"}))
        self.assertEqual(code, 200)
        self.assertEqual([(x["acct"], x["id"]) for x in json.loads(out)["sessions"]], [(self.a, "local_7")])
        self.assertEqual(self.call("/api/search?q=")[0], 400)
        self.assertEqual(self.call("/api/search?q=" + "x" * 81)[0], 400)

    def test_panel_terminal_sessions(self):
        Terminal.prepare(self)
        write(self.first / "sessions" / f"{os.getpid()}.json", pid=os.getpid(), sessionId=self.S2, cwd=str(self.proj), status="idle")
        self.start()
        page = self.call(f"/?t={self.token}", token=False)[1]
        self.assertIn('id="live"', page)
        out = json.loads(self.call("/api/search?" + urllib.parse.urlencode({"q": "登录"}))[1])
        self.assertEqual([(x["sid"], x["name"], x["title"]) for x in out["cli"]], [(self.S1, "first", "Login fixes")])
        self.assertIn(f"claude --resume {self.S1}", out["cli"][0]["cmd"])
        live = json.loads(self.call("/api/live")[1])
        self.assertEqual([(x["sid"], x["status"]) for x in live["rows"]], [(self.S2, "idle")])
        self.assertEqual(self.call("/api/live", {"do": "show", "target": "x:1"})[0], 400)
        self.assertEqual(self.call("/api/resume", {"sid": "../../etc"})[0], 400)
        out = json.loads(self.call("/api/resume", {"sid": self.S1})[1])
        self.assertTrue(out["ok"], out)
        self.assertTrue((self.home / "term").exists())
        self.assertFalse(json.loads(self.call("/api/resume", {"sid": self.S2})[1])["ok"])  # it is running

    def test_demo_reads_nothing_and_does_nothing(self):
        self.start("--demo")
        page = self.call(f"/?t={self.token}", token=False)[1]
        self.assertIn('data-acct="demo-work"', page)
        self.assertNotIn(self.a, page)
        out = json.loads(self.call("/api/move", {"from": self.a, "to": self.b, "range": "all"})[1])
        self.assertFalse(out["ok"])
        self.assertFalse((self.home / ".config/claude-move/panel.json").exists())
        self.assertFalse((self.home / "quit").exists())

    def test_panel_accent_setting(self):
        self.start()
        self.assertEqual(self.call("/api/look", {"accent": 1.5})[0], 200)
        saved = json.loads((self.home / ".config/claude-move/look.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["accent"], 1.5)
        for bad in (5, -1, "1", True, None):
            self.assertEqual(self.call("/api/look", {"accent": bad})[0], 400)
        page = self.call(f"/?t={self.token}", token=False)[1]
        self.assertIn('id="accent" min="0" max="200" value="150"', page)
        self.assertEqual(self.call("/api/look", {"theme": "dark", "lang": "zh"})[0], 200)
        for bad in ({"theme": "pink"}, {"lang": "fr"}, {}):
            self.assertEqual(self.call("/api/look", bad)[0], 400)
        page = self.call(f"/?t={self.token}", token=False)[1]
        self.assertIn('<html lang="zh" data-theme="dark">', page)
        self.assertIn('data-to="en"', page)
        self.assertEqual(json.loads((self.home / ".config/claude-move/look.json").read_text(encoding="utf-8"))["accent"], 1.5)

    def test_panel_script_parses(self):
        import re
        self.start()
        page = self.call(f"/?t={self.token}", token=False)[1]
        js = self.home / "page.js"
        js.write_text(re.findall(r"<script>(.*?)</script>", page, re.S)[-1], encoding="utf-8")
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_usage_text_fallback(self):
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader("cm2", str(TOOL))
        spec = importlib.util.spec_from_loader("cm2", loader)
        cm = importlib.util.module_from_spec(spec)
        loader.exec_module(cm)
        # the structured report can come back with limits: null while the text still has the meters
        msg = {"type": "assistant", "usage_report": {"rate_limits": {"limits": None}},
               "message": {"content": [{"type": "text", "text": "Current session: 7% used · resets 3pm (UTC)\n"
                                        "Current week (all models): 96% used · resets Oct 27 at 10am (Asia/Singapore)\n"
                                        "Current week (Fable): 0% used"}]}}
        rows = cm.parse_usage_report(json.dumps(msg))
        self.assertEqual([(r["kind"], r["percent"], r["scope"]) for r in rows],
                         [("session", 7.0, None), ("weekly_all", 96.0, None), ("weekly_scoped", 0.0, "Fable")])
        self.assertEqual(time.gmtime(rows[0]["resets_at"]).tm_hour, 15)
        try:
            from zoneinfo import ZoneInfo
            zones = bool(ZoneInfo("Asia/Singapore"))
        except Exception:  # no zone database (Windows without tzdata): read as local time, the zone the CLI uses
            zones = False
        when = (time.gmtime if zones else time.localtime)(rows[1]["resets_at"])
        self.assertEqual(time.strftime("%m-%d %H:%M", when), "10-27 02:00" if zones else "10-27 10:00")


class PanelLifecycle(unittest.TestCase):
    setUp, tearDown = Usage.setUp, Usage.tearDown

    def env(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(CLAUDE_MOVE_HOME=str(self.home), CLAUDE_MOVE_ROOT=str(self.root), CLAUDE_MOVE_DESKTOP_CONFIG=str(self.desk),
                   CLAUDE_MOVE_LANG="en", CLAUDE_MOVE_SKIP_APP_CHECK="1")
        return env

    def test_second_launch_reuses_and_idle_stops(self):
        first = subprocess.Popen([sys.executable, str(TOOL), "panel", "--no-open", "--idle", "1"],
                                 stdout=subprocess.PIPE, text=True, env=self.env())
        self.addCleanup(lambda: (first.kill(), first.wait(), first.stdout.close()))
        url = first.stdout.readline().split()[3]
        second = subprocess.run([sys.executable, str(TOOL), "panel", "--no-open"], capture_output=True, text=True,
                                env=self.env(), timeout=30)
        self.assertIn(url, second.stdout)  # no second server
        self.assertEqual(first.wait(timeout=30), 0)  # nobody polls, so it stops after the idle limit
        self.assertFalse((self.home / ".config/claude-move/panel.json").exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS only")
    def test_app_bundle(self):
        r = subprocess.run([sys.executable, str(TOOL), "app", "install", "--dir", str(self.home / "Apps"), "--no-dock"],
                           capture_output=True, text=True, env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        app = self.home / "Apps" / "Claude Move.app"
        launch = (app / "Contents/Resources/launch.sh").read_text(encoding="utf-8")
        self.assertIn("panel --here --idle 1800", launch)
        self.assertTrue((app / "Contents/Resources/applet.icns").stat().st_size > 1000)
        self.assertFalse((app / "Contents/Resources/Assets.car").exists())
        v = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stderr)


class Run(unittest.TestCase):
    """run: at a usage limit the session is copied to the freest CLI login and resumed there; notify; doctor."""
    setUp, tearDown = Usage.setUp, Usage.tearDown
    run_tool = Usage.run_tool

    def logins(self):
        a_cfg, b_cfg = self.home / ".claude-first", self.home / ".claude-second"
        for c, acct in ((a_cfg, self.a), (b_cfg, self.b)):
            c.mkdir()
            (c / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": acct}}))
        self.run_tool("name", "aaaa", "first")
        self.run_tool("name", "bbbb", "second")
        return a_cfg, b_cfg

    def test_run_moves_session_at_limit_and_resumes(self):
        a_cfg, b_cfg = self.logins()
        soon = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now + 7200))
        report = {"type": "assistant", "usage_report": {"rate_limits": {"limits": [
            {"kind": "weekly_all", "percent": 41, "resets_at": soon}]}}}
        hit = limit_hit("x", self.now, "five_hour", int(self.now + 3600), entry="cli")
        argv = self.home / "argv"
        # the stub claude: /usage answers for both; in the first login it hits the limit and waits like the TUI does
        exe = stub(self.home / "claude", f"""
a = sys.argv[1:]
sid = next(a[i + 1] for i, x in enumerate(a[:-1]) if x in ("--session-id", "--resume")) if "-p" not in a else None
if sid is None:
    print({json.dumps(report)!r}); sys.exit(0)
d = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "-p"
d.mkdir(parents=True, exist_ok=True)
f = (d / (sid + ".jsonl")).open("a", encoding="utf-8")
if os.environ["CLAUDE_CONFIG_DIR"] == {str(a_cfg)!r}:
    f.write('{{"type":"user"}}\\n' + {json.dumps(hit)!r} + "\\n"); f.close(); time.sleep(30); sys.exit(0)
pathlib.Path({str(argv)!r}).write_text("\\n".join(a) + "\\n", encoding="utf-8")
f.write('{{"type":"user","b":1}}\\n'); f.close()
""")
        sent = self.home / "sent"
        r = self.run_tool("run", "first", "--rc", CLAUDE_MOVE_CLAUDE=str(exe), CLAUDE_MOVE_POLL="0.1",
                          CLAUDE_MOVE_NOTIFY_CMD=append_cmd(sent))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("first hit its 5-hour limit", r.stderr)
        self.assertIn("Moving this session to second", r.stderr)
        args = argv.read_text(encoding="utf-8").splitlines()
        sid = args[args.index("--resume") + 1]
        self.assertEqual(args[args.index("--remote-control") + 1], "second")
        self.assertIn("Continue where you left off", args[-1])
        moved = (b_cfg / "projects/-p" / f"{sid}.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(moved), 3)  # first's two lines, then second's own
        self.assertEqual(len((a_cfg / "projects/-p" / f"{sid}.jsonl").read_text(encoding="utf-8").splitlines()), 2)  # source untouched
        self.assertIn("first hit its limit; the session moved to second", sent.read_text(encoding="utf-8"))

    def test_run_stays_when_no_other_account(self):
        a_cfg, _ = self.logins()
        hit = limit_hit("x", self.now, "seven_day", int(self.now + 3600), entry="cli")
        exe = stub(self.home / "claude", f"""
a = sys.argv[1:]
if "-p" in a:
    print("Not logged in"); sys.exit(0)
d = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "-p"
d.mkdir(parents=True, exist_ok=True)
with (d / (a[a.index("--session-id") + 1] + ".jsonl")).open("a", encoding="utf-8") as f:
    f.write({json.dumps(hit)!r} + "\\n")
time.sleep(1); sys.exit(3)
""")
        r = self.run_tool("run", "first", CLAUDE_MOVE_CLAUDE=str(exe), CLAUDE_MOVE_POLL="0.1", CLAUDE_MOVE_NOTIFY_CMD=NOOP)
        self.assertEqual(r.returncode, 3)  # claude was left alone and its exit code passed through
        self.assertIn("No other account to move to", r.stderr)

    def test_notify_once_per_level_and_window(self):
        sent = self.home / "sent"
        cfg = self.home / ".claude-second"
        cfg.mkdir()
        (cfg / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        reset = int(self.now + 3600)

        def record(pct, at=reset):
            line = json.dumps({"rate_limits": {"five_hour": {"used_percentage": pct, "resets_at": at}}})
            return self.run_tool("watch", "record", stdin=line, CLAUDE_CONFIG_DIR=str(cfg), CLAUDE_MOVE_NOTIFY_CMD=append_cmd(sent))

        record(50)
        self.assertFalse(sent.exists())
        record(91)
        record(92)
        self.assertEqual(sent.read_text(encoding="utf-8").count("5h limit 9"), 1)
        record(96)
        record(10, reset + FIVE_H)  # next window: starts over, nothing to say yet
        record(80, reset + FIVE_H)
        self.assertEqual([ln for ln in sent.read_text(encoding="utf-8").splitlines() if "limit" in ln],
                         [f"bbbbbbbb: 5h limit 91% used · resets {fmt(reset)}", f"bbbbbbbb: 5h limit 96% used · resets {fmt(reset)}",
                          f"bbbbbbbb: 5h limit 80% used · resets {fmt(reset + FIVE_H)}"])
        self.assertIn("off", self.run_tool("notify", "off").stdout)
        record(99, reset + FIVE_H)
        self.assertEqual(sent.read_text(encoding="utf-8").count("limit"), 3)
        self.assertIn("80/95", self.run_tool("notify", "on", "--levels", "95,80").stdout)

    def test_doctor(self):
        cfg = self.home / ".claude-second"
        cfg.mkdir()
        (cfg / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        (self.home / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))  # stale profile
        r = self.run_tool("doctor")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("bbbbbbbb shows up in ~/.claude-second, ~/.claude; claude-move uses ~/.claude-second", r.stdout)
        self.assertIn("aaaaaaaa has desktop sessions but no CLI login", r.stdout)
        self.assertIn("no status line recorder in ~/.claude-second", r.stdout)
        self.assertIn("thing(s) to look at", r.stdout)


def fmt(ts):
    return time.strftime("%m-%d %H:%M", time.localtime(ts))


class Windows(unittest.TestCase):
    """The Windows branches: the scripts, commands and icon are checked on any OS; the rest only on Windows."""

    def setUp(self):
        self.cm = load_tool("cmw")
        self.cm.WIN, self.cm.ZH = True, False

    def test_windows_scripts(self):
        cm = self.cm
        path, body = cm.term_script("login-claude-new", None, {"CLAUDE_CONFIG_DIR": r"C:\Users\Lay la\.claude-new"},
                                    [r"C:\Users\Lay la\AppData\Roaming\npm\claude.cmd", "auth", "login", "--claudeai"],
                                    before=["Sign in (100% & done) <now>"], after=["ok"])
        self.assertEqual(path.name, "login-claude-new.cmd")
        self.assertEqual(body.split("\r\n"), [
            "@echo off", "chcp 65001 >nul", 'cd /d "%USERPROFILE%"', r'set "CLAUDE_CONFIG_DIR=C:\Users\Lay la\.claude-new"',
            "echo(Sign in ^(100%% ^& done^) ^<now^>",
            r'call "C:\Users\Lay la\AppData\Roaming\npm\claude.cmd" auth login --claudeai', "echo(ok", ""])
        _, body = cm.term_script("claude-rc", r"D:\work\app", {"CLAUDE_CONFIG_DIR": None}, ["claude", "--remote-control", "it's me"])
        self.assertIn(r'cd /d D:\work\app 2>nul || cd /d "%USERPROFILE%"', body)
        self.assertIn('set "CLAUDE_CONFIG_DIR="\r\nclaude --remote-control "it\'s me"', body)
        cfg = cm.HOME / ".claude-gmail"
        self.assertEqual(cm.env_cmd(cfg, "claude"), f"$env:CLAUDE_CONFIG_DIR='{cfg}'; claude")
        self.assertEqual(cm.env_cmd(cm.HOME / ".claude", "claude"), "claude")
        self.assertIn("PowerShell", cm.t("t_none", t="x"))
        self.assertIn("this computer", cm.t("p_url", u="u"))

    def test_windows_desktop_app_is_told_from_the_cli(self):
        cm = self.cm
        self.assertTrue(cm.desktop_exe(r"C:\Users\x\AppData\Local\AnthropicClaude\app-1.2.3\claude.exe"))
        self.assertTrue(cm.desktop_exe(r"C:\Program Files\WindowsApps\Claude_1.9659.2.0_x64__pzs8sxrjxfjjc\app\Claude.exe"))
        self.assertFalse(cm.desktop_exe(r"C:\Users\x\.local\bin\claude.exe"))
        self.assertFalse(cm.desktop_exe(r"C:\Program Files\nodejs\node.exe"))

    def test_icon(self):
        import base64
        import struct
        png = self.cm.png_shrink(base64.b64decode("".join(self.cm.ICON_PNG)))
        self.assertEqual(struct.unpack(">II", png[16:24]), (256, 256))
        ico = self.cm.png_to_ico(png)
        self.assertEqual(ico[:6], b"\0\0\1\0\1\0")
        self.assertEqual(ico[22:], png)

    @unittest.skipUnless(WIN, "Windows only")
    def test_start_menu_shortcut(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CLAUDE_MOVE_HOME=tmp, CLAUDE_MOVE_LANG="en")
            r = subprocess.run([sys.executable, str(TOOL), "app", "install", "--dir", tmp, "--no-dock"],
                               capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(tmp) / "Claude Move.lnk").stat().st_size > 0)
            self.assertTrue((Path(tmp) / ".config/claude-move/claude-move.ico").exists())
            r = subprocess.run([sys.executable, str(TOOL), "app", "uninstall", "--dir", tmp],
                               capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((Path(tmp) / "Claude Move.lnk").exists())

    @unittest.skipUnless(WIN, "Windows only")
    def test_processes(self):
        cm = load_tool("cmw2")
        procs = cm.win_procs()
        self.assertEqual(procs[os.getpid()][0], os.getppid())
        self.assertTrue(cm.pid_alive(os.getpid()))
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.assertTrue(cm.pid_alive(child.pid))
        self.assertTrue(cm.pid_alive(child.pid), "asking must not end it, as os.kill(pid, 0) would")
        child.kill()
        child.wait()
        self.assertFalse(cm.pid_alive(child.pid))
        self.assertIsInstance(cm.app_running(), bool)


class Help(unittest.TestCase):
    def test_every_help_renders(self):
        for args in ([], ["list"], ["sessions"], ["name"], ["to"], ["undo"], ["import-cli"], ["usage"], ["panel"], ["app"], ["term"], ["run"], ["notify"], ["doctor"], ["watch"],
                     ["quota-snapshot"], ["fm-pin"], ["find"], ["resume"], ["ps"], ["tmux"]):
            r = subprocess.run([sys.executable, str(TOOL), *args, "--help"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (args, r.stderr[-300:]))
