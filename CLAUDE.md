# Maintaining claude-move

If `HANDOFF.md` exists next to this file, read it first: it holds the local state (what is pushed, what is not, which accounts this Mac has).

## Rules

- Single file, standard library only, runs on macOS's own Python 3.9. No new dependencies.
- It also runs on Windows. Anything that calls a macOS tool (`open`, `osascript`, `ps`, `.command` files, the Dock) needs a `WIN` branch next to it; read and write files as UTF-8. GitHub Actions runs the tests on Windows, so keep them free of sh-only commands (use the `py_cmd`/`stub` helpers in the tests).
- Copy only: never delete session entries on either account; back up the target before writing; keep `undo` working. The one exception is the copies tool (`dupes`, the panel's Copies), one item at a time and only when the user picks it: archiving moves an older copy aside (never a session's newest copy, one in use, or the `~/.claude` copy a desktop list opens) and can be put back; deleting is only of archived copies and claude-move's own backups. Each is written to the trail.
- Never read or use login credentials, and never change which account the desktop app is signed into. Official numbers come only from the limit messages in transcripts, the CLI's `/usage`, and the CLI status line's `rate_limits`. Do not show estimated percentages.
- Every user-facing string goes through the `T` table with English and Chinese.
- argparse help strings: write `%%` for a literal percent sign.
- The panel serves 127.0.0.1 only, with a one-time token and a Host check; its buttons do fixed actions only.
- After changing anything inside `Claude Move.app`, drop `Assets.car` and `CFBundleIconName` and re-sign ad hoc (`app install` does this).
- The repo's default app icon stays the generic one in `ICON_PNG`; do not commit Anthropic's mascot.

## Before you commit

```bash
python3 -W error::ResourceWarning -m unittest discover tests
```

Update `CHANGELOG.md` and both language sections of `README.md`. Commit as `Layla <335815953+Layla-NL@users.noreply.github.com>`. Ask the user before pushing, tagging or publishing a release.
