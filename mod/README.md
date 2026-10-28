# cmove: claude-move inside Claude Code

A Claude Code mod that puts [claude-move](https://github.com/Layla-NL/claude-move) beside the chat. claude-move does the work; the mod draws it.

- **Status line:** each account's official weekly percentage, Codex accounts too, (or when it stops cooling), and which account to use next. Refreshed every five minutes.
- **`/cm`:** a pane with the Claude Code sessions running now, from every CLI login. Busy ones are marked ●, and your groups (`claude-move group`) are listed together. 📌 pins a session to the top, ✎ names it, and → brings up its tmux window.
- **`/cm-find <words>`:** searches what was said in every terminal session. ↩ resumes a hit in a new tmux window or terminal window, and → goes to it if it is running.
- **Move** (a page of `/cm`): after you sign the desktop app into another account, copy your sessions into it from the account you used before. The first press shows what would change; the second quits the app, copies (backing up the list first) and opens the app again. A claude-move running on its own does that, so quitting the app does not stop it, and a notification says how it went. Undo the last move the same way.

It needs claude-move 0.8.3 or newer, on `PATH` or in `~/.local/bin`. Each button runs one claude-move command, so claude-move's rules hold: it copies and never deletes, backs up before it writes, and never reads login credentials.

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

- **状态栏**：每个号（包括 Codex 的号）的官方本周百分比（冷却中的号显示几点恢复），以及建议下一个用哪个号。每 5 分钟刷新一次。
- **`/cm`**：打开一个面板，列出现在在跑的 Claude Code 会话，所有命令行登录都算。忙的会话标 ●，自己建的分组（`claude-move group`）排在一起。📌 置顶，✎ 起名，→ 切到它所在的 tmux 窗口。
- **`/cm-find 关键词`**：按聊过的内容搜所有终端会话。↩ 在新的 tmux 窗口或终端里接着做；会话还在跑的话，→ 直接切过去。
- **搬会话**（`/cm` 里的一页）：桌面 App 登上另一个号以后，把之前那个号的会话拷过来。第一次按只预览要搬什么；第二次按才会关掉 App、搬（先备份列表）、再打开 App。这一步交给独立运行的 claude-move 去做，所以 App 关掉也不会打断，做完会弹通知。上次搬家也能同样两下撤回。

需要 claude-move 0.8.3 或更新的版本，放在 `PATH` 里或 `~/.local/bin`。每个按钮都只运行一条 claude-move 命令，所以 claude-move 的规矩照样成立：只拷贝、不删除，写之前先备份，不读登录凭据。

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
