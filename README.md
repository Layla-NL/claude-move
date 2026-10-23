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
| `claude-move usage [--refresh] [--html] [--config DIR]` | Quota per account: cooling and reset times, use this week and in the last 5 hours, official % from the CLI. `--refresh` asks `/usage` of each signed-in CLI folder first; `--html` opens a panel page |
| `claude-move panel` | The same panel in your browser, served on 127.0.0.1 only, with a button that moves your sessions after you switch accounts (see below) |
| `claude-move app install [--icon IMAGE] [--no-dock]` | Make `~/Applications/Claude Move.app` and put it in the Dock: double-click it to open the panel, no Terminal needed |
| `claude-move term <account>` | Open a Terminal window running Claude Code as that account, with its own CLI login folder (`CLAUDE_CONFIG_DIR=~/.claude-<name>`) |
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

### Switching from the panel

`claude-move panel` opens the panel with a switch button. Signing in stays with you, in the app's own sign-in:

1. In the desktop app, log out, sign in with the account you want, and open the Code tab once.
2. In the panel, press "Move sessions from A to B and reopen the app". It checks that the app really is signed
   into B (from the app's log), quits the app, runs the same copy as `claude-move to B` (backup first), and
   reopens the app.

Easiest: run `claude-move app install` once. It makes `~/Applications/Claude Move.app` (in the Dock too); double-click
it and the panel opens. It runs on its own, so quitting the desktop app from the panel does not stop it, a second
double-click brings back the running panel, and it stops by itself 30 minutes after its page is closed.
`--icon` takes any image for the app icon. If you start `claude-move panel` by hand, do it from Terminal, not from
inside a Claude Code session in the desktop app: quitting the app would stop that session too. The panel is served on 127.0.0.1 with a one-time token, so only this Mac can
use it, and its buttons can only quit/reopen the app, move sessions, refresh the official %, and open Terminal.
Each card with a CLI login has "Open in Terminal", which starts `claude` in a new Terminal window with that
account's own config folder (the same as `claude-move term <account>`; nothing about the login is read), and can
also copy that command (`CLAUDE_CONFIG_DIR=~/.claude-work claude`). When `~/.claude` and a `~/.claude-*` folder show
the same account, the `~/.claude-*` one is used.

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

- `usage [--refresh] [--html] [--config 目录]`：各账号额度面板；`--refresh` 先向每个命令行登录问官方 `/usage`，`--html` 打开网页版。
- `panel`：在浏览器里打开带按钮的面板（只在本机 127.0.0.1 上）。换号时：先在桌面 App 里退出登录、登上新号、打开一次 Code 页，再回面板点“把 A 的会话搬到 B，并重开 App”。面板会先从 App 日志确认 App 现在登录的确实是 B，然后退出 App、照 `claude-move to B` 搬会话（先备份）、重新打开 App。登录这一步始终由你在 App 里自己点。请在“终端”里运行 `claude-move panel`，不要在桌面 App 的 Claude Code 会话里运行，因为退出 App 会连那个会话一起关掉。有命令行登录的号，卡片上有“打开终端”：弹出一个新终端窗口，用这个号自己的配置目录运行 `claude`（和 `claude-move term <账号>` 一样，不读登录信息）；也可以一键复制这条启动命令。`~/.claude` 和某个 `~/.claude-*` 显示的是同一个号时，用 `~/.claude-*` 那个。
- `app install [--icon 图片] [--no-dock]`：生成 `~/Applications/Claude Move.app` 并放进程序坞，双击就打开面板，不用开终端。它独立运行，从面板退出桌面 App 不会把它关掉；再双击会回到已经开着的面板；页面关掉 30 分钟后自己停。`--icon` 可以换成任意图片当图标。
- `term <账号>`：弹出一个终端窗口，用这个号的命令行登录目录（`CLAUDE_CONFIG_DIR=~/.claude-<名字>`）运行 Claude Code。
- `watch install` / `watch uninstall`：装上（或卸掉）状态栏记录器，用命令行版时记下官方百分比。

**额度面板：** `claude-move usage` 把几个号放在一起看，告诉你该换到哪个：
- 冷却和恢复时间：撞到 5 小时或每周上限时，Claude Code 会把官方提示和恢复时间写进会话记录，面板读的就是它，所以能看到“每周额度用完，10-24 10:00 恢复”，以及每周几点重置。
- 用量：把 `~/.claude/projects` 里的回复按最近 5 小时和本周加起来，按 API 价折算，只用来比较几个号谁用得多，不是账单，也不是套餐百分比。桌面 App 的回复算给当时登录的那个号（App 自己的日志里记着它在用哪个账号），命令行的回复算给 `--config` 指定的配置目录的账号。
- 官方百分比：`claude-move usage --refresh` 对每个登录过的命令行配置目录（`~/.claude` 和 `~/.claude-*`）各跑一次官方的 `/usage`，拿到和套餐用量页一样的数据：这 5 小时、本周、按模型分的每周额度。`/usage` 是本地命令，不耗额度；claude-move 只是运行命令行，碰不到登录信息。另外 `claude-move watch install` 可以装一个状态栏记录器，命令行每刷新一次状态栏就记一次（你原来的状态栏照常显示）；桌面 App 的 Code 页不运行状态栏脚本。

- 套餐：每个号旁边标出 Pro、Max 5x 或 Max 20x（来自命令行登录缓存的账号资料）。建议换哪个号时按套餐大小算本周剩多少，不只看百分比。

每个号在自己的命令行配置目录里登录一次，就能看到所有号的官方百分比：

```bash
CLAUDE_CONFIG_DIR=~/.claude-work claude    # 进去后输入 /login，用这个号登录
```

每个号换一个目录名（`~/.claude-personal` 等）照做一遍，然后运行 `claude-move usage --refresh --html`。
只算这台 Mac 上的 Claude Code，网页聊天和别的设备上的用量算不进来。

**不做的事：** 不搬 artifact、项目这类存在 claude.ai 上的东西（它们跟着创建它的账号走）；从不读、不用登录凭据（`usage` 只读会话记录、账号 id 和桌面 App 日志里写着当前账号的那几行；`watch install` 只在你运行时改 `settings.json`，`watch uninstall` 会把原来的状态栏放回去）；会话里点过的“这次允许”不会带过去。

中文提示会在系统语言是中文时自动出现，也可以用 `CLAUDE_MOVE_LANG=zh` 指定。
