# Changelog

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
