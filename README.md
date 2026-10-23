# claude-move

Switched the Claude desktop app to another account and the Code tab's session list is empty?
Your sessions are still on disk. `claude-move` copies the list over to the account you are using now.

[中文说明](#中文)

> Unofficial. Not affiliated with or endorsed by Anthropic. It depends on the desktop app's
> on-disk layout, which may change in any release. macOS only.

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

## Switching accounts

1. Sign the desktop app into the new account and open the Code tab once, so its folder exists.
2. Quit the desktop app completely (Claude menu → Quit).
3. Run `claude-move to <new account>`.
4. Reopen the app.

## Commands

| Command | What it does |
|---|---|
| `claude-move list` | Accounts on this Mac, live/archived session counts, which one was used last |
| `claude-move sessions <account>` | Live sessions of one account |
| `claude-move name <account> <label>` | Give an account a short label, e.g. `work`, `personal` |
| `claude-move to <target> [--from <source>] [--days N] [--all] [--only TEXT] [--dry-run]` | Copy live sessions used in the last N days (default 3) from the source (default: the most recently used account) to the target. `--only` picks sessions by title text or id prefix (repeatable). Lists any artifacts those sessions published, because those stay with the account that created them |
| `claude-move undo [--list] [--backup NAME] [--dry-run]` | Put the target account's list back exactly as it was before the last move: replaced entries are restored, added ones removed. The state right before the undo is saved too |
| `claude-move import-cli --config DIR [--project PATH] [--session ID] [--days N] [--dry-run]` | Copy CLI session transcripts from another config folder (e.g. a second account under `CLAUDE_CONFIG_DIR=~/.claude-work`) into `~/.claude`, so the desktop app can open them. Never overwrites. A project folder name that starts with `-` needs `--project=-Users-me-app` |

`<account>` is a label, or the first few characters of the account id shown by `list`.
Labels are stored in `~/.config/claude-move/accounts.json`.

## What it does not do

- It does not move artifacts, projects or anything stored on claude.ai; those stay with the
  account that created them.
- It does not touch your CLI config directories (`~/.claude*`) or credentials.
- Permissions you granted inside a session ("allow for this session") are not carried over.

## Tests

```bash
python3 -m unittest discover tests
```

## License

MIT

---

## 中文

Claude 桌面 App 换了账号登录以后，Code 页左边的会话列表空了？会话其实都还在本机，`claude-move` 把列表搬到你现在用的账号下。

> 非官方工具，和 Anthropic 没有关系。它依赖桌面 App 在磁盘上的存放方式，App 更新后可能失效。只支持 macOS。

**为什么会空：** 会话**列表**按账号存在 `~/Library/Application Support/Claude/claude-code-sessions/<账号>/<组织>/` 下面；会话的**完整记录**在 `~/.claude/projects/`，不属于任何账号。换号以后什么都没丢，只是新账号下面没有指向这些会话的条目。

**安全：** 只复制，不删任何东西；写之前先把目标账号的整份列表备份；目标那边更新的不覆盖；桌面 App 开着时不动手；`--dry-run` 只看不改。

**换号步骤：**
1. 桌面 App 用新账号登录，打开一次 Code 页；
2. 完全退出桌面 App（菜单 Claude → 退出）；
3. 运行 `claude-move to <新账号>`；
4. 重新打开 App。

**命令：**
- `list` 看有哪些账号；`sessions <账号>` 看某个账号的会话；`name <账号> <名字>` 起个好记的名字。
- `to <目标> [--from 来源] [--days N] [--all] [--only 文字] [--dry-run]`：搬最近 N 天（默认 3 天）用过、没归档的会话；`--only` 按标题或 id 挑着搬。搬之前会列出这些会话发布过的 artifact，提醒它们还归创建它的账号。
- `undo [--list] [--backup 名字] [--dry-run]`：把目标账号的列表恢复成上次搬之前的样子，换掉的放回去，新加的拿掉；撤回前的样子也另存一份。
- `import-cli --config 目录 [--project 路径] [--session id] [--days N] [--dry-run]`：把另一个配置目录（比如用 `CLAUDE_CONFIG_DIR=~/.claude-work` 登录的另一个账号）里的命令行会话记录拷到 `~/.claude`，桌面 App 就能打开；从不覆盖。

**不做的事：** 不搬 artifact、项目这类存在 claude.ai 上的东西（它们跟着创建它的账号走）；不碰命令行的配置目录和登录凭据；会话里点过的“这次允许”不会带过去。

中文提示会在系统语言是中文时自动出现，也可以用 `CLAUDE_MOVE_LANG=zh` 指定。
