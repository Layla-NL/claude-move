# claude-move

Switched the Claude desktop app to another account and the Code tab's session list is empty?
Your sessions are still on disk. `claude-move` copies the list over to the account you are using now.

[中文说明](#中文)

> Unofficial. Not affiliated with or endorsed by Anthropic. It depends on the desktop app's
> on-disk layout, which may change in any release. macOS and Windows (Windows support is new: its tests run on
> Windows in CI, and finding, closing and reopening the desktop app was tried on Windows 11, but a full move has not
> been yet; see [Windows](#windows)).

## Why the list looks empty

The desktop app keeps the Code session **list** per account:

```
~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/local_*.json
```

The **transcripts** themselves live in `~/.claude/projects/` and do not belong to any account.
So after a sign-in switch, nothing is lost: the new account just has no list entries pointing at
your sessions. `claude-move` copies those entries across.

## Safety

- Copy only. It never deletes anything, on either account.
- Before writing, it backs up the target account's whole list to
  `~/Library/Application Support/Claude/claude-code-sessions-backups/<time>-<account>`.
- If the target already has a newer copy of a session, that copy is kept.
- It refuses to write while the desktop app is running.
- `--dry-run` shows the plan and changes nothing.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Layla-NL/claude-move/main/claude-move -o ~/.local/bin/claude-move
chmod +x ~/.local/bin/claude-move
```

Needs Python 3.9+ (the one macOS ships is fine). No dependencies.

## Windows

Install Python 3.9 or newer from python.org (or `winget install Python.Python.3.13`), then in PowerShell:

```powershell
irm https://raw.githubusercontent.com/Layla-NL/claude-move/main/claude-move -OutFile $HOME\claude-move.py
py $HOME\claude-move.py app install     # a "Claude Move" shortcut in the Start menu and on the desktop
```

Open Claude Move from the Start menu to get the panel; everything below works from there. On the command line,
write `py $HOME\claude-move.py` wherever this page says `claude-move`. What is different on Windows:

- The desktop app's data is in `%APPDATA%\Claude` (the Microsoft Store version too). If a Store version keeps a copy in
  `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude`, claude-move uses whichever has the newest session list.
- Commands to copy are for PowerShell: `$env:CLAUDE_CONFIG_DIR='C:\Users\you\.claude-work'; claude`.
- "Open in Terminal" opens a console window (Windows Terminal when it is your default) that stays open after `claude`
  ends.
- The desktop app's ✕ only hides it in the notification area, and nothing outside the app can ask it to quit, so the
  panel's move button ends its processes (anything running in its Code tab stops, as when you quit it), then starts
  it again from the Start menu entry. On the command line, quit it yourself: right-click its icon in the notification
  area, then Quit.
- Notifications are Windows toasts.
- `app install` makes a Start menu shortcut (and one on the desktop unless `--no-dock`) instead of `Claude Move.app`;
  `--icon` takes a PNG or ICO.

## Switching accounts

1. Sign the desktop app into the new account and open the Code tab once, so its folder exists.
2. Quit the desktop app completely (Claude menu → Quit).
3. Run `claude-move to <new account>`.
4. Reopen the app.

## Commands

| Command | What it does |
|---|---|
| `claude-move list [--json]` | Accounts on this Mac, live/archived session counts, which one was used last. `--json` adds the account the desktop app is signed into and the last `--app` move, for the mod |
| `claude-move sessions <account>` | Live sessions of one account |
| `claude-move name <account> <label>` | Give an account a short label, e.g. `work`, `personal` |
| `claude-move to <target> [--from <source>] [--days N] [--all] [--only TEXT] [--dry-run] [--app]` | Copy live sessions used in the last N days (default 3) from the source (default: the most recently used account) to the target. `--only` picks sessions by title text or id prefix (repeatable). Lists any artifacts those sessions published, because those stay with the account that created them. `--app` quits the desktop app first and opens it again afterwards; started inside the app, it hands the work to a copy of claude-move running on its own, which sends a notification when it is done |
| `claude-move undo [--list] [--backup NAME] [--dry-run] [--app]` | Put the target account's list back exactly as it was before the last move: replaced entries are restored, added ones removed. The state right before the undo is saved too. `--app` as for `to` |
| `claude-move usage [--refresh] [--html] [--config DIR]` | Quota per account: cooling and reset times, use this week and in the last 5 hours, official % from the CLI. `--refresh` asks `/usage` of each signed-in CLI folder first; `--html` opens a panel page; `--json` prints the numbers for the mod |
| `claude-move panel [--demo]` | The same panel in your browser, served on 127.0.0.1 only, with a button that moves your sessions after you switch accounts (see below). `--demo` shows sample accounts instead, reads nothing on this computer and its buttons do nothing: for screenshots, or a look before you set anything up |
| `claude-move app install [--icon IMAGE] [--no-dock]` | Make `~/Applications/Claude Move.app` and put it in the Dock: double-click it to open the panel, no Terminal needed |
| `claude-move bar install` | macOS: a ball in the menu bar through [SwiftBar](https://swiftbar.app) or xbar, colored like the panel, for the account the desktop app is signed into; its menu lists every account and opens the panel. It reads only the official numbers already saved, so it costs nothing to run every minute. `bar uninstall` removes it |
| `claude-move term <account> [--rc]` | Open a new tmux window (when tmux is running) or Terminal window running Claude Code as that account, with its own CLI login folder (`CLAUDE_CONFIG_DIR=~/.claude-<name>`), in the project folder that account used last. `--rc` starts it as a Remote Control session named after the account, so the Claude phone app signed into the same account can join |
| `claude-move run <account> [--rc] [--resume ID] [-- claude args]` | Run Claude Code as that account; when the session hits a usage limit, move it to the CLI login with the most left and resume it there (see below) |
| `claude-move notify on\|off\|status\|test [--levels 75,90,95]` | macOS notifications when an account's official % passes each level, once per reset window (on by default). Once a week, the first time the panel or `usage` reads your use, a summary of last week: total at API prices, the account that used most, the busiest day |
| `claude-move doctor [--refresh]` | Check labels, CLI logins (and whether `/usage` answers in each), accounts that show up in two folders, desktop accounts without a CLI login, the status line recorder and the app's signature |
| `claude-move watch install` / `uninstall` | Record the official 5-hour/weekly % each time the CLI status line refreshes; keeps your existing status line |
| `claude-move fm-pin [<account>] [--group crews\|resident] [--relaunch]` | For [firstmate](https://github.com/kunchenguid/firstmate): show which CLI login each group uses, or pin a group to one. It checks that login answers `/usage` and is not cooling (`--force` pins it anyway). The crews (the default group) are pinned in firstmate's `config/claude-account` and in each second mate's own home, and the quota snapshot follows them; crews started after that use it, running ones stay where they are. `--group resident` pins the second mates themselves (`config/secondmate-accounts/<id>/claude-account`); each takes it when relaunched, and `--relaunch` relaunches the idle ones through firstmate's `bin/fm-control.sh` |
| `claude-move quota-snapshot [--refresh] [--account A] [--out FILE]` | Write one account's official % in quota-axi's cache format, so firstmate's quota-axi reads it through `QUOTA_AXI_SNAPSHOT` without touching the login or the Keychain (see below). `schedule [--every 10]` / `unschedule`: refresh it every few minutes (launchd on macOS, Task Scheduler on Windows); `status` shows the pin, the file and the schedule |
| `claude-move find <words> [--account A] [--json]` | Search what was said in the terminal sessions of every CLI login: your prompts, Claude's replies and session titles (not tool output). Each hit shows the account, project, a snippet, whether it is running, and `claude-move resume <id>`. The first search reads every transcript once into `~/.cache/claude-move/search.db` (readable only by you); later ones read only what is new |
| `claude-move resume <id> [--to <account>] [--here]` | Resume a terminal session in its own folder with its own login: in a new tmux window when tmux is running, else a new terminal window; `--here` in this one. `--to` copies it into another account's CLI login first (copy only, as `run` does) and resumes it there. A session that is already running is not started twice |
| `claude-move ps [--go <target>] [--label <target> <name>] [--pin\|--unpin <target>...] [--json]` | Claude Code sessions running now, from every CLI login: account, busy or idle, tmux window, name, folder. `--go` shows one (by tmux target, session id prefix or pid) in the terminal attached to tmux, or opens a terminal attached to it. `--label` gives one a name of your own (`""` takes it off), kept in `~/.config/claude-move/labels.json` and shown first in `ps`, the tmux menu, the panel and `find`; windows claude-move names follow it, and windows other tools named (firstmate's `fm-*`) keep their names. `--pin` keeps sessions at the top of `ps`, the tmux menu and the panel (📌), `--unpin` takes them off, also by id once a session has ended |
| `claude-move group [<name> [<session>...]] [--to <account>] [--out] [--dry-run]` | Your own groups of terminal sessions, kept in `~/.config/claude-move/groups.json`; `ps`, the panel and the mod list each group together. `group <name> <session>...` puts sessions in a group (made then; a session is in one group at most), `--out` takes them out. `group <name> --to <account>` moves the whole group to another CLI login: each idle member running in tmux quits and resumes there, copied first, with its conversation and id kept. Busy members, members outside tmux, sessions with nothing said yet and firstmate's crews (switched with `fm-pin`) are left as they are, each with what to do |
| `claude-move tmux [name\|line\|menu\|conf]` | `name` names each tmux window that holds one Claude session `account·session` (● while busy); windows someone else named, such as firstmate's, stay as they are. `line` prints running sessions per account for the status bar, `menu` pops up a menu of them. `conf --install` adds a block to `~/.tmux.conf` (backed up first) that wires these up: mouse on, `line` in the status bar every 15 s, prefix + S for the menu; `conf --remove` takes it out and puts tmux's defaults back |
| `claude-move import-cli --config DIR [--project PATH] [--session ID] [--days N] [--dry-run]` | Copy CLI session transcripts from another config folder (e.g. a second account under `CLAUDE_CONFIG_DIR=~/.claude-work`) into `~/.claude`, so the desktop app can open them. Never overwrites. A project folder name that starts with `-` needs `--project=-Users-me-app` |

`<account>` is a label, or the first few characters of the account id shown by `list`.
Labels are stored in `~/.config/claude-move/accounts.json`.

## Quota panel

`claude-move usage` shows each account side by side, so you know which one to switch to:

- **Cooling and reset times.** When an account hits its 5-hour or weekly limit, Claude Code writes the
  official limit message, with the reset time, into the transcript. The panel reads those, so you see
  "weekly limit used up, back at 10-24 10:00" and when each weekly window resets.
- **Use per account.** Replies in `~/.claude/projects` and in every signed-in CLI folder (`~/.claude-*`) are summed for the last 5 hours and the current week,
  priced at API list prices. This is only for comparing accounts; it is not your bill and not a percentage
  of your plan. Desktop replies are credited to whoever was signed into the desktop app at that moment
  (the app's own log names the account it is using); CLI replies go to the account of the config folder
  they ran in, also after the session was copied into `~/.claude` for the app (`--config` adds a folder elsewhere).
- **Official percentages, from the CLI.** `claude-move usage --refresh` runs the CLI's own `/usage` command once
  for every config folder that is signed in (`~/.claude` and `~/.claude-*`) and shows the same meters as the
  plan's usage page: this 5-hour session, the week, and any per-model weekly meter. `/usage` is a local
  command, so it uses no quota, and claude-move never sees the login: it only runs the CLI.
  Alternatively, `claude-move watch install` adds a status line recorder that saves the percentages each time
  the CLI status line refreshes (your existing status line keeps showing). The desktop app's Code tab does
  not run status line scripts.
- **Plan.** Each account shows its plan (Pro, Max 5x, Max 20x) from the profile its CLI login caches. The
  suggested account is the one with the most quota left this week, weighting the weekly % by plan size.

To get official percentages for every account, sign each one into its own CLI config folder once:

```bash
CLAUDE_CONFIG_DIR=~/.claude-work claude    # then type /login and sign in with that account
```

Repeat with another folder name (`~/.claude-personal`, ...) per account, then run `claude-move usage --refresh --html`.

`claude-move usage --html` also writes a panel page and opens it. It counts Claude Code on this Mac only;
claude.ai chat and other devices are not included.

### What the panel shows

- Each account is a card with a ball of slowly flowing ink. Its color follows the account's tightest official
  limit: blue when little is used, then teal, green and yellow, amber at 75%, red at 90% and 95% (where
  notifications fire), deep red when used up or cooling. When the number changes, the color travels along that
  ramp. An account with no official % is silver: the color is never estimated. The big number is that limit's %
  used, the small tabs under it switch to another limit, and a cooling account shows when it is back.
- Buttons are icons. Hover one, or the check mark or clock in a card's corner, to see what it does and how old
  the official numbers are.
- **Total use:** every account's use at API list prices as a heatmap, one square a day for 26 weeks, next to the
  hours of the week you use Claude Code most. Click a day to see the projects behind it. Claude Code deletes
  transcripts after 30 days by default; claude-move keeps the daily figures in its cache, so the heatmap fills
  in from the day you start using it.
- **Next 7 days:** a line per account with a dot where each official limit resets (colored by how full it is) and a
  red bar until a cooling account is back. The scale is stretched near "now", so the next hours are readable.
- **Search** (top right) finds desktop sessions of every account by title. A result from another account has a
  button that copies it into the account the desktop app is signed into (the app is closed and reopened).
- **Keys:** 1–9 open that card's terminal, / searches, R refreshes the official %, Esc closes.
- The browser tab shows the desktop app's account: its ball as the icon, its number in the title.
- "Accent" in the dock sets how much a second color drifts through each ball; the buttons at the top right switch
  between light, dark and the system's theme, and between English and Chinese. All three are kept in
  `~/.config/claude-move/look.json`.

### Switching from the panel

`claude-move panel` opens the panel with a switch button. Signing in stays with you, in the app's own sign-in:

1. In the desktop app, log out, sign in with the account you want, and open the Code tab once.
2. In the panel, press the black "A → B" button. It checks that the app really is signed
   into B (from the app's log), quits the app, runs the same copy as `claude-move to B` (backup first), and
   reopens the app.

Easiest: run `claude-move app install` once. It makes `~/Applications/Claude Move.app` (in the Dock too); double-click
it and the panel opens. It runs on its own, so quitting the desktop app from the panel does not stop it, a second
double-click brings back the running panel, and it stops by itself 30 minutes after its page is closed.
`--icon` takes any image for the app icon. If you start `claude-move panel` by hand, do it from Terminal, not from
inside a Claude Code session in the desktop app: quitting the app would stop that session too. The panel is served on 127.0.0.1 with a one-time token, so only this Mac can
use it, and its buttons can only quit/reopen the app, move sessions, refresh the official %, and open Terminal.
Each card with a CLI login has "Open in Terminal", which starts `claude` in a new Terminal window with that
account's own config folder, in the project folder it used last (the same as `claude-move term <account>`; nothing
about the login is read), and "Open in Terminal, reachable from phone", which adds `--remote-control <label>`. Both
commands can also be copied (`CLAUDE_CONFIG_DIR=~/.claude-work claude`). When `~/.claude` and a `~/.claude-*` folder show
the same account, the `~/.claude-*` one is used.

### Terminal sessions

Under the cards, **Terminal sessions** lists the Claude Code sessions running on this Mac from every CLI login
(`ps`), pinned ones first, then busy, refreshed every 10 seconds; the pin button pins one to the top, and Go there brings up its tmux window. Its buttons name tmux windows
(`tmux name`) and add or remove the `~/.tmux.conf` block (`tmux conf`, after showing it). The search box at the top
finds terminal sessions by what was said (`find`) under the desktop ones, with Resume (`resume`), Go there for one
that is running, and the command to resume it by hand. The list comes from the `sessions/<pid>.json` files Claude Code
keeps for its running processes; those are not documented and may change.

### Inside Claude Code: the cmove mod

The same terminal-session list, quota and search can sit beside the chat in Claude Code, as a mod in [`mod/`](mod/):
quota per account in the status line, `/cm` for the running sessions (📌 pin, ✎ name, → go there) and
`/cm-find <words>` to search and resume. Its Move page copies the desktop app's sessions into the account the app
is signed into now: the first press shows what would change, the second quits the app, copies (backup first) and
opens it again, through `claude-move to --app`, which runs on its own so quitting the app does not stop it. Undo the
last move there the same way. Its buttons run claude-move, which has to be installed.

```
/plugin install cmove --marketplace Layla-NL/claude-move
```

### Everything else from the panel

So you never need a terminal, the panel also does the rest. Each card can be renamed, and has "Install / Remove
status line recorder" for its CLI login (it asks first, since that edits the login's `settings.json`), or "Add CLI
login" when the account has none: that opens a Terminal window with the CLI's own `claude auth login --claudeai` for
a new `~/.claude-<name>` folder, you sign in in the browser, and the panel names the account once the login shows
up. In the dock under the cards:

- **Move sessions:** pick source, target and which sessions (last 3 or 7 days, all, or ticked ones), preview, then
  move. An open desktop app is quit and reopened around the move.
- **Undo a move:** the backups, each with an undo button.
- **Sessions by account**, and **open CLI sessions in the desktop app** (the panel's `import-cli`).
- **Auto-continue sessions:** each `run` session, which account it is on now and when it switched.
- **Check-up:** `doctor`, with a fix button where there is one, and a button to add another account's CLI login.
- **Notifications:** on/off, levels, a test.
- **firstmate crews** (when `~/Developer/firstmate` exists): which account the crews use, the snapshot and its
  schedule, a "pin for crews" button per account and "refresh the snapshot now". The card the crews use has an
  anchor next to its name.
- **Updates:** asks GitHub for the latest release when you press it; nothing is downloaded.

Every button is a fixed action, and every value the page sends (account, backup, session id, label, folder name)
is checked against what is on this Mac first.

### Going on at a usage limit

`claude-move run <account>` starts `claude` with that account's CLI login and a session id it picks. It watches that
session's transcript (subagents included). When the official limit message shows up, it asks each other CLI login
its `/usage`, picks the one with the most left that is not cooling, stops `claude`, copies the transcript into that
login's folder (whatever was there for this session is saved under `~/.config/claude-move/run-backups` first),
and starts `claude --resume <id>` there with a note to continue. The source transcript is left as it was. If no
account is free, `claude` is left running and you get a notification. `--rc` makes each step a Remote Control
session named after its account. In the panel, tick "Terminals switch account and go on…" and the Open in Terminal
buttons go through `run`.

It only works in the CLI: the desktop app's sign-in stays with you. Background tasks and a tool call that was
running do not carry over; the new account gets the conversation and goes on from there. Whether using several
accounts this way is allowed depends on Anthropic's terms for your plan, so check them first.

Notifications (`claude-move notify`) fire when the official % updates: the status line recorder in each CLI login
(`CLAUDE_CONFIG_DIR=~/.claude-work claude-move watch install`) or `usage --refresh`. `claude-move doctor` lists what
is missing.

### firstmate

[firstmate](https://github.com/kunchenguid/firstmate) checks Claude quota with quota-axi before it starts work.
Reading it itself, quota-axi needs the Keychain; given `QUOTA_AXI_SNAPSHOT=<file>` it reads only that file. claude-move
writes that file from the official numbers it already has:

```bash
claude-move fm-pin outlook             # crews use ~/.claude-outlook; the snapshot follows
claude-move fm-pin gmail --group resident   # the second mates use gmail once relaunched
claude-move quota-snapshot schedule    # refresh it every 10 minutes
export QUOTA_AXI_SNAPSHOT=~/.cache/claude-move/quota-axi-snapshot.json   # in firstmate's start-up
```

- The file is quota-axi's cache format: one Claude row without an account key (the row firstmate binds Claude crews
  to), windows `five_hour`, `seven_day` and `model:<id>` for per-model weeks, `refreshedAt` set to when `/usage`
  answered. It is written to a temporary file and renamed, readable only by you.
- The account is the one in firstmate's `config/claude-account`, so pin and snapshot cannot drift apart.
- Freshness: each scheduled run asks that login's `/usage` (no quota used), and the other logins' once an hour. With
  the status line recorder in that login, crews that are working update it too, at most once a minute. quota-axi
  treats a snapshot as current until a window resets, so if `/usage` keeps failing for an hour (signed out, asleep
  too long) the file is moved aside to `….stale`: firstmate then sees no Claude quota instead of old quota. Without
  official numbers nothing is written and the command exits non-zero.
- Each write is logged in `~/.cache/claude-move/quota-snapshot.log` (account, both percentages, `refreshedAt`).
- Switching stays yours: at 90 and 95% the notification for the crews' account names the login with the most of this
  week left and the `fm-pin` command for it. Nothing switches crews on its own: firstmate leaves that file to its
  captain, and rotating accounts automatically is the kind of use Anthropic's terms may not allow.

### Copies and their trail

A desktop session has one history: every desktop account reads the same transcript in `~/.claude`, and a move only
copies the small list entry that points to it. A terminal session moved to another login (`resume --to`, `run`,
moving a group) is copied whole into that login's folder; each move copies the newest over the copy there (saving
what was there first in `~/.config/claude-move/run-backups`), so it stays one line of history as long as you go on
in one place at a time. Copies are never merged and claude-move deletes none of them.

Every copy claude-move makes is written to `~/.config/claude-move/moves.jsonl`: when, which session, from and to
which account or folder, its size, and where what it replaced was saved.

```bash
claude-move dupes                    # sessions kept in more than one folder, what the copies and the backups take
claude-move trail d767de1f           # one session: its copies now, the desktop lists holding it, its moves, older versions
claude-move dupes --max-copies 2 --max-mb 1024   # the limits the panel warns at
```

Past a limit the panel shows a warning at the top; its Copies tool lists the copies and shows each session's
trail. Claude Code itself clears transcripts older than `cleanupPeriodDays` (30 days by default) in each folder.

### Codex

Codex logins sit beside the Claude ones. Codex keeps no per-account session list, so nothing is moved; the rest is
the same. Each Codex folder (`~/.codex`, and `~/.codex-<name>` for another login through `CODEX_HOME`) is read for
what its session files say: the account each session ran under (`creator_account_id`), and the official numbers
Codex writes as it goes (`rate_limits`: the week and the 5-hour window, the plan, credits). Its `auth.json` is never
opened.

```bash
claude-move codex                    # each Codex account: plan, official %, reset, credits, folder, the one to use
claude-move codex login work         # sign another login into ~/.codex-work (codex login, in a new window)
claude-move codex term work          # open Codex with that login, in the folder it was used in last
claude-move name 320d codex-main     # name a Codex account like any other
```

`usage` (and `usage --json`, the panel's cards, the mod's status line) shows the Codex accounts after the Claude
ones; notifications at 75/90/95% cover them too. `ps`, the panel's running list and the mod list running Codex
sessions (macOS and Linux, from the session file each Codex process holds open), busy or idle, with their tmux
window; `find` searches what was said in them and `resume <id>` resumes one with `codex resume` in its own folder
and login. Pins, names and groups work on them as on Claude sessions; moving a group leaves its Codex sessions
where they are.

## What it does not do

- It does not move artifacts, projects or anything stored on claude.ai; those stay with the
  account that created them.
- It never reads or uses credentials. `usage` reads transcripts, account ids and the desktop app's log lines
  that name the signed-in account; `watch install` edits `settings.json` only when you run it, and
  `watch uninstall` puts the old status line back.
- Permissions you granted inside a session ("allow for this session") are not carried over.

## Tests

```bash
python3 -m unittest discover tests
```

GitHub Actions runs them on Windows (Python 3.9 and 3.14) and macOS for every push.

## License

MIT

---

## 中文

Claude 桌面 App 换了账号登录以后，Code 页左边的会话列表空了？会话其实都还在本机，`claude-move` 把列表搬到你现在用的账号下。

> 非官方工具，和 Anthropic 没有关系。它依赖桌面 App 在磁盘上的存放方式，App 更新后可能失效。支持 macOS 和 Windows（Windows 是新加的：测试在 GitHub 的 Windows 机器上跑过；在 Windows 11 真机上试过找到、关掉、重新打开桌面 App，完整搬一次还没试过）。

**Windows：** 先从 python.org 装 Python 3.9 以上（或 `winget install Python.Python.3.13`），然后在 PowerShell 里：

```powershell
irm https://raw.githubusercontent.com/Layla-NL/claude-move/main/claude-move -OutFile $HOME\claude-move.py
py $HOME\claude-move.py app install     # 开始菜单和桌面上会出现 “Claude Move” 快捷方式
```

从开始菜单打开 Claude Move 就是面板，下面说的事都能在面板上点。命令行里把本文的 `claude-move` 换成 `py $HOME\claude-move.py`。和 Mac 不一样的地方：
- 桌面 App 的数据在 `%APPDATA%\Claude`（微软商店版也是）。如果商店版在 `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude` 也有一份，claude-move 用会话列表最新的那个。
- 复制的命令是 PowerShell 写法：`$env:CLAUDE_CONFIG_DIR='C:\Users\你\.claude-work'; claude`。
- “打开终端”开的是命令行窗口（默认终端是 Windows Terminal 就用它），`claude` 退出后窗口不关。
- 桌面 App 点 ✕ 只是缩到通知区域，外面也没办法请它退出，所以面板的搬家按钮会直接结束它的进程（Code 页里正在跑的会停下，跟退出 App 一样），搬完再从开始菜单的入口打开它。用命令行的话自己退出：右键通知区域里的 Claude 图标 → 退出。
- 通知是 Windows 的系统通知。
- `app install` 生成开始菜单快捷方式（不加 `--no-dock` 时桌面上也放一个），不是 `Claude Move.app`；`--icon` 用 PNG 或 ICO。

**为什么会空：** 会话**列表**按账号存在 `~/Library/Application Support/Claude/claude-code-sessions/<账号>/<组织>/` 下面；会话的**完整记录**在 `~/.claude/projects/`，不属于任何账号。换号以后什么都没丢，只是新账号下面没有指向这些会话的条目。

**安全：** 只复制，不删任何东西；写之前先把目标账号的整份列表备份；目标那边更新的不覆盖；桌面 App 开着时不动手；`--dry-run` 只看不改。

**换号步骤：**
1. 桌面 App 用新账号登录，打开一次 Code 页；
2. 完全退出桌面 App（菜单 Claude → 退出）；
3. 运行 `claude-move to <新账号>`；
4. 重新打开 App。

**命令：**
- `list` 看有哪些账号（`--json` 还会给出桌面 App 现在登录的号和上次用 `--app` 搬的结果，给 mod 用）；`sessions <账号>` 看某个账号的会话；`name <账号> <名字>` 起个好记的名字。
- `to <目标> [--from 来源] [--days N] [--all] [--only 文字] [--dry-run] [--app]`：搬最近 N 天（默认 3 天）用过、没归档的会话；`--only` 按标题或 id 挑着搬。搬之前会列出这些会话发布过的 artifact，提醒它们还归创建它的账号。`--app` 会先退出桌面 App，搬完再打开；如果是在 App 里面运行的，就交给一个独立运行的 claude-move 去做，做完弹通知。
- `undo [--list] [--backup 名字] [--dry-run] [--app]`：把目标账号的列表恢复成上次搬之前的样子，换掉的放回去，新加的拿掉；撤回前的样子也另存一份。`--app` 同 `to`。
- `import-cli --config 目录 [--project 路径] [--session id] [--days N] [--dry-run]`：把另一个配置目录（比如用 `CLAUDE_CONFIG_DIR=~/.claude-work` 登录的另一个账号）里的命令行会话记录拷到 `~/.claude`，桌面 App 就能打开；从不覆盖。

- `usage [--refresh] [--html] [--json] [--config 目录]`：各账号额度面板；`--refresh` 先向每个命令行登录问官方 `/usage`，`--html` 打开网页版，`--json` 输出给 mod 用的数字。
- `panel [--demo]`：在浏览器里打开带按钮的面板（只在本机 127.0.0.1 上）。`--demo` 换成示例账号，不读这台电脑上的任何东西，按钮也不做事，用来截图或者先看看长什么样。换号时：先在桌面 App 里退出登录、登上新号、打开一次 Code 页，再回面板点黑色的“A → B”按钮。面板会先从 App 日志确认 App 现在登录的确实是 B，然后退出 App、照 `claude-move to B` 搬会话（先备份）、重新打开 App。登录这一步始终由你在 App 里自己点。请在“终端”里运行 `claude-move panel`，不要在桌面 App 的 Claude Code 会话里运行，因为退出 App 会连那个会话一起关掉。有命令行登录的号，卡片上有“打开终端”：弹出一个新终端窗口，在这个号最近用过的项目文件夹里，用它自己的配置目录运行 `claude`（和 `claude-move term <账号>` 一样，不读登录信息）；“打开终端（手机可连）”再加上 `--remote-control <名字>`，手机 Claude App 登录同一个号就能连上。两条命令也都能一键复制。`~/.claude` 和某个 `~/.claude-*` 显示的是同一个号时，用 `~/.claude-*` 那个。
- `app install [--icon 图片] [--no-dock]`：生成 `~/Applications/Claude Move.app` 并放进程序坞，双击就打开面板，不用开终端。它独立运行，从面板退出桌面 App 不会把它关掉；再双击会回到已经开着的面板；页面关掉 30 分钟后自己停。`--icon` 可以换成任意图片当图标。
- `bar install`：macOS 菜单栏上的一颗小球（通过 [SwiftBar](https://swiftbar.app) 或 xbar），颜色和面板一样，显示桌面 App 登录的那个号；点开列出所有号，还能打开面板。只读已经存下的官方数字，每分钟跑一次也不费事。`bar uninstall` 去掉。
- `term <账号> [--rc]`：tmux 开着时开一个新的 tmux 窗口，不然弹出一个终端窗口，在这个号最近用过的项目文件夹里，用它的命令行登录目录（`CLAUDE_CONFIG_DIR=~/.claude-<名字>`）运行 Claude Code；`--rc` 以 Remote Control 会话启动、用账号名字命名，手机 App 登录同一个号就能连上。
- `run <账号> [--rc] [--resume id] [-- claude 的参数]`：用这个号运行 Claude Code，撞到额度上限时把会话搬到剩得最多的号接着干（见下面）。
- `notify on|off|status|test [--levels 75,90,95]`：某个号的官方百分比过 75/90/95% 时弹系统通知，每个重置周期每档只提醒一次（默认开）。每周第一次打开面板或运行 `usage` 时，还会发一条上周小结：按 API 价总共用了多少、哪个号用得最多、哪天最忙。
- `doctor [--refresh]`：自检：名字、各命令行登录（以及 `/usage` 能不能用）、同一个号出现在两个目录、有桌面会话却没有命令行登录的号、状态栏记录器、小 App 的签名。
- `watch install` / `watch uninstall`：装上（或卸掉）状态栏记录器，用命令行版时记下官方百分比。
- `find <词> [--account 账号] [--json]`：搜所有命令行登录的终端会话里聊过的内容：你说的话、Claude 的回答、会话标题（不搜工具输出）。每条结果显示账号、项目、片段、是不是正在跑，以及 `claude-move resume <id>`。第一次搜会把所有会话记录读一遍，存进 `~/.cache/claude-move/search.db`（只有你能读），之后只读新增的。
- `resume <id> [--to 账号] [--here]`：在会话自己的文件夹、用它自己的登录接着跑：tmux 开着就开一个新的 tmux 窗口，不然开新终端窗口；`--here` 就在当前终端。`--to` 先把会话复制到另一个号的命令行登录（只复制，和 `run` 一样）再在那边接上。已经在跑的会话不会再开第二个。
- `ps [--go 目标] [--label 目标 名字] [--pin|--unpin 目标…] [--json]`：现在在跑的 Claude Code 会话，所有命令行登录都算：账号、忙还是空闲、在哪个 tmux 窗口、名字、文件夹。`--go` 切过去（按 tmux 目标、会话 id 开头或进程号），在连着 tmux 的终端里显示，没有就开一个终端连上。`--label` 给会话起你自己的名字（写 `""` 去掉），存在 `~/.config/claude-move/labels.json`，`ps`、tmux 菜单、面板和 `find` 都先用它；claude-move 起名的窗口跟着改，别的工具起名的窗口（firstmate 的 `fm-*`）名字不动。`--pin` 把会话置顶（📌），`ps`、tmux 菜单和面板里都排最前，可以一次写好几个；`--unpin` 取消，会话结束了也能按 id 取消。
- `group [组名 [会话…]] [--to 账号] [--out] [--dry-run]`：自己给终端会话分组，存在 `~/.config/claude-move/groups.json`；`ps`、面板和 mod 里同组的排在一起。`group 组名 会话…` 把会话放进组（组随之建好；一个会话只在一个组里），`--out` 移出。`group 组名 --to 账号` 整组换号：tmux 里空闲的组员会退出，先拷到那个号的命令行登录，再在那边接着做，对话和会话 id 都不变。正在忙的、不在 tmux 里的、还没聊过的、firstmate 的船员（用 `fm-pin` 换）都不动，各自说明怎么办。面板的会话列表里每行有分组按钮，每组标题旁边可以选“这组换到…”。
- `tmux [name|line|menu|conf]`：`name` 把只装着一个 Claude 会话的 tmux 窗口改名成“账号·会话名”（忙的时候前面有 ●）；别人起过名的窗口（比如 firstmate 的）不动。`line` 输出给状态栏用的各账号会话数，`menu` 弹出会话菜单。`conf --install` 往 `~/.tmux.conf` 加一段（先备份）把这些接上：开鼠标、状态栏每 15 秒显示一次 `line`、前缀键 + S 弹菜单；`conf --remove` 去掉这段并恢复 tmux 默认。
- `fm-pin [<账号>] [--group 船员|常驻] [--relaunch]`：给 [firstmate](https://github.com/kunchenguid/firstmate) 用，按组换号。不带账号时列出各命令行登录的官方额度，以及船员、常驻两组各用哪个号；带账号时先确认这个登录 `/usage` 能回、没在冷却（`--force` 照样钉）。默认换的是船员组：写 firstmate 的 `config/claude-account`，每个二副自己家里的那份也一起改，快照跟着换到这个号；之后新起的船员用它，已经在跑的不变。`--group 常驻` 换的是二副本身（`config/secondmate-accounts/<id>/claude-account`），每个二副重启后才生效，加 `--relaunch` 会通过 firstmate 的 `bin/fm-control.sh` 重启空闲的那些。
- `quota-snapshot [--refresh] [--account 账号] [--out 文件]`：把一个号的官方百分比写成 quota-axi 的缓存格式，firstmate 的 quota-axi 通过 `QUOTA_AXI_SNAPSHOT` 读它，不碰登录和钥匙串（见下面）。`schedule [--every 10]` / `unschedule` 定时刷新（macOS 用 launchd，Windows 用任务计划程序）；`status` 看钉的号、文件和定时。

**额度面板：** `claude-move usage` 把几个号放在一起看，告诉你该换到哪个：
- 冷却和恢复时间：撞到 5 小时或每周上限时，Claude Code 会把官方提示和恢复时间写进会话记录，面板读的就是它，所以能看到“每周额度用完，10-24 10:00 恢复”，以及每周几点重置。
- 用量：把 `~/.claude/projects` 和每个已登录的命令行目录（`~/.claude-*`）里的回复按最近 5 小时和本周加起来，按 API 价折算，只用来比较几个号谁用得多，不是账单，也不是套餐百分比。桌面 App 的回复算给当时登录的那个号（App 自己的日志里记着它在用哪个账号），命令行的回复算给它当时所在的配置目录的账号，会话被拷进 `~/.claude` 给桌面 App 接着用以后也一样（别处的目录用 `--config` 加）。
- 官方百分比：`claude-move usage --refresh` 对每个登录过的命令行配置目录（`~/.claude` 和 `~/.claude-*`）各跑一次官方的 `/usage`，拿到和套餐用量页一样的数据：这 5 小时、本周、按模型分的每周额度。`/usage` 是本地命令，不耗额度；claude-move 只是运行命令行，碰不到登录信息。另外 `claude-move watch install` 可以装一个状态栏记录器，命令行每刷新一次状态栏就记一次（你原来的状态栏照常显示）；桌面 App 的 Code 页不运行状态栏脚本。

- 套餐：每个号旁边标出 Pro、Max 5x 或 Max 20x（来自命令行登录缓存的账号资料）。建议换哪个号时按套餐大小算本周剩多少，不只看百分比。

每个号在自己的命令行配置目录里登录一次，就能看到所有号的官方百分比：

```bash
CLAUDE_CONFIG_DIR=~/.claude-work claude    # 进去后输入 /login，用这个号登录
```

每个号换一个目录名（`~/.claude-personal` 等）照做一遍，然后运行 `claude-move usage --refresh --html`。
只算这台 Mac 上的 Claude Code，网页聊天和别的设备上的用量算不进来。

**面板长什么样：**
- 每个号一张卡片，上面一颗像墨水一样慢慢流动的球。颜色跟着这个号最紧的那项官方额度走：用得少是蓝，往上经过青、绿、黄，75% 是琥珀，90% 和 95%（发通知的地方）转红，用完或冷却中是深红；数字变的时候，颜色沿着这条渐变走过去。没有官方百分比的号是银灰色，颜色从不估算。大数字是那项额度的已用百分比，下面的小标签切换看哪一项；冷却中的号显示几点恢复。
- 按钮都是图标。鼠标停在上面（包括卡片右上角的 ✓ 和时钟），就会说明它做什么、官方数据是多久前取的。
- **总消耗：** 所有账号按 API 价折算的用量热力图，近 26 周每天一格，旁边是一周里每个小时平均用多少；点某一天能看是哪些项目用的。Claude Code 默认 30 天后删会话记录，claude-move 会把每天的数留在缓存里，所以热力图从你开始用的那天起慢慢填满。
- **接下来 7 天：** 每个号一条线，每项官方额度在它重置的时间点上有个圆点（颜色看那项用了多少），冷却中的号有条红条一直到恢复。刻度在“现在”附近拉开，接下来几个小时看得清楚。
- **搜会话**（右上角）：按标题搜所有号在桌面 App 里的会话。搜到别的号的会话，旁边有个按钮能把它拷到桌面 App 现在登录的号（会关掉再重开 App）。下面接着是终端会话，按聊过的内容搜（`find`），每条有“接着做”（`resume`），正在跑的有“过去”，还能复制手动接上的命令。
- **终端会话**（卡片下面）：这台 Mac 上正在跑的 Claude Code 会话，所有命令行登录都算（`ps`），置顶的在最前，然后是忙的，每 10 秒刷新；图钉按钮把它置顶或取消，“过去”打开它所在的 tmux 窗口。旁边的按钮给 tmux 窗口起名（`tmux name`），以及装上 / 撤掉 `~/.tmux.conf` 那段（`tmux conf`，装之前先给你看内容）。列表来自 Claude Code 给运行中进程记的 `sessions/<pid>.json`，这个格式没有文档，以后可能会变。
- **放进 Claude Code 里（cmove mod）**：同样的终端会话列表、额度和搜索，也可以作为 mod 放在 Claude Code 的对话旁边，代码在 [`mod/`](mod/)。状态栏显示各号额度，`/cm` 打开在跑的会话（📌 置顶、✎ 起名、→ 过去），`/cm-find 关键词` 搜索并接着做。“搬会话”页把桌面 App 的会话拷到 App 现在登录的号：第一次按只预览要搬什么，第二次按才会关掉 App、搬（先备份）、再打开。背后是 `claude-move to --app`，它独立运行，所以 App 关掉也不会打断它。上次搬家也能在这里同样两下撤回。按钮背后跑的是 claude-move，所以本体要先装上。安装：在终端会话里输入 `/plugin install cmove --marketplace Layla-NL/claude-move`。
- **快捷键：** 1–9 打开对应卡片的终端，/ 搜索，R 刷新官方百分比，Esc 关闭。
- 浏览器标签页显示桌面 App 登录的那个号：图标是它的球，标题是它的数字。
- 底部 Dock 里的“点缀”调节球里第二种颜色的多少；右上角能切换浅色 / 深色 / 跟随系统，以及中文 / English。这几项都存在 `~/.config/claude-move/look.json`，下次打开还是你选的。

**撞上限自动续接：** `claude-move run <账号>` 用这个号的命令行登录启动 `claude`，会话 id 由它事先定好，然后盯着这个会话的记录（子代理的也算）。一出现官方的限额提示，就挨个问别的命令行登录的 `/usage`，挑没在冷却、剩得最多的那个；然后停掉 `claude`，把会话记录复制到那个号的目录（那边原来有这个会话的话，先另存到 `~/.config/claude-move/run-backups`），在那边 `claude --resume <id>` 接上，并发一句“接着做”。原来那份记录不动。没有能换的号时，`claude` 原样留着，并弹通知告诉你。`--rc` 让每一段都是用账号名字命名的 Remote Control 会话。面板上勾选“打开的终端撞到额度上限时自动换号接着干”，打开终端的按钮就会走 `run`。只对命令行版有效，桌面 App 的登录还是你自己点；后台任务和正在跑的工具调用不会跟过去，新号拿到的是对话本身，从那里接着做。这样轮换几个号是否允许，取决于 Anthropic 对你这个套餐的条款，用之前先看一下。

**面板里全都能做（不用开命令行）：** 每张卡片可以改名；有命令行登录的号可以“装/卸状态栏记录器”（会改这个登录的 `settings.json`，点之前会问你）；没有命令行登录的号有“加命令行登录”：弹出终端窗口跑官方的 `claude auth login --claudeai`，登录目录是新建的 `~/.claude-<名字>`，你在浏览器里登录，面板认出来后自动给它起名。卡片下面的 Dock 里还有：
- **迁移：** 选择来源、目标和范围（最近 3 天、7 天、全部，或者只迁移勾选的），预览后执行；桌面 App 开着的话会先退出、迁移完再打开。
- **撤销：** 列出备份，每个都能一键撤销那次迁移。
- **各账号的会话**，以及 **命令行会话导入桌面 App**（面板版的 `import-cli`）。
- **自动续接的会话：** 每个 `run` 会话现在在哪个号、什么时候换过。
- **诊断：** 就是 `doctor`，能修的旁边有修复按钮；还有“添加另一个账号的命令行登录”。
- **通知：** 开关、阈值、测试通知。
- **firstmate 船员**（有 `~/Developer/firstmate` 时出现）：船员用哪个号、快照和定时刷新，每个号一个“钉给船员”按钮，还有“现在刷新快照”。船员在用的那张卡片，名字旁边有个锚。
- **检查更新：** 你点了才去 GitHub 看最新发布，不下载任何东西。

每个按钮都只做固定的事，页面发来的每个值（账号、备份、会话 id、名字、目录名）都先和本机实际有的对一遍。

**通知和自检：** 官方百分比一更新就检查要不要通知，来源是各命令行登录里的状态栏记录器（`CLAUDE_CONFIG_DIR=~/.claude-work claude-move watch install`）或 `usage --refresh`。`claude-move doctor` 会列出还缺什么。

**firstmate：** firstmate 派活前用 quota-axi 看 Claude 额度。quota-axi 自己读要钥匙串授权；给它 `QUOTA_AXI_SNAPSHOT=<文件>` 就只读这个文件。claude-move 用已有的官方数据写这个文件：

```bash
claude-move fm-pin outlook             # 船员用 ~/.claude-outlook，快照跟着它
claude-move fm-pin gmail --group 常驻   # 二副重启后用 gmail
claude-move quota-snapshot schedule    # 每 10 分钟刷新一次
export QUOTA_AXI_SNAPSHOT=~/.cache/claude-move/quota-axi-snapshot.json   # 写进 firstmate 的启动脚本
```

- 文件是 quota-axi 的缓存格式：一条不带账号 key 的 Claude 记录（firstmate 给 Claude 船员绑的就是这一行），窗口是 `five_hour`、`seven_day`，按模型的周额度是 `model:<id>`，`refreshedAt` 是 `/usage` 回答的时间。先写临时文件再改名，只有你自己能读。
- 写哪个号看 firstmate 的 `config/claude-account`，钉的号和快照不会对不上。
- 保鲜：定时任务每次问这个登录的 `/usage`（不耗额度），别的登录每小时问一次。这个登录装了状态栏记录器的话，船员干活时也会顺手更新，最多一分钟一次。quota-axi 在窗口重置前都把快照当新的用，所以 `/usage` 连续失败一小时（退出登录、电脑睡太久），文件会挪成 `….stale`：firstmate 看到的是“没有 Claude 额度数据”，而不是旧数。没有官方数据时什么都不写，命令非零退出。
- 每次写入记在 `~/.cache/claude-move/quota-snapshot.log`（账号、两个百分比、`refreshedAt`）。
- 换号还是你来：船员用的号过 90%、95% 时，通知会写出本周剩得最多的号和对应的 `fm-pin` 命令。不会自动给船员换号：firstmate 规定这个文件只由船长改，而且自动轮换几个号，Anthropic 的条款未必允许。

**副本和轨迹：** 桌面会话只有一份历史：所有桌面账号读的是 `~/.claude` 里同一份记录，迁移只拷指向它的那张列表卡片。终端会话换到另一个登录（`resume --to`、`run`、整组换号）时，会整份拷进那个登录的文件夹；每次都用最新的那份覆盖那边的旧副本（覆盖前存到 `~/.config/claude-move/run-backups`），所以只要同一时间只在一边接着聊，历史就还是一条线。副本不会自动合并，claude-move 也一个都不删。

claude-move 每拷一次，都记进 `~/.config/claude-move/moves.jsonl`：什么时候、哪个会话、从哪个号或文件夹到哪个、多大、被覆盖的那份存在哪。

```bash
claude-move dupes                    # 哪些会话在不止一个文件夹里有副本，副本和备份各占多少
claude-move trail d767de1f           # 一个会话：现在的副本、哪些桌面列表里有它、搬过的路径、旧版本
claude-move dupes --max-copies 2 --max-mb 1024   # 面板提示的上限
```

超过上限时面板顶部会出提示；工具栏的“副本”列出所有副本，每个会话都能看轨迹。Claude Code 自己会按 `cleanupPeriodDays`（默认 30 天）清掉各文件夹里的旧记录。

**Codex：** Codex 的登录和 Claude 的放在一起管。Codex 没有按号分开的会话列表，所以不搬会话，别的都一样。每个 Codex 文件夹（`~/.codex`，以及通过 `CODEX_HOME` 用的另一个登录 `~/.codex-<名字>`）只读它的会话记录：每个会话是哪个号跑的（`creator_account_id`），以及 Codex 一边跑一边写下的官方额度（`rate_limits`：本周和 5 小时窗口、套餐、credits）。从不打开它的 `auth.json`。

```bash
claude-move codex                    # 每个 Codex 号：套餐、官方百分比、重置时间、credits、文件夹、建议用哪个
claude-move codex login work         # 在 ~/.codex-work 登录另一个号（新窗口里跑 codex login）
claude-move codex term work          # 用这个登录打开 Codex，在它上次用的文件夹里
claude-move name 320d codex-main     # 像别的号一样给 Codex 号起名
```

`usage`（以及 `usage --json`、面板卡片、mod 的状态栏）在 Claude 的号后面列出 Codex 的号，75/90/95% 的通知也管它们。`ps`、面板的在跑列表和 mod 都会列出在跑的 Codex 会话（macOS 和 Linux，看每个 Codex 进程开着的会话文件），忙还是空闲、在哪个 tmux 窗口；`find` 能搜它们里聊过的内容，`resume <id>` 用 `codex resume` 在它自己的文件夹和登录里接着做。置顶、起名、分组对它们一样有用；整组换号时，组里的 Codex 会话不动。

**不做的事：** 不搬 artifact、项目这类存在 claude.ai 上的东西（它们跟着创建它的账号走）；从不读、不用登录凭据（`usage` 只读会话记录、账号 id 和桌面 App 日志里写着当前账号的那几行；`watch install` 只在你运行时改 `settings.json`，`watch uninstall` 会把原来的状态栏放回去）；会话里点过的“这次允许”不会带过去。

中文提示会在系统语言是中文时自动出现，也可以用 `CLAUDE_MOVE_LANG=zh` 指定。
