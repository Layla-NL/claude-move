# Changelog

## 0.8.3
- Codex accounts, beside the Claude ones (nothing is moved: Codex keeps no per-account session list). `codex` lists each Codex account its folders' sessions ran under (`creator_account_id`) with the official numbers Codex writes in them (`rate_limits`: week, 5 hours, plan, credits); `codex login <name>` signs another login into `~/.codex-<name>`; `codex term <account>` opens Codex with one. `auth.json` is never opened. `usage`, `usage --json`, the panel's cards, the mod's status line and the 75/90/95% notifications include them. `ps`, the panel and the mod list running Codex sessions (from the session file each Codex process holds open; macOS and Linux), `find` searches them (the index is rebuilt once) and `resume` resumes one with `codex resume`. `name` also names CLI-only and Codex accounts.
- `group`: your own groups of terminal sessions (`~/.config/claude-move/groups.json`), listed together in `ps`, the panel and the mod. `group <name> --to <account>` moves a whole group to another CLI login: each idle member in tmux quits (SIGTERM, as closing its terminal would) and resumes there, copied first, conversation and id kept. Busy members, members outside tmux, sessions with nothing said yet and firstmate's crews are left, each with what to do. The panel's session list has a group button on each row and a "move this group to" choice on each group.

## 0.8.2
- `fm-pin` switches firstmate's accounts by group. The crews (the default) are pinned in firstmate's `config/claude-account` and now also in each second mate's own home, so the second mates' crews follow. `--group resident` (常驻) pins the second mates themselves through `config/secondmate-accounts/<id>/claude-account`; `--relaunch` relaunches the idle ones with firstmate's `bin/fm-control.sh` so they take it now, and busy ones are left with the command to run later. `fm-pin` without an account shows what each group uses. The panel's firstmate tool has a pin button for each group.
- The mod's Move page: copy the desktop app's sessions into the account it is signed into now, from any other account and over 3 days, 7 days or all. The first press shows what would change, the second quits the app, copies (backup first) and opens it again; Undo the last move works the same way.
- `to --app` / `undo --app`: quit the desktop app first and open it again afterwards. Started inside the app (its Code page, the mod), a copy of claude-move running on its own does it, since quitting the app ends what it started, and a notification says how it went. The log is kept in `~/.config/claude-move/last-move.json`.
- `list --json`: the desktop app's accounts, the one it is signed into, and the last `--app` move.
- The panel opens the desktop app again even when a move fails unexpectedly.

## 0.8.1
- The cmove mod (`mod/`, installed with `/plugin install cmove --marketplace Layla-NL/claude-move`): quota per account in Claude Code's status line, `/cm` for a pane with the running sessions (pin, name, go there), and `/cm-find` to search and resume. Each button runs one claude-move command.
- `usage --json` and `find --json`, which the mod reads.
- Use per account now counts every signed-in CLI folder (`~/.claude-*`), not only `~/.claude`, so the cards include the crews' and other CLI logins' use. A CLI session copied into `~/.claude` for the desktop app keeps its CLI replies under the login they ran in, so they no longer show up as "CLI, account unknown" (the separate CLI card).
- `ps --label <target> <name>`: give a running session a name of your own, kept by claude-move in `~/.config/claude-move/labels.json` (transcripts and Claude Code's own names are not touched). It comes first in `ps`, the tmux menu, the panel and `find`, and windows claude-move names follow it; firstmate's `fm-*` windows keep their names. `""` takes it off.
- `ps --pin <target>...` / `--unpin`: pin running sessions to the top of `ps`, the tmux menu and the panel (📌), in the order they were pinned, kept in `~/.config/claude-move/pins.json`. The panel's live list has a pin button on each row.

## 0.8.0
- `find <words>`: search what was said in every CLI login's terminal sessions (prompts, replies, titles; not tool output) through an index in `~/.cache/claude-move/search.db` (mode 0600) that reads each transcript once and then only what is appended. Hits show account, project, a snippet, whether the session is running, and how to resume it.
- `resume <id> [--to <account>] [--here]`: resume a terminal session in its folder with its login, in a new tmux window or terminal window; `--to` copies it to another CLI login first. A running session is not started twice.
- `ps [--go <target>]`: the Claude Code sessions running now across every CLI login, read from Claude Code's own `sessions/<pid>.json`, with busy/idle and the tmux pane each runs in; `--go` brings one up. Each is named by the name you gave it, else its title, else the window name firstmate gave it.
- `tmux name|line|menu|conf`: name tmux windows after the account and session in them (only windows nobody else named), a status bar line, a session menu, and a `~/.tmux.conf` block (`conf --install`, backed up first; `conf --remove`).
- `term` and the panel's terminal buttons open a tmux window when tmux is running.
- The panel lists running terminal sessions under the cards, with Go there and the tmux buttons, and its search box also finds terminal sessions by what was said, with Resume.

## 0.7.0
- `quota-snapshot`: one account's official numbers in quota-axi's cache format (schema 3, one keyless Claude row: `five_hour`, `seven_day`, `model:<id>` weeks, `refreshedAt` when `/usage` answered), for firstmate's quota-axi through `QUOTA_AXI_SNAPSHOT`. Written atomically, mode 0600, logged in `~/.cache/claude-move/quota-snapshot.log`. Without official numbers it writes nothing and exits non-zero; when `/usage` keeps failing and the numbers are an hour old, the file is moved aside so firstmate sees no quota rather than old quota. `schedule` refreshes it every 10 minutes (a launchd agent on macOS, a scheduled task on Windows), asking the other logins' `/usage` once an hour; the status line recorder in the pinned login also rewrites it, at most once a minute.
- `fm-pin [<account>]`: lists the CLI logins with their official numbers, or pins firstmate's Claude crews to one (`config/claude-account`) after checking it answers `/usage` and is not cooling; the snapshot follows the pin.
- At 90 and 95%, the notification for the crews' account names the login with the most of this week left and its `fm-pin` command.
- The panel has a firstmate crews tool (pin, snapshot, schedule, how it works) when firstmate is there, and an anchor on the card the crews use.
- The status line recorder keeps the per-model weekly meters `/usage` gave (the status line has none), and `/usage` rows keep the model id.

## 0.6.1
- A new default icon in the panel's look: a ball drawn by the panel's own shader, frosted glass over its lower half, and the move button.

## 0.6.0
- The panel is redesigned. Each account is a card with a ball drawn by a small WebGL shader, its color following the account's tightest official limit along one ramp (blue, teal, green, yellow, amber at 75%, red at 90 and 95%, deep red when used up), with frosted glass over its lower half; no official % means silver. Tabs on the card switch between limits and the color travels along the ramp. Buttons are icons with a tooltip; the tools sit in a dock under the cards. Without WebGL, or with reduced motion, the ball is a still gradient.
- Total use: a heatmap of every account's use at API list prices over 26 weeks, and by hour of the week; click a day for its projects (a worktree counts as its repository). Daily figures stay in the cache after Claude Code deletes old transcripts (the cache keeps 26 weeks and is rebuilt once).
- The browser tab shows the desktop app's account: its ball as the icon, its number in the title.
- Next 7 days: when each account's official limits reset and how long cooling lasts, on one timeline.
- Search desktop sessions of every account by title, and copy a found one into the account the desktop app is signed into.
- Keys in the panel: 1–9 open a card's terminal, / searches, R refreshes, Esc closes.
- `bar install` (macOS): a menu bar ball through SwiftBar or xbar, colored like the panel, with every account in its menu; it reads only the official numbers already saved.
- A weekly summary notification, the first time each week the panel or `usage` reads your use: last week's total at API prices, the account that used most, the busiest day. It follows `notify on|off`.
- `panel --demo`: the panel with sample accounts, for screenshots or a first look; it reads nothing on this computer and its buttons do nothing.
- Settings on the panel, kept in `~/.config/claude-move/look.json`: accent (how much a second color drifts through each ball), theme (light, dark or the system's) and language (English or Chinese, over the system's).

## 0.5.0
- Windows. The desktop app's data is found under `%APPDATA%\Claude` or, for the Microsoft Store build, `%LOCALAPPDATA%\Packages\…\LocalCache\Roaming\Claude` (the one with the newest session list), its log next to it. The desktop app is told from the `claude` CLI by its install path; its ✕ only hides it in the notification area and nothing outside it can ask it to quit, so the move button ends its process tree (the panel says that anything running in its Code tab stops) and starts it again (its launcher, else the Start menu entry). Finding, ending and reopening the Store build, and the toast, were tried on Windows 11. Terminal buttons write a `.cmd` script and open a console window that stays open; copied commands are PowerShell. Notifications are toasts. `app install` makes a Start menu shortcut (and a desktop one) that runs the panel under `pythonw`, with the icon shrunk to 256 px and stored as `.ico`. `run` ends claude's whole process tree at a limit (npm installs start it through a `.cmd`). The status line recorder is written so both Git Bash and cmd can run it, and an existing status line is chained through Git Bash. Chinese is picked from the Windows display language. Checking whether the panel is already running no longer uses `os.kill(pid, 0)`, which on Windows would end that process.
- Files claude-move writes and reads are UTF-8 on every system.
- Reset times from `/usage` text in UTC no longer need a time zone database; other named zones fall back to local time when there is none (Windows without the `tzdata` package), which is the zone the CLI prints.
- Tests run on Windows (Python 3.9 and 3.14) and macOS in GitHub Actions; the fake `claude` in the tests is Python.

## 0.4.0
- `usage --refresh`: official percentages for every account, from the CLI's own `/usage` command run once per signed-in config folder (`~/.claude`, `~/.claude-*`, `--config`). Shows every meter the plan reports (5-hour session, week, per-model week); a meter at 100% counts as cooling until it resets; the official weekly reset time is used when known. No quota is used and claude-move never reads the login.
- The panel's meters turn red at 80%.
- `panel`: the panel served on 127.0.0.1 with a one-time token, with a button that, after you sign the desktop app into another account yourself, checks the app really is signed into it, quits the app, moves the sessions (backup first) and reopens the app. Cards can copy the CLI command for their account; a button refreshes the official %.
- `app install`: a double-clickable `Claude Move.app` (with icon, in the Dock) that opens the panel without Terminal; `--icon` for a custom image. The panel runs one instance at a time, `--idle` stops it after its page is gone, and when it is started inside the desktop app (its terminal pane or a Code session) it relaunches on its own so quitting the app cannot stop it mid-move.
- `term <account> [--rc]` and "Open in Terminal" buttons on each panel card: a new Terminal window running `claude` with that account's own CLI config folder, in the project folder the account used last (its newest desktop session or CLI transcript; a worktree counts as its repo). `--rc` / "reachable from phone" adds `--remote-control <label>`; both commands can be copied. It opens a small `.command` file, so it needs no Automation permission. A `~/.claude-*` folder now wins over `~/.claude` when both show the same account (the profile cached in `~/.claude.json` can outlive its login).
- `run <account>`: runs `claude` with that account's CLI login and watches the session's transcript. At the official limit message it asks the other CLI logins' `/usage`, copies the transcript into the freest one (backing up any copy already there), and resumes the session there with a note to continue; if no account is free, `claude` is left alone. `--rc`, `--resume`, extra arguments after `--`. The panel's "switch account and go on" checkbox makes its Open in Terminal buttons use it.
- `notify`: macOS notifications when an official meter passes 75/90/95% (`--levels`), once per reset window, checked whenever the status line recorder or `/usage` updates the %; `on`, `off`, `status`, `test`.
- `doctor [--refresh]`: labels, CLI logins and whether `/usage` answers in each, accounts in two folders (a stale `~/.claude` profile is called harmless), desktop accounts without a CLI login, the status line recorder per login, the app's signature.
- The panel does everything without a terminal: rename accounts, install or remove the status line recorder per CLI login, add a CLI login (the CLI's own `claude auth login` in a new `~/.claude-<name>` folder, named once it shows up), move sessions with a preview and a pick list, undo a move, browse each account's sessions, copy CLI sessions into the desktop app, follow `run` sessions, run the check-up with fix buttons, set notifications, and look for a newer release. Each value the page sends is checked against this Mac.
- Fixed: a stray parenthesis in the panel script stopped all of its buttons; a test now parses the page script with node when it is installed.
- `/usage` text is read when its structured report comes back without rows.
- Each account shows its plan (Pro, Max 5x, Max 20x) from the profile the CLI caches; the suggested account is the one with the most quota left this week by plan size.

## 0.3.0
- `usage`: quota per account. Cooling and reset times from the official limit messages in transcripts; use in the last 5 hours and this week, priced at API list prices for comparison; desktop replies credited to the account signed into the app at the time (from the app's log), CLI replies to `--config` folders; suggests which account to switch to. `--html` writes and opens a panel page. Transcripts are read incrementally (cached by file offset).
- `watch install` / `uninstall`: a status line recorder that saves the official 5-hour/weekly % from the Claude Code CLI per account, keeping any existing status line. The desktop app's Code tab does not run status line scripts.

## 0.2.0
- `undo`: restore the target account's list to its state before the last move (replaced entries back, added entries removed); the state right before the undo is saved too.
- `import-cli`: copy CLI session transcripts (and their side folders) from another config folder into `~/.claude`; never overwrites.
- `to --only`: pick sessions by title text or id prefix.
- `to` lists artifacts the moved sessions published, since those stay with the account that created them.

## 0.1.0
- `list`, `sessions`, `name`, `to` with `--from`, `--days`, `--all`, `--dry-run`; copy only, target backed up first.
