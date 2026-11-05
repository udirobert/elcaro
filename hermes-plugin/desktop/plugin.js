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

function fmtTime(ts) {
  if (!ts) return '--:--:--'
  const d = new Date(ts * 1000)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function ChainBadge({ verify }) {
  if (!verify) return null
  const ok = verify.ok
  const color = ok ? '#46a758' : '#e5484d'
  return jsx('span', {
    className: 'rounded px-1.5 py-0.5 text-[0.625rem] font-semibold',
    style: { color, border: `1px solid ${color}` },
    title: `${verify.checked} entries checked, ${verify.broken} broken`,
    children: ok ? `chain ✓ ${verify.checked}` : `TAMPERED ${verify.broken}`,
  })
}

function EdgeRow({ e }) {
  const edge = (e.edges || [])[0] || {}
  const token = String(edge.token || '?')
  const origin = String(edge.origin_sha256 || '?').slice(0, 10)
  return jsxs('div', {
    className:
      'flex flex-col gap-0.5 rounded border border-(--ui-border) px-2 py-1.5',
    style: { borderLeft: '3px solid #8e4ec6' },
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between gap-2',
        children: [
          jsx('span', {
            className: 'font-mono text-[0.75rem]',
            style: { color: '#8e4ec6' },
            children: '⚡ propagation',
          }),
          jsx('span', {
            className: 'text-[0.625rem] text-(--ui-text-tertiary)',
            children: fmtTime(e.ts),
          }),
        ],
      }),
      jsx('div', {
        className: 'text-[0.6875rem] text-(--ui-text-tertiary)',
        children: `canary ${token.slice(0, 18)}… minted by ${origin}… (scored ${
          edge.origin_score ?? '?'
        }) resurfaced in ${e.tool_name || '?'}`,
      }),
    ],
  })
}

function VerdictRow({ e }) {
  if (e.type === 'edge') return jsx(EdgeRow, { e })
  const honeypot = (e.flagged_techniques || []).includes('decoy_exfiltration')
  const color = honeypot ? '#e5484d' : LEVEL_COLOR[e.risk_level] || LEVEL_COLOR.unknown
  const techs = (e.flagged_techniques || []).join(', ') || 'none'
  const label = honeypot
    ? 'HONEYPOT'
    : e.surface === 'tool_args'
      ? 'args-block'
      : e.quarantined
        ? 'quarantined'
        : 'scanned'
  return jsxs('div', {
    className: 'flex flex-col gap-0.5 rounded border border-(--ui-border) px-2 py-1.5',
    style: honeypot ? { borderColor: '#e5484d' } : {},
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between gap-2',
        children: [
          jsx('span', {
            className: 'font-mono text-[0.75rem]',
            children: `${e.tool_name || '?'}`,
          }),
          jsxs('span', {
            className: 'flex items-center gap-1.5',
            children: [
              jsx('span', {
                className: 'text-[0.625rem] text-(--ui-text-tertiary)',
                children: fmtTime(e.ts),
              }),
              jsx('span', {
                className: 'rounded px-1.5 py-0.5 text-[0.625rem] font-semibold',
                style: { color, border: `1px solid ${color}` },
                children: `${e.risk_level || '?'} ${Number(e.risk_score || 0).toFixed(2)}`,
              }),
            ],
          }),
        ],
      }),
      jsx('div', {
        className: 'text-[0.6875rem] text-(--ui-text-tertiary)',
        children: `${label} · ${techs}${e.signature ? ' · signed' : ''}${
          e.session_id ? ` · sess ${String(e.session_id).slice(0, 8)}` : ''
        }`,
      }),
    ],
  })
}

function ReceiptRow({ e }) {
  return jsxs('div', {
    className: 'flex items-center justify-between gap-2 text-[0.6875rem]',
    children: [
      jsx('span', {
        className: 'font-mono text-(--ui-text-tertiary)',
        children: `${e.tool_name || '?'} ${Number(e.risk_score || 0).toFixed(2)}`,
      }),
      jsx('span', {
        className: 'text-(--ui-text-tertiary)',
        children: `${fmtTime(e.ts)} · sha ${String(e.content_sha256 || '').slice(0, 8)}… ✓`,
      }),
    ],
  })
}

function ThreatLogPane() {
  const [data, setData] = useState({ entries: [], total: 0, quarantined: 0 })
  const [stats, setStats] = useState(null)
  const [verify, setVerify] = useState(null)
  const [decoy, setDecoy] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [showReceipts, setShowReceipts] = useState(false)
  const [error, setError] = useState('')

  const refresh = () => {
    if (!_ctx) return
    Promise.all([
      _ctx.rest('/verdicts?n=50'),
      _ctx.rest('/stats'),
      _ctx.rest('/verify'),
      _ctx.rest('/decoy'),
      _ctx.rest('/receipts?n=10'),
    ])
      .then(([v, s, c, d, r]) => {
        setData(v || { entries: [] })
        setStats(s || null)
        setVerify(c || null)
        setDecoy(d || null)
        setReceipts((r && r.receipts) || [])
        setError('')
      })
      .catch((e) => setError(String(e)))
  }
  useEffect(() => {
    refresh()
    const off = host.onEvent('plugin.elcaro.verdict.logged', refresh)
    return typeof off === 'function' ? off : undefined
  }, [])

  const edges = data.entries.filter((e) => e.type === 'edge')
  const decoyHits = decoy?.hits || 0

  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-3 text-sm',
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between gap-2',
        children: [
          jsx('div', { className: 'font-medium', children: 'Elcaro threat log' }),
          jsxs('div', {
            className: 'flex items-center gap-1.5',
            children: [
              jsx(ChainBadge, { verify }),
              jsx('button', {
                type: 'button',
                className: 'rounded border border-(--ui-border) px-2 py-0.5 text-[0.6875rem]',
                onClick: refresh,
                children: 'refresh',
              }),
            ],
          }),
        ],
      }),
      jsx('div', {
        className: 'text-[0.6875rem] text-(--ui-text-tertiary)',
        children:
          `${data.quarantined} quarantined / ${data.total} scanned` +
          (stats?.signed ? ` · ${stats.signed} signed` : '') +
          (edges.length ? ` · ${edges.length} propagation` : ''),
      }),
      decoy
        ? jsx('div', {
            className: 'text-[0.6875rem]',
            style: { color: decoyHits > 0 ? '#e5484d' : '#46a758' },
            children: decoy.armed
              ? decoyHits > 0
                ? `◉ honeypot sprung — ${decoyHits} exfiltration attempt(s) caught`
                : '◉ honeypot armed — service-credentials.env is bait'
              : '◌ honeypot not materialized',
          })
        : null,
      edges.length
        ? jsx('div', {
            className: 'rounded px-2 py-1 text-[0.6875rem]',
            style: { color: '#8e4ec6', border: '1px solid #8e4ec6' },
            children: `⚡ ${edges.length} propagation edge(s) — an injection resurfaced across tool calls`,
          })
        : null,
      error
        ? jsx('div', { className: 'text-[0.6875rem] text-(--ui-text-tertiary)', children: error })
        : null,
      jsxs('div', {
        className: 'flex flex-col gap-1.5 overflow-y-auto',
        children: data.entries.length
          ? data.entries.map((e, i) => jsx(VerdictRow, { e, key: i }))
          : [
              jsx('div', {
                className: 'text-[0.75rem] text-(--ui-text-tertiary)',
                children: 'No verdicts yet — tool results will be scanned as they arrive.',
              }),
            ],
      }),
      receipts.length
        ? jsxs('div', {
            className: 'mt-auto flex flex-col gap-1 border-t border-(--ui-border) pt-2',
            children: [
              jsx('button', {
                type: 'button',
                className: 'text-left text-[0.6875rem] font-medium text-(--ui-text-tertiary)',
                onClick: () => setShowReceipts(!showReceipts),
                children: `${showReceipts ? '▾' : '▸'} signed receipts (${receipts.length}) — clean scans, verifiable offline`,
              }),
              showReceipts
                ? jsxs('div', {
                    className: 'flex flex-col gap-1',
                    children: receipts
                      .slice(0, 5)
                      .map((e, i) => jsx(ReceiptRow, { e, key: i })),
                  })
                : null,
            ],
          })
        : null,
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
    const off = host.onEvent('plugin.elcaro.verdict.logged', load)
    return () => {
      clearInterval(t)
      if (typeof off === 'function') off()
    }
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
