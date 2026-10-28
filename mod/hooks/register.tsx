import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Desk, Found, Hit, LiveRow, Mv, Quota, QuotaRow, Span, Tab } from '../types'

// The mod draws; claude-move does the work. Every action is one claude-move command, so the
// rules claude-move keeps (copy only, back up first, never read credentials) hold here too.

const PANE = 'claude-move'
const live = atom({ plugin: 'cmove', key: 'live' } as const, [], { shape: 'live-1' })
const quota = atom({ plugin: 'cmove', key: 'quota' } as const, null, { shape: 'quota-1' })
const found = atom({ plugin: 'cmove', key: 'found' } as const, { q: '', rows: [] }, { shape: 'found-1' })
const tab = atom({ plugin: 'cmove', key: 'tab' } as const, 'live' as Tab)
const note = atom({ plugin: 'cmove', key: 'note' } as const, '')
const editing = atom({ plugin: 'cmove', key: 'editing' } as const, '')
const desk = atom({ plugin: 'cmove', key: 'desk' } as const, null, { shape: 'desk-1' })
const mv = atom({ plugin: 'cmove', key: 'mv' } as const, { src: '', span: '3', armed: '', log: '' } as Mv, { shape: 'mv-1' })

const T = {
  pane: ['claude-move', 'claude-move'],
  live: ['Sessions', '会话'],
  find: ['Search', '搜索'],
  refresh: ['Refresh', '刷新'],
  none: ['No Claude Code session is running.', '现在没有在跑的 Claude Code 会话。'],
  ungrouped: ['Not in a group', '未分组'],
  missing: ['claude-move is not installed: see github.com/Layla-NL/claude-move',
            '没找到 claude-move：先装上它（github.com/Layla-NL/claude-move）'],
  week: ['week', '本周'],
  cool: ['cooling', '冷却'],
  pick: ['use', '建议'],
  q: ['what was said…', '聊过的内容…'],
  noHit: ['Nothing found.', '没搜到。'],
  pin: ['Pin to the top', '置顶'],
  unpin: ['Unpin', '取消置顶'],
  name: ['Name it', '起名'],
  go: ['Go there', '过去'],
  resume: ['Resume', '接着做'],
  naming: ['name: ', '名字：'],
  cmdOpen: ['Running sessions, quota and search (claude-move)', '在跑的会话、额度和搜索（claude-move）'],
  cmdFind: ['Search what was said in terminal sessions (claude-move find)', '按聊过的内容搜终端会话（claude-move find）'],
  opened: ['claude-move pane opened.', '已打开 claude-move 面板。'],
  move: ['Move', '搬会话'],
  signedIn: ['The desktop app is signed into', '桌面 App 现在登录的是'],
  noSigned: ["Can't tell which account the desktop app is signed into: open the app once.",
             '看不出桌面 App 登录的是哪个号：先打开一次 App。'],
  noFolder: ['Its Code page has no list yet: open Code once in the app, then come back.',
             '这个号的 Code 页还没有列表：先在 App 里打开一次 Code 页。'],
  noSource: ['No other account has sessions to copy.', '别的号没有可搬的会话。'],
  from: ['from', '从'],
  span: ['used in', '范围'],
  d3: ['3 days', '3 天'],
  d7: ['7 days', '7 天'],
  all: ['all', '全部'],
  moveTo: ['Copy into', '搬到'],
  confirm: ['Press again: quit the app, copy, reopen', '再按一次：关掉 App，搬完再打开'],
  undo: ['Undo the last move', '撤回上次搬家'],
  undoConfirm: ['Press again: quit the app, undo, reopen', '再按一次：关掉 App，撤回后再打开'],
  lastMove: ['Last move', '上次搬家'],
  ok: ['went through', '搬好了'],
  failed: ['did not go through', '没搬成'],
  copyOnly: ['It copies and never deletes, and backs up the list first; the first press only shows what would change.',
             '只拷贝不删除，搬之前先备份；第一次按只是预览，什么都不改。'],
} as const
let zh = false
const t = (k: keyof typeof T) => T[k][zh ? 1 : 0]

let bin: string[] | null = null // how to start claude-move, found once
let paneOpen = false

async function cm($: EngineInterface, args: string[], timeoutMs = 60000) {
  // on PATH, else where its installer puts it
  const tries = bin ? [bin] : [['claude-move'], async () => [`${(await $.env.get('HOME')) ?? ''}/.local/bin/claude-move`]]
  for (const tryOne of tries) {
    try {
      const b = typeof tryOne === 'function' ? await tryOne() : tryOne
      const r = await $.process.run([...b, ...args], { timeoutMs })
      bin = b
      return { ok: r.exitCode === 0, out: r.stdout, err: r.stderr.trim() }
    } catch {
      if (bin) break // it started before: this was a timeout, not a missing tool
    }
  }
  return { ok: false, out: '', err: bin ? '' : t('missing') }
}

function percent(r: QuotaRow) {
  const wk = r.official?.rows.find(m => m.kind === 'weekly_all')
  return wk && wk.percent !== null ? `${Math.round(wk.percent)}%` : ''
}

function clock(sec: number) {
  const d = new Date(sec * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function day(sec: number) {
  const d = new Date(sec * 1000)
  return `${d.getMonth() + 1}-${d.getDate()} ${clock(sec)}`
}

function quotaLine(q: Quota) {
  return q.rows
    .map(r => `${r.name} ${r.cool ? `${t('cool')}→${clock(r.cool.until)}` : percent(r) || '–'}`)
    .join(' · ')
}

async function refreshQuota($: EngineInterface) {
  const r = await cm($, ['usage', '--json'], 180000)
  if (!r.ok) {
    if (r.err) $.ui.status(`claude-move: ${r.err.split('\n').pop()}`)
    return
  }
  const q = JSON.parse(r.out) as Quota
  await update($, quota, () => q)
  $.ui.status(`${quotaLine(q)}${q.pick ? ` · ${t('pick')} ${q.pick}` : ''}`)
}

async function refreshLive($: EngineInterface) {
  const r = await cm($, ['ps', '--json'])
  if (r.ok) await update($, live, () => JSON.parse(r.out) as LiveRow[])
  else if (r.err) await update($, note, () => r.err)
}

async function act($: EngineInterface, args: string[]) {
  const r = await cm($, args)
  await update($, note, () => (r.out.trim() || r.err).split('\n').pop() ?? '')
  await refreshLive($)
}

async function search($: EngineInterface, q: string) {
  const words = q.trim()
  await update($, tab, () => 'find' as Tab)
  if (!words) return
  await update($, note, () => '…')
  const r = await cm($, ['find', '--json', '--limit', '30', ...words.split(/\s+/)], 180000)
  await update($, found, () => ({ q: words, rows: r.ok ? (JSON.parse(r.out) as Hit[]) : [] }))
  await update($, note, () => (r.ok ? '' : r.err.split('\n').pop() ?? ''))
}

async function refreshDesk($: EngineInterface) {
  const r = await cm($, ['list', '--json'])
  if (r.ok) await update($, desk, () => JSON.parse(r.out) as Desk)
  else if (r.err) await update($, note, () => r.err)
}

const spanArgs = (s: Span) => (s === 'all' ? ['--all'] : ['--days', s])

// The first press shows what would change (a dry run) and arms the button; the second does it with --app,
// which inside the desktop app hands the work to a claude-move of its own, as quitting the app ends this mod.
async function press($: EngineInterface, which: 'move' | 'undo', args: string[]) {
  const m = await read($, mv)
  const armed = m.armed === which
  const r = await cm($, [...args, armed ? '--app' : '--dry-run'], 180000)
  const next: Mv['armed'] = armed || !r.ok ? '' : which
  await update($, mv, cur => ({ ...cur, armed: next, log: (r.out.trim() || r.err).trim() }))
  if (armed) await refreshDesk($)
}

async function openPane($: EngineInterface) {
  paneOpen = true
  await $.ui.open({ id: PANE, title: t('pane') })
  void refreshLive($)
}

function ago(ms: number) {
  const m = Math.max(0, Math.round((Date.now() - ms) / 60000))
  return m < 60 ? `${m}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const lang = (await $.env.get('CLAUDE_MOVE_LANG')) ?? (await $.env.get('LANG')) ?? ''
    zh = lang.toLowerCase().startsWith('zh')
    await $.command.register({ name: 'cm', description: t('cmdOpen') })
    await $.command.register({ name: 'cm-find', description: t('cmdFind') })
    // quota: now, then every five minutes; claude-move reads only what was appended since
    $.clock.after(1000, () => void refreshQuota($))
    $.clock.every(5 * 60000, () => void refreshQuota($))
    // the running list only while the pane is open
    $.clock.every(15000, () => {
      if (paneOpen) void refreshLive($)
    })

    return next(e)
  })

  on('command.run', { command: 'cm' }, async $ => {
    await update($, tab, () => 'live' as Tab)
    await openPane($)

    return { text: t('opened') }
  })

  on('command.run', { command: 'cm-find' }, async ($, e) => {
    await openPane($)
    void search($, e.args)

    return { text: t('opened') }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) paneOpen = false

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const els = $.ui.resolve(e)
    const { Box, Text, Button } = els
    // the phone draws no field yet (its table hands out a stand-in): /cm-find searches there
    const Input = e.surface !== 'mobile' && 'Input' in els ? els.Input : null
    const [rows, q, hits, which, msg, edit, d, m] = await Promise.all([
      read($, live), read($, quota), read($, found), read($, tab), read($, note), read($, editing), read($, desk), read($, mv),
    ])
    const room = Math.max(3, (e.viewport?.rows ?? 30) - 8)

    const head = (
      <Box flexDirection="column">
        {q && (
          <Box flexWrap="wrap" columnGap={2}>
            {q.rows.map(r => (
              <Text color={r.cool ? 'red' : undefined} dimColor={!r.cool && !percent(r)}>
                <Text bold>{r.name}</Text> {r.cool ? `${t('cool')}→${clock(r.cool.until)}` : `${t('week')} ${percent(r) || '–'}`}
              </Text>
            ))}
            {q.pick && <Text dimColor>{t('pick')} {q.pick}</Text>}
          </Box>
        )}
        <Box columnGap={1}>
          <Button key="tab-live" variant={which === 'live' ? 'primary' : undefined}
            onPress={() => update($, tab, () => 'live' as Tab)}>{`${t('live')} ${rows.length}`}</Button>
          <Button key="tab-find" variant={which === 'find' ? 'primary' : undefined}
            onPress={() => update($, tab, () => 'find' as Tab)}>{t('find')}</Button>
          <Button key="tab-move" variant={which === 'move' ? 'primary' : undefined}
            onPress={async () => { await update($, tab, () => 'move' as Tab); await refreshDesk($) }}>{t('move')}</Button>
          <Button key="refresh" plain label="↻" hotkey="r"
            onPress={() => Promise.all([refreshLive($), refreshQuota($), refreshDesk($)])} />
        </Box>
      </Box>
    )

    const grouped = rows.some(r => r.group)
    const liveList = (
      <Box flexDirection="column">
        {rows.length === 0 && <Text dimColor>{t('none')}</Text>}
        {rows.slice(0, room).map((r, i, shown) => (
          <Box key={`row-${r.sid}`} flexDirection="column">
            {grouped && !r.pin && (!shown[i - 1] || shown[i - 1]?.pin || shown[i - 1]?.group !== r.group) && (
              <Text dimColor bold>{r.group || t('ungrouped')}</Text>
            )}
            <Box columnGap={1}>
              <Text color={r.status === 'busy' ? 'red' : undefined} dimColor={r.status !== 'busy'}>
                {r.status === 'busy' ? '●' : '○'}
              </Text>
              <Button key={`pin-${r.sid}`} plain dimColor={!r.pin} label={r.pin ? '📌' : '·'}
                onPress={() => act($, ['ps', r.pin ? '--unpin' : '--pin', r.sid])} />
              <Box flexShrink={0}><Text bold>{r.name}</Text></Box>
              <Box flexGrow={1} flexShrink={1}>
                <Text wrap="truncate-end">{r.title || r.sid.slice(0, 8)} <Text dimColor>{r.project}</Text></Text>
              </Box>
              {Input && (
                <Button key={`name-${r.sid}`} plain dimColor label="✎"
                  onPress={() => update($, editing, cur => (cur === r.sid ? '' : r.sid))} />
              )}
              {r.tmux && (
                <Button key={`go-${r.sid}`} plain label="→"
                  onPress={() => act($, ['ps', '--go', r.tmux])} />
              )}
            </Box>
            {Input && edit === r.sid && (
              <Input key={`label-${r.sid}`} label={t('naming')} value={r.title} autoFocus
                onSubmit={async (v: string) => {
                  await update($, editing, () => '')
                  await act($, ['ps', '--label', r.sid, v])
                }} />
            )}
          </Box>
        ))}
      </Box>
    )

    const findList = (
      <Box flexDirection="column">
        {Input && (
          <Input key="q" placeholder={t('q')} value={hits.q} autoFocus submitLabel={t('find')}
            onSubmit={(v: string) => search($, v)} />
        )}
        {hits.q && hits.rows.length === 0 && msg !== '…' && <Text dimColor>{t('noHit')}</Text>}
        {hits.rows.slice(0, Math.max(1, Math.floor(room / 2))).map(hit => (
          <Box key={`hit-${hit.sid}`} flexDirection="column">
            <Box columnGap={1}>
              <Box flexShrink={0}><Text bold>{hit.name}</Text></Box>
              <Box flexGrow={1} flexShrink={1}>
                <Text wrap="truncate-end">{hit.title} <Text dimColor>{hit.project} · {ago(hit.last)}</Text></Text>
              </Box>
              {hit.live && !hit.live.startsWith('pid ')
                ? <Button key={`hgo-${hit.sid}`} plain label="→" onPress={() => act($, ['ps', '--go', hit.live])} />
                : !hit.live && <Button key={`res-${hit.sid}`} plain label="↩" onPress={() => act($, ['resume', hit.sid])} />}
            </Box>
            {hit.snippet && <Text dimColor wrap="truncate-end">  {hit.snippet}</Text>}
          </Box>
        ))}
      </Box>
    )

    const signed = d?.rows.find(r => r.acct === d.signed)
    const named = (acct: string) => d?.rows.find(r => r.acct === acct)?.name || acct.slice(0, 8)
    const sources = (d?.rows ?? []).filter(r => r.acct !== d?.signed && r.live > 0).sort((a, b) => b.last - a.last)
    const src = sources.find(r => r.acct === m.src) ?? sources[0]
    const choose = (patch: Partial<Mv>) => update($, mv, (cur): Mv => ({ ...cur, ...patch, armed: '', log: '' }))
    const moveArgs = signed && src ? ['to', signed.acct, '--from', src.acct, ...spanArgs(m.span)] : []
    const movePage = (
      <Box flexDirection="column" rowGap={1}>
        {!d ? <Text dimColor>…</Text>
          : !d.signed ? <Text>{t('noSigned')}</Text>
          : (
            <Box flexDirection="column">
              <Text>{t('signedIn')} <Text bold>{named(d.signed)}</Text></Text>
              {!signed && <Text>{t('noFolder')}</Text>}
            </Box>
          )}
        {signed && sources.length === 0 && <Text dimColor>{t('noSource')}</Text>}
        {signed && src && (
          <Box flexDirection="column" rowGap={1}>
            <Box columnGap={1} flexWrap="wrap">
              <Text dimColor>{t('from')}</Text>
              {sources.map(r => (
                <Button key={`src-${r.acct}`} variant={r.acct === src.acct ? 'primary' : undefined}
                  onPress={() => choose({ src: r.acct })}>{`${named(r.acct)} ${r.live}`}</Button>
              ))}
            </Box>
            <Box columnGap={1}>
              <Text dimColor>{t('span')}</Text>
              {(['3', '7', 'all'] as Span[]).map(s => (
                <Button key={`span-${s}`} variant={m.span === s ? 'primary' : undefined}
                  onPress={() => choose({ span: s })}>{t(s === '3' ? 'd3' : s === '7' ? 'd7' : 'all')}</Button>
              ))}
            </Box>
            <Box columnGap={1} flexWrap="wrap">
              <Button key="move-go" variant="primary"
                onPress={() => press($, 'move', moveArgs)}>
                {m.armed === 'move' ? t('confirm') : `${t('moveTo')} ${named(signed.acct)}`}
              </Button>
              <Button key="move-undo" variant={m.armed === 'undo' ? 'primary' : undefined}
                onPress={() => press($, 'undo', ['undo'])}>
                {m.armed === 'undo' ? t('undoConfirm') : t('undo')}
              </Button>
            </Box>
            <Text dimColor>{t('copyOnly')}</Text>
          </Box>
        )}
        {d?.last_move && (
          <Text dimColor>{t('lastMove')} {day(d.last_move.at)}: {d.last_move.ok ? t('ok') : t('failed')}</Text>
        )}
        {m.log && (
          <Box flexDirection="column">
            {m.log.split('\n').slice(0, Math.max(3, room - 8)).map(line => <Text dimColor wrap="truncate-end">{line}</Text>)}
          </Box>
        )}
      </Box>
    )

    return (
      <Box flexDirection="column" rowGap={1}>
        {head}
        {which === 'live' ? liveList : which === 'find' ? findList : movePage}
        {msg && <Text dimColor wrap="truncate-end">{msg}</Text>}
      </Box>
    )
  })
}
