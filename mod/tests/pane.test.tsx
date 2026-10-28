import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'cmove',
  component: 'Pane',
  requestId: 'claude-move',
  props: {
    title: 'claude-move',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

const PS = [
  { pid: 1, sid: 'aaaaaaaa-1', name: 'main', title: '二副·群聊', status: 'busy', project: '~/fm', tmux: 'firstmate:15.0', pin: true, group: '' },
  { pid: 2, sid: 'bbbbbbbb-2', name: 'outlook', title: 'claude-move 维护', status: 'idle', project: '~/cm', tmux: '', pin: false, group: '实验' },
]
const USAGE = {
  pick: 'main',
  rows: [
    { acct: 'a', name: 'main', plan: 'Max 20x', cool: null, week_usd: 9, official: { at: 1, rows: [{ kind: 'weekly_all', percent: 18, resets_at: 2 }] } },
    { acct: 'b', name: 'gmail', plan: 'Max 20x', cool: null, week_usd: 9, official: null },
  ],
}

const DESK = {
  signed: 'g', last_move: null,
  rows: [
    { acct: 'g', name: 'gmail', last: 1, live: 0 },
    { acct: 'o', name: 'outlook', last: 3, live: 12 },
    { acct: 'm', name: 'main', last: 2, live: 4 },
  ],
}

// claude-move stands in: each command answers what the real one prints, and every argv is kept
function fakeTool(on: any, ran: string[][]) {
  on('process.run', (_: unknown, e: { argv: string[] }) => {
    ran.push([...e.argv])
    const out = e.argv[1] === 'ps' && e.argv[2] === '--json' ? JSON.stringify(PS)
      : e.argv[1] === 'usage' ? JSON.stringify(USAGE)
      : e.argv[1] === 'list' ? JSON.stringify(DESK)
      : e.argv[1] === 'to' && e.argv.includes('--dry-run') ? 'From outlook to gmail: 1 session(s)\n  add: 额度快照  [10-28 15:00]\n'
      : e.argv[1] === 'to' ? 'claude-move takes it from here\n'
      : e.argv[1] === 'find' ? JSON.stringify([{ sid: 'cccccccc-3', name: 'main', project: '~/x', title: '额度快照', last: 0, snippet: '…额度…', live: '' }])
      : 'done\n'
    return { value: { exitCode: 0, stdout: out, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.status', () => ({ value: undefined }))
}

test('the pane lists running sessions, and its buttons run claude-move', async ($, on) => {
  const ran: string[][] = []
  fakeTool(on, ran)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'refresh' })

  expect((await ui.find({ type: 'Text', text: /二副·群聊/ }))?.text).toContain('二副·群聊')
  expect((await ui.find({ type: 'Text', text: /main/ }))?.text).toContain('18%')
  expect((await ui.find({ type: 'Text', text: /^实验$/ }))?.text).toBe('实验')

  await ui.press({ key: 'pin-aaaaaaaa-1' })
  expect(ran).toContainEqual(['claude-move', 'ps', '--unpin', 'aaaaaaaa-1'])
  await ui.press({ key: 'go-aaaaaaaa-1' })
  expect(ran).toContainEqual(['claude-move', 'ps', '--go', 'firstmate:15.0'])
  // a session outside tmux has no Go there
  expect(await ui.find({ type: 'Button', key: 'go-bbbbbbbb-2' })).toBeUndefined()
  await ui.unmount()
})

test('search finds a session and resumes it', async ($, on) => {
  const ran: string[][] = []
  fakeTool(on, ran)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'tab-find' })
  await ui.input({ key: 'q', text: '额度', kind: 'submit' })

  expect(ran).toContainEqual(['claude-move', 'find', '--json', '--limit', '30', '额度'])
  expect((await ui.find({ type: 'Text', text: /额度快照/ }))?.text).toContain('额度快照')
  await ui.press({ key: 'res-cccccccc-3' })
  expect(ran).toContainEqual(['claude-move', 'resume', 'cccccccc-3'])
  await ui.unmount()
})

test('the phone gets the list without fields', async ($, on) => {
  fakeTool(on, [])
  const ui = await $.ui.mount({ ...PANE, surface: 'mobile' })
  await ui.press({ key: 'refresh' })
  expect(await ui.find({ type: 'Button', key: 'name-aaaaaaaa-1' })).toBeUndefined()
  expect((await ui.find({ type: 'Text', text: /二副·群聊/ }))?.text).toContain('二副·群聊')
  await ui.unmount()
})

test('moving shows what would change first, and quits the app only on the second press', async ($, on) => {
  const ran: string[][] = []
  fakeTool(on, ran)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'tab-move' })
  expect((await ui.find({ type: 'Text', text: /gmail/ }))?.text).toContain('gmail')

  // the most recently used other account is the source; main is one press away
  await ui.press({ key: 'span-7' })
  await ui.press({ key: 'move-go' })
  expect(ran.at(-1)).toEqual(['claude-move', 'to', 'g', '--from', 'o', '--days', '7', '--dry-run'])
  expect((await ui.find({ type: 'Text', text: /额度快照/ }))?.text).toContain('额度快照')
  await ui.press({ key: 'move-go' })
  expect(ran.at(-2)).toEqual(['claude-move', 'to', 'g', '--from', 'o', '--days', '7', '--app'])
  expect(ran.at(-1)).toEqual(['claude-move', 'list', '--json'])

  // choosing again disarms
  await ui.press({ key: 'src-m' })
  await ui.press({ key: 'move-go' })
  expect(ran.at(-1)).toEqual(['claude-move', 'to', 'g', '--from', 'm', '--days', '7', '--dry-run'])
  await ui.press({ key: 'span-all' })
  await ui.press({ key: 'move-go' })
  expect(ran.at(-1)).toEqual(['claude-move', 'to', 'g', '--from', 'm', '--all', '--dry-run'])

  await ui.press({ key: 'move-undo' })
  expect(ran.at(-1)).toEqual(['claude-move', 'undo', '--dry-run'])
  await ui.press({ key: 'move-undo' })
  expect(ran.at(-2)).toEqual(['claude-move', 'undo', '--app'])
  expect(ran.at(-1)).toEqual(['claude-move', 'list', '--json'])
  await ui.unmount()
})
