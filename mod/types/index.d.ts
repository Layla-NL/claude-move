// What `claude-move ps --json` prints, one running session.
export type LiveRow = {
  pid: number
  sid: string
  name: string
  title: string
  status: string
  project: string
  tmux: string
  pin: boolean
}

// One official meter, as `claude-move usage --json` prints it.
export type Meter = { kind: string; percent: number | null; resets_at: number | null }

export type QuotaRow = {
  acct: string
  name: string
  plan: string
  cool: { kind: string; until: number } | null
  week_usd: number
  official: { at: number; rows: Meter[] } | null
}

export type Quota = { pick: string | null; rows: QuotaRow[] }

// One hit of `claude-move find --json`; `live` is a tmux target, "pid N", or "".
export type Hit = {
  sid: string
  name: string
  project: string
  title: string
  last: number
  snippet: string
  live: string
}

export type Found = { q: string; rows: Hit[] }

// What `claude-move list --json` prints: the desktop app's account lists, and which one it is signed into.
export type DeskRow = { acct: string; name: string; last: number; live: number }
export type Desk = {
  signed: string | null
  last_move: { at: number; ok: boolean; log: string } | null
  rows: DeskRow[]
}

// The move page: the account to copy from, how far back, and which button waits for its second press.
export type Span = '3' | '7' | 'all'
export type Mv = { src: string; span: Span; armed: '' | 'move' | 'undo'; log: string }

export type Tab = 'live' | 'find' | 'move'

declare module 'claude-code' {
  interface PluginState {
    'cmove': {
      live: Shaped<LiveRow[]>
      quota: Shaped<Quota | null>
      found: Shaped<Found>
      tab: Tab
      note: string
      editing: string
      desk: Shaped<Desk | null>
      mv: Shaped<Mv>
    }
  }
}
