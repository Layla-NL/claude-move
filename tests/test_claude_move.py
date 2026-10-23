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
        log = self.home / "Library/Logs/Claude/main.log"
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
                   CLAUDE_MOVE_LANG="en", **env_extra)
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env, input=stdin)

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
        page = (self.home / ".config/claude-move/usage.html").read_text()
        self.assertIn("<!doctype html>", page)
        self.assertIn("prefers-color-scheme:dark", page)

    def test_watch_records_official_limits_and_restores_old_status_line(self):
        cfg = self.home / "cli"
        cfg.mkdir()
        (cfg / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": self.b}}))
        (cfg / "settings.json").write_text(json.dumps({"theme": "dark", "statusLine": {"type": "command", "command": "echo old"}}))
        r = self.run_tool("watch", "install", CLAUDE_CONFIG_DIR=str(cfg))
        self.assertEqual(r.returncode, 0, r.stderr)
        cmd = json.loads((cfg / "settings.json").read_text())["statusLine"]["command"]
        self.assertIn("watch record", cmd)
        payload = json.dumps({"rate_limits": {"five_hour": {"used_percentage": 23.5, "resets_at": 1},
                                              "seven_day": {"used_percentage": 41.2, "resets_at": 2}}})
        r = self.run_tool("watch", "record", stdin=payload, CLAUDE_CONFIG_DIR=str(cfg))
        self.assertEqual(r.stdout.strip(), "old")  # the previous status line still shows
        saved = json.loads((self.home / ".config/claude-move/limits.json").read_text())
        self.assertEqual([(r["kind"], r["percent"]) for r in saved[self.b]["rows"]], [("weekly_all", 41.2), ("session", 23.5)])
        r = self.run_tool("usage")
        self.assertIn("official: week 41% · 5h 24%", r.stdout)
        self.run_tool("watch", "uninstall", CLAUDE_CONFIG_DIR=str(cfg))
        s = json.loads((cfg / "settings.json").read_text())
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
        stub = self.home / "claude"
        stub.write_text("#!/bin/sh\n"
                        f"if [ \"$CLAUDE_CONFIG_DIR\" = \"{good}\" ]; then echo '{json.dumps(report)}'; "
                        "else echo 'Not logged in · Please run /login'; fi\n")
        stub.chmod(0o755)
        self.run_tool("name", "bbbb", "second")
        r = self.run_tool("usage", "--refresh", CLAUDE_MOVE_CLAUDE=str(stub))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("~/.claude-second: second  week 41% · week · Opus 12% · 5h 100%", r.stdout)
        self.assertIn("~/.claude-old: no plan usage", r.stdout)
        line = next(ln for ln in r.stdout.splitlines() if ln.startswith("second"))
        self.assertIn("Max 20x", line)
        self.assertIn("cooling", line)  # 5-hour meter at 100% counts as cooling until it resets
        self.assertIn("official: week 41% · week · Opus 12% · 5h 100%", line)
        page_r = self.run_tool("usage", "--html", "--no-open")
        self.assertEqual(page_r.returncode, 0, page_r.stderr)
        self.assertIn("week · Opus", (self.home / ".config/claude-move/usage.html").read_text())


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
    setUp, tearDown = Usage.setUp, Usage.tearDown

    def start(self):
        import re
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(CLAUDE_MOVE_HOME=str(self.home), CLAUDE_MOVE_ROOT=str(self.root), CLAUDE_MOVE_DESKTOP_CONFIG=str(self.desk),
                   CLAUDE_MOVE_LANG="en", CLAUDE_MOVE_SKIP_APP_CHECK="1",
                   CLAUDE_MOVE_QUIT_CMD=f"touch {self.home}/quit", CLAUDE_MOVE_OPEN_CMD=f"touch {self.home}/open")
        self.proc = subprocess.Popen([sys.executable, str(TOOL), "panel", "--no-open"], stdout=subprocess.PIPE, text=True, env=env)
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
        log = self.home / "Library/Logs/Claude/main.log"
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.now - 10))
        log.write_text(log.read_text() + f"{stamp} [info] [oauth-v2] lookup orgId=x cacheKey=acct:{c}|y:x:https:/\n")
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
        self.assertEqual(time.strftime("%m-%d %H:%M", time.gmtime(rows[1]["resets_at"])), "10-27 02:00")


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
        launch = (app / "Contents/Resources/launch.sh").read_text()
        self.assertIn("panel --here --idle 1800", launch)
        self.assertTrue((app / "Contents/Resources/applet.icns").stat().st_size > 1000)
        self.assertFalse((app / "Contents/Resources/Assets.car").exists())
        v = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stderr)


class Help(unittest.TestCase):
    def test_every_help_renders(self):
        for args in ([], ["list"], ["sessions"], ["name"], ["to"], ["undo"], ["import-cli"], ["usage"], ["panel"], ["app"], ["watch"]):
            r = subprocess.run([sys.executable, str(TOOL), *args, "--help"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (args, r.stderr[-300:]))
