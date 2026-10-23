# Changelog

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
