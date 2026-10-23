# Changelog

## 0.4.0
- `usage --refresh`: official percentages for every account, from the CLI's own `/usage` command run once per signed-in config folder (`~/.claude`, `~/.claude-*`, `--config`). Shows every meter the plan reports (5-hour session, week, per-model week); a meter at 100% counts as cooling until it resets; the official weekly reset time is used when known. No quota is used and claude-move never reads the login.
- The panel's meters turn red at 80%.
- `panel`: the panel served on 127.0.0.1 with a one-time token, with a button that, after you sign the desktop app into another account yourself, checks the app really is signed into it, quits the app, moves the sessions (backup first) and reopens the app. Cards can copy the CLI command for their account; a button refreshes the official %.
- `app install`: a double-clickable `Claude Move.app` (with icon, in the Dock) that opens the panel without Terminal; `--icon` for a custom image. The panel runs one instance at a time, `--idle` stops it after its page is gone, and when it is started inside the desktop app (its terminal pane or a Code session) it relaunches on its own so quitting the app cannot stop it mid-move.
- `term <account> [--rc]` and "Open in Terminal" buttons on each panel card: a new Terminal window running `claude` with that account's own CLI config folder, in the project folder the account used last (its newest desktop session or CLI transcript; a worktree counts as its repo). `--rc` / "reachable from phone" adds `--remote-control <label>`; both commands can be copied. It opens a small `.command` file, so it needs no Automation permission. A `~/.claude-*` folder now wins over `~/.claude` when both show the same account (the profile cached in `~/.claude.json` can outlive its login).
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
