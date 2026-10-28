# cmove: claude-move inside Claude Code

A Claude Code mod that puts [claude-move](https://github.com/Layla-NL/claude-move) beside the chat. claude-move does the work; the mod draws it.

- **Status line:** each account's official weekly percentage (or when it stops cooling), and which account to use next. Refreshed every five minutes.
- **`/cm`:** a pane with the Claude Code sessions running now, from every CLI login. Busy ones are marked ●. 📌 pins a session to the top, ✎ names it, and → brings up its tmux window.
- **`/cm-find <words>`:** searches what was said in every terminal session. ↩ resumes a hit in a new tmux window or terminal window, and → goes to it if it is running.

It needs claude-move 0.8.1 or newer, on `PATH` or in `~/.local/bin`. Each button runs one claude-move command, so claude-move's rules hold: it copies and never deletes, backs up before it writes, and never reads login credentials.

Moving sessions between desktop-app accounts stays in claude-move (`claude-move panel` or `claude-move to`). That step quits and reopens the desktop app, and a mod runs inside it.

## Install

At the prompt of a terminal session:

```
/plugin install cmove --marketplace Layla-NL/claude-move
```

From a shell:

```
claude plugin install cmove --marketplace Layla-NL/claude-move
```

In the desktop app, where `/plugin` does not run: click + next to the prompt box, then Plugins. Choose Add marketplace with `Layla-NL/claude-move`, then Add plugin.

---

# cmove：放进 Claude Code 里的 claude-move

这是一个 Claude Code 的 mod，把 [claude-move](https://github.com/Layla-NL/claude-move) 放到对话旁边。干活的是 claude-move，mod 只负责显示。

- **状态栏**：每个号的官方本周百分比（冷却中的号显示几点恢复），以及建议下一个用哪个号。每 5 分钟刷新一次。
- **`/cm`**：打开一个面板，列出现在在跑的 Claude Code 会话，所有命令行登录都算。忙的会话标 ●。📌 置顶，✎ 起名，→ 切到它所在的 tmux 窗口。
- **`/cm-find 关键词`**：按聊过的内容搜所有终端会话。↩ 在新的 tmux 窗口或终端里接着做；会话还在跑的话，→ 直接切过去。

需要 claude-move 0.8.1 或更新的版本，放在 `PATH` 里或 `~/.local/bin`。每个按钮都只运行一条 claude-move 命令，所以 claude-move 的规矩照样成立：只拷贝、不删除，写之前先备份，不读登录凭据。

桌面 App 换号搬会话仍然用 claude-move 本体（`claude-move panel` 或 `claude-move to`）。搬会话要关掉再重开桌面 App，而 mod 就运行在 App 里面。

## 安装

在终端会话的输入框里：

```
/plugin install cmove --marketplace Layla-NL/claude-move
```

在 shell 里：

```
claude plugin install cmove --marketplace Layla-NL/claude-move
```

桌面 App 里不能用 `/plugin`：点输入框旁边的 +，再点 Plugins。选 Add marketplace，填 `Layla-NL/claude-move`，然后点 Add plugin。
