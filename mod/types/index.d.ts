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

export type Tab = 'live' | 'find'

declare module 'claude-code' {
  interface PluginState {
    'cmove': {
      live: Shaped<LiveRow[]>
      quota: Shaped<Quota | null>
      found: Shaped<Found>
      tab: Tab
      note: string
      editing: string
    }
  }
}
