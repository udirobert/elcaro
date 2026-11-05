// Elcaro — Desktop threat-log pane + status-bar chip.
// Disk-plugin ESM; imports only @hermes/plugin-sdk and react/jsx-runtime.
import { host } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'
import { useEffect, useState } from 'react'

let _ctx = null

const LEVEL_COLOR = {
  dangerous: '#e5484d',
  suspicious: '#f5a524',
  low: '#46a758',
  safe: '#46a758',
  unknown: '#888888',
}

function VerdictRow({ e }) {
  const color = LEVEL_COLOR[e.risk_level] || LEVEL_COLOR.unknown
  const techs = (e.flagged_techniques || []).join(', ') || 'none'
  return jsxs('div', {
    className: 'flex flex-col gap-0.5 rounded border border-(--ui-border) px-2 py-1.5',
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between gap-2',
        children: [
          jsx('span', { className: 'font-mono text-[0.75rem]', children: e.tool_name || '?' }),
          jsx('span', {
            className: 'rounded px-1.5 py-0.5 text-[0.625rem] font-semibold',
            style: { color, border: `1px solid ${color}` },
            children: `${e.risk_level || '?'} ${Number(e.risk_score || 0).toFixed(2)}`,
          }),
        ],
      }),
      jsx('div', {
        className: 'text-[0.6875rem] text-(--ui-text-tertiary)',
        children: `${e.type === 'edge' ? 'propagation ⚡' : e.surface === 'tool_args' ? 'args-block' : e.quarantined ? 'quarantined' : 'scanned'} · ${techs}${e.signature ? ' · signed' : ''}`,
      }),
    ],
  })
}

function ThreatLogPane() {
  const [data, setData] = useState({ entries: [], total: 0, quarantined: 0 })
  const [error, setError] = useState('')

  const refresh = () => {
    if (!_ctx) return
    _ctx.rest('/verdicts?n=50')
      .then((d) => { setData(d || { entries: [] }); setError('') })
      .catch((e) => setError(String(e)))
  }
  useEffect(() => {
    refresh()
    host.onEvent('plugin.elcaro.verdict.logged', refresh)
  }, [])

  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-3 text-sm',
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between',
        children: [
          jsx('div', { className: 'font-medium', children: 'Elcaro threat log' }),
          jsx('button', {
            type: 'button',
            className: 'rounded border border-(--ui-border) px-2 py-0.5 text-[0.6875rem]',
            onClick: refresh,
            children: 'refresh',
          }),
        ],
      }),
      jsx('div', {
        className: 'text-[0.6875rem] text-(--ui-text-tertiary)',
        children: `${data.quarantined} quarantined / ${data.total} scanned`,
      }),
      error
        ? jsx('div', { className: 'text-[0.6875rem] text-(--ui-text-tertiary)', children: error })
        : null,
      jsxs('div', {
        className: 'flex flex-col gap-1.5 overflow-y-auto',
        children: data.entries.length
          ? data.entries.map((e, i) => jsx(VerdictRow, { e, key: i }))
          : [jsx('div', {
              className: 'text-[0.75rem] text-(--ui-text-tertiary)',
              children: 'No verdicts yet — tool results will be scanned as they arrive.',
            })],
      }),
    ],
  })
}

function StatusChip() {
  const [q, setQ] = useState(null)
  useEffect(() => {
    const load = () => {
      if (!_ctx) return
      _ctx.rest('/stats').then((d) => setQ(d?.quarantined ?? 0)).catch(() => setQ(null))
    }
    load()
    const t = setInterval(load, 30000)
    host.onEvent('plugin.elcaro.verdict.logged', load)
    return () => clearInterval(t)
  }, [])
  if (q === null) return null
  return jsx('button', {
    type: 'button',
    className: 'px-1.5 text-[0.6875rem]',
    style: { color: q > 0 ? '#e5484d' : '#46a758' },
    title: `${q} result(s) quarantined by elcaro`,
    children: `◉ ${q}`,
  })
}

export default {
  id: 'elcaro',
  name: 'Elcaro',
  register(ctx) {
    _ctx = ctx
    ctx.register({
      id: 'threat-log',
      area: 'panes',
      title: 'threat log',
      data: { placement: 'right', width: '300px' },
      render: () => jsx(ThreatLogPane, {}),
    })
    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 131,
      render: () => jsx(StatusChip, {}),
    })
  },
}
