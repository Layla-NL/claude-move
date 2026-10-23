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
| `claude-move usage [--html] [--config DIR]` | Quota per account: cooling and reset times, use this week and in the last 5 hours, official % recorded from the CLI. `--html` opens a panel page |
| `claude-move watch install` / `uninstall` | Record the official 5-hour/weekly % each time the CLI status line refreshes; keeps your existing status line |
| `claude-move import-cli --config DIR [--project PATH] [--session ID] [--days N] [--dry-run]` | Copy CLI session transcripts from another config folder (e.g. a second account under `CLAUDE_CONFIG_DIR=~/.claude-work`) into `~/.claude`, so the desktop app can open them. Never overwrites. A project folder name that starts with `-` needs `--project=-Users-me-app` |

`<account>` is a label, or the first few characters of the account id shown by `list`.
Labels are stored in `~/.config/claude-move/accounts.json`.

## Quota panel

`claude-move usage` shows each account side by side, so you know which one to switch to:

- **Cooling and reset times.** When an account hits its 5-hour or weekly limit, Claude Code writes the
  official limit message, with the reset time, into the transcript. The panel reads those, so you see
  "weekly limit used up, back at 10-24 10:00" and when each weekly window resets.
- **Use per account.** Replies in `~/.claude/projects` are summed for the last 5 hours and the current week,
  priced at API list prices. This is only for comparing accounts; it is not your bill and not a percentage
  of your plan. Desktop replies are credited to whoever was signed into the desktop app at that moment
  (the app's own log names the account it is using); CLI replies go to the account of the config folder
  you pass with `--config`.
- **Official percentages, from the CLI.** Claude Code hands its status line the official 5-hour and weekly
  percentages for Pro and Max plans. `claude-move watch install` adds a small status line recorder that saves
  them per account (your existing status line keeps showing). The desktop app's Code tab does not run
  status line scripts, so these only update while you use the CLI.

`claude-move usage --html` also writes a panel page and opens it. It counts Claude Code on this Mac only;
claude.ai chat and other devices are not included.

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

- `usage [--html] [--config 目录]`：各账号额度面板，`--html` 打开网页版。
- `watch install` / `watch uninstall`：装上（或卸掉）状态栏记录器，用命令行版时记下官方百分比。

**额度面板：** `claude-move usage` 把几个号放在一起看，告诉你该换到哪个：
- 冷却和恢复时间：撞到 5 小时或每周上限时，Claude Code 会把官方提示和恢复时间写进会话记录，面板读的就是它，所以能看到“每周额度用完，10-24 10:00 恢复”，以及每周几点重置。
- 用量：把 `~/.claude/projects` 里的回复按最近 5 小时和本周加起来，按 API 价折算，只用来比较几个号谁用得多，不是账单，也不是套餐百分比。桌面 App 的回复算给当时登录的那个号（App 自己的日志里记着它在用哪个账号），命令行的回复算给 `--config` 指定的配置目录的账号。
- 官方百分比：Pro 和 Max 用户的 Claude Code 会把官方的 5 小时、每周百分比交给状态栏。`claude-move watch install` 装一个小记录器，按账号存下来，你原来的状态栏照常显示。桌面 App 的 Code 页不运行状态栏脚本，所以只有用命令行版时才会更新。
只算这台 Mac 上的 Claude Code，网页聊天和别的设备上的用量算不进来。

**不做的事：** 不搬 artifact、项目这类存在 claude.ai 上的东西（它们跟着创建它的账号走）；从不读、不用登录凭据（`usage` 只读会话记录、账号 id 和桌面 App 日志里写着当前账号的那几行；`watch install` 只在你运行时改 `settings.json`，`watch uninstall` 会把原来的状态栏放回去）；会话里点过的“这次允许”不会带过去。

中文提示会在系统语言是中文时自动出现，也可以用 `CLAUDE_MOVE_LANG=zh` 指定。
