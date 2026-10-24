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
| `claude-move list` | Accounts on this Mac, live/archived session counts, which one was used last |
| `claude-move sessions <account>` | Live sessions of one account |
| `claude-move name <account> <label>` | Give an account a short label, e.g. `work`, `personal` |
| `claude-move to <target> [--from <source>] [--days N] [--all] [--only TEXT] [--dry-run]` | Copy live sessions used in the last N days (default 3) from the source (default: the most recently used account) to the target. `--only` picks sessions by title text or id prefix (repeatable). Lists any artifacts those sessions published, because those stay with the account that created them |
| `claude-move undo [--list] [--backup NAME] [--dry-run]` | Put the target account's list back exactly as it was before the last move: replaced entries are restored, added ones removed. The state right before the undo is saved too |
| `claude-move usage [--refresh] [--html] [--config DIR]` | Quota per account: cooling and reset times, use this week and in the last 5 hours, official % from the CLI. `--refresh` asks `/usage` of each signed-in CLI folder first; `--html` opens a panel page |
| `claude-move panel` | The same panel in your browser, served on 127.0.0.1 only, with a button that moves your sessions after you switch accounts (see below) |
| `claude-move app install [--icon IMAGE] [--no-dock]` | Make `~/Applications/Claude Move.app` and put it in the Dock: double-click it to open the panel, no Terminal needed |
| `claude-move term <account> [--rc]` | Open a Terminal window running Claude Code as that account, with its own CLI login folder (`CLAUDE_CONFIG_DIR=~/.claude-<name>`), in the project folder that account used last. `--rc` starts it as a Remote Control session named after the account, so the Claude phone app signed into the same account can join |
| `claude-move run <account> [--rc] [--resume ID] [-- claude args]` | Run Claude Code as that account; when the session hits a usage limit, move it to the CLI login with the most left and resume it there (see below) |
| `claude-move notify on\|off\|status\|test [--levels 75,90,95]` | macOS notifications when an account's official % passes each level, once per reset window (on by default) |
| `claude-move doctor [--refresh]` | Check labels, CLI logins (and whether `/usage` answers in each), accounts that show up in two folders, desktop accounts without a CLI login, the status line recorder and the app's signature |
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
- "Accent" in the dock sets how much a second color drifts through each ball; it is kept in
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
- `list` 看有哪些账号；`sessions <账号>` 看某个账号的会话；`name <账号> <名字>` 起个好记的名字。
- `to <目标> [--from 来源] [--days N] [--all] [--only 文字] [--dry-run]`：搬最近 N 天（默认 3 天）用过、没归档的会话；`--only` 按标题或 id 挑着搬。搬之前会列出这些会话发布过的 artifact，提醒它们还归创建它的账号。
- `undo [--list] [--backup 名字] [--dry-run]`：把目标账号的列表恢复成上次搬之前的样子，换掉的放回去，新加的拿掉；撤回前的样子也另存一份。
- `import-cli --config 目录 [--project 路径] [--session id] [--days N] [--dry-run]`：把另一个配置目录（比如用 `CLAUDE_CONFIG_DIR=~/.claude-work` 登录的另一个账号）里的命令行会话记录拷到 `~/.claude`，桌面 App 就能打开；从不覆盖。

- `usage [--refresh] [--html] [--config 目录]`：各账号额度面板；`--refresh` 先向每个命令行登录问官方 `/usage`，`--html` 打开网页版。
- `panel`：在浏览器里打开带按钮的面板（只在本机 127.0.0.1 上）。换号时：先在桌面 App 里退出登录、登上新号、打开一次 Code 页，再回面板点黑色的“A → B”按钮。面板会先从 App 日志确认 App 现在登录的确实是 B，然后退出 App、照 `claude-move to B` 搬会话（先备份）、重新打开 App。登录这一步始终由你在 App 里自己点。请在“终端”里运行 `claude-move panel`，不要在桌面 App 的 Claude Code 会话里运行，因为退出 App 会连那个会话一起关掉。有命令行登录的号，卡片上有“打开终端”：弹出一个新终端窗口，在这个号最近用过的项目文件夹里，用它自己的配置目录运行 `claude`（和 `claude-move term <账号>` 一样，不读登录信息）；“打开终端（手机可连）”再加上 `--remote-control <名字>`，手机 Claude App 登录同一个号就能连上。两条命令也都能一键复制。`~/.claude` 和某个 `~/.claude-*` 显示的是同一个号时，用 `~/.claude-*` 那个。
- `app install [--icon 图片] [--no-dock]`：生成 `~/Applications/Claude Move.app` 并放进程序坞，双击就打开面板，不用开终端。它独立运行，从面板退出桌面 App 不会把它关掉；再双击会回到已经开着的面板；页面关掉 30 分钟后自己停。`--icon` 可以换成任意图片当图标。
- `term <账号> [--rc]`：弹出一个终端窗口，在这个号最近用过的项目文件夹里，用它的命令行登录目录（`CLAUDE_CONFIG_DIR=~/.claude-<名字>`）运行 Claude Code；`--rc` 以 Remote Control 会话启动、用账号名字命名，手机 App 登录同一个号就能连上。
- `run <账号> [--rc] [--resume id] [-- claude 的参数]`：用这个号运行 Claude Code，撞到额度上限时把会话搬到剩得最多的号接着干（见下面）。
- `notify on|off|status|test [--levels 75,90,95]`：某个号的官方百分比过 75/90/95% 时弹系统通知，每个重置周期每档只提醒一次（默认开）。
- `doctor [--refresh]`：自检：名字、各命令行登录（以及 `/usage` 能不能用）、同一个号出现在两个目录、有桌面会话却没有命令行登录的号、状态栏记录器、小 App 的签名。
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

**面板长什么样：**
- 每个号一张卡片，上面一颗像墨水一样慢慢流动的球。颜色跟着这个号最紧的那项官方额度走：用得少是蓝，往上经过青、绿、黄，75% 是琥珀，90% 和 95%（发通知的地方）转红，用完或冷却中是深红；数字变的时候，颜色沿着这条渐变走过去。没有官方百分比的号是银灰色，颜色从不估算。大数字是那项额度的已用百分比，下面的小标签切换看哪一项；冷却中的号显示几点恢复。
- 按钮都是图标。鼠标停在上面（包括卡片右上角的 ✓ 和时钟），就会说明它做什么、官方数据是多久前取的。
- **总消耗：** 所有账号按 API 价折算的用量热力图，近 26 周每天一格，旁边是一周里每个小时平均用多少；点某一天能看是哪些项目用的。Claude Code 默认 30 天后删会话记录，claude-move 会把每天的数留在缓存里，所以热力图从你开始用的那天起慢慢填满。
- **接下来 7 天：** 每个号一条线，每项官方额度在它重置的时间点上有个圆点（颜色看那项用了多少），冷却中的号有条红条一直到恢复。刻度在“现在”附近拉开，接下来几个小时看得清楚。
- **搜会话**（右上角）：按标题搜所有号在桌面 App 里的会话。搜到别的号的会话，旁边有个按钮能把它拷到桌面 App 现在登录的号（会关掉再重开 App）。
- **快捷键：** 1–9 打开对应卡片的终端，/ 搜索，R 刷新官方百分比，Esc 关闭。
- 浏览器标签页显示桌面 App 登录的那个号：图标是它的球，标题是它的数字。
- 底部 Dock 里的“点缀”调节球里第二种颜色的多少，存在 `~/.config/claude-move/look.json`。

**撞上限自动续接：** `claude-move run <账号>` 用这个号的命令行登录启动 `claude`，会话 id 由它事先定好，然后盯着这个会话的记录（子代理的也算）。一出现官方的限额提示，就挨个问别的命令行登录的 `/usage`，挑没在冷却、剩得最多的那个；然后停掉 `claude`，把会话记录复制到那个号的目录（那边原来有这个会话的话，先另存到 `~/.config/claude-move/run-backups`），在那边 `claude --resume <id>` 接上，并发一句“接着做”。原来那份记录不动。没有能换的号时，`claude` 原样留着，并弹通知告诉你。`--rc` 让每一段都是用账号名字命名的 Remote Control 会话。面板上勾选“打开的终端撞到额度上限时自动换号接着干”，打开终端的按钮就会走 `run`。只对命令行版有效，桌面 App 的登录还是你自己点；后台任务和正在跑的工具调用不会跟过去，新号拿到的是对话本身，从那里接着做。这样轮换几个号是否允许，取决于 Anthropic 对你这个套餐的条款，用之前先看一下。

**面板里全都能做（不用开命令行）：** 每张卡片可以改名；有命令行登录的号可以“装/卸状态栏记录器”（会改这个登录的 `settings.json`，点之前会问你）；没有命令行登录的号有“加命令行登录”：弹出终端窗口跑官方的 `claude auth login --claudeai`，登录目录是新建的 `~/.claude-<名字>`，你在浏览器里登录，面板认出来后自动给它起名。卡片下面的 Dock 里还有：
- **搬会话：** 选从哪个号搬到哪个号、搬哪些（最近 3 天、7 天、全部，或者勾选），先预览再搬；桌面 App 开着的话会先退出、搬完再打开。
- **撤回搬家：** 列出备份，每个都能一键撤回。
- **各账号的会话**，以及 **命令行会话导入桌面 App**（面板版的 `import-cli`）。
- **自动续接的会话：** 每个 `run` 会话现在在哪个号、什么时候换过。
- **自检：** 就是 `doctor`，能修的旁边有修复按钮；还有“再加一个号的命令行登录”。
- **通知：** 开关、阈值、测试通知。
- **检查更新：** 你点了才去 GitHub 看最新发布，不下载任何东西。

每个按钮都只做固定的事，页面发来的每个值（账号、备份、会话 id、名字、目录名）都先和本机实际有的对一遍。

**通知和自检：** 官方百分比一更新就检查要不要通知，来源是各命令行登录里的状态栏记录器（`CLAUDE_CONFIG_DIR=~/.claude-work claude-move watch install`）或 `usage --refresh`。`claude-move doctor` 会列出还缺什么。

**不做的事：** 不搬 artifact、项目这类存在 claude.ai 上的东西（它们跟着创建它的账号走）；从不读、不用登录凭据（`usage` 只读会话记录、账号 id 和桌面 App 日志里写着当前账号的那几行；`watch install` 只在你运行时改 `settings.json`，`watch uninstall` 会把原来的状态栏放回去）；会话里点过的“这次允许”不会带过去。

中文提示会在系统语言是中文时自动出现，也可以用 `CLAUDE_MOVE_LANG=zh` 指定。
