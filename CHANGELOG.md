# Changelog

## 0.2.0
- `undo`: restore the target account's list to its state before the last move (replaced entries back, added entries removed); the state right before the undo is saved too.
- `import-cli`: copy CLI session transcripts (and their side folders) from another config folder into `~/.claude`; never overwrites.
- `to --only`: pick sessions by title text or id prefix.
- `to` lists artifacts the moved sessions published, since those stay with the account that created them.

## 0.1.0
- `list`, `sessions`, `name`, `to` with `--from`, `--days`, `--all`, `--dry-run`; copy only, target backed up first.
