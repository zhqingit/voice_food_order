import React, { useEffect, useState } from 'react'
import {
  createPromotion,
  deletePromotion,
  listPromotions,
  updatePromotion,
  type PlatformPromotion,
  type PromotionChannels,
  type PromotionKind,
} from '../api/promotionsApi'

const subStyle: React.CSSProperties = { fontSize: 12, color: 'var(--color-text-secondary)' }

function usd(v: string | number): string {
  return `$${Number(v).toFixed(2)}`
}

function terms(p: PlatformPromotion): string {
  const off = p.kind === 'percent' ? `${Number(p.value)}% off` : `${usd(p.value)} off`
  return Number(p.min_subtotal) > 0 ? `${off} orders of ${usd(p.min_subtotal)} or more` : `${off} any order`
}

function limits(p: PlatformPromotion): string {
  const parts = []
  if (p.first_order_only) parts.push('first order only')
  if (p.per_user_limit) parts.push(`${p.per_user_limit}× per customer`)
  parts.push(p.monthly_budget ? `budget ${usd(p.spent_this_month)} / ${usd(p.monthly_budget)} this month` : `${usd(p.spent_this_month)} this month, no budget`)
  return parts.join(' · ')
}

function errorMessage(err: unknown): string {
  const res = (err as { response?: { status?: number; data?: { detail?: string; code?: string } } }).response
  if (res?.status === 422) return 'Check the fields (amount above 0, at most 100%, end date after start).'
  return res?.data?.detail ?? 'Something went wrong.'
}

export function PromotionsRoute(): React.JSX.Element {
  const [promos, setPromos] = useState<PlatformPromotion[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [name, setName] = useState('')
  const [kind, setKind] = useState<PromotionKind>('percent')
  const [value, setValue] = useState('')
  const [minSubtotal, setMinSubtotal] = useState('')
  const [channels, setChannels] = useState<PromotionChannels>('app')
  const [startsOn, setStartsOn] = useState('')
  const [endsOn, setEndsOn] = useState('')
  const [firstOrderOnly, setFirstOrderOnly] = useState(false)
  const [perUser, setPerUser] = useState('')
  const [budget, setBudget] = useState('')

  async function reload(): Promise<void> {
    try {
      setPromos(await listPromotions())
    } catch {
      setError('Failed to load promotions.')
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  async function run(fn: () => Promise<unknown>): Promise<void> {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await reload()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  function handleCreate(e: React.FormEvent): void {
    e.preventDefault()
    const v = Number(value)
    if (!name.trim() || !(v > 0) || (kind === 'percent' && v > 100)) {
      setError('Enter a name and an amount above 0 (at most 100%).')
      return
    }
    void run(async () => {
      await createPromotion({
        name: name.trim(),
        kind,
        value: v.toFixed(2),
        min_subtotal: (Number(minSubtotal) || 0).toFixed(2),
        channels,
        starts_on: startsOn || null,
        ends_on: endsOn || null,
        first_order_only: firstOrderOnly,
        per_user_limit: perUser ? Math.max(1, Math.floor(Number(perUser))) : null,
        monthly_budget: budget ? Number(budget).toFixed(2) : null,
      })
      setName('')
      setValue('')
      setMinSubtotal('')
      setPerUser('')
      setBudget('')
    })
  }

  function handleBudget(p: PlatformPromotion): void {
    const input = window.prompt('Monthly budget in dollars (empty = no budget):', p.monthly_budget ?? '')
    if (input === null) return
    const amount = input.trim() ? Number(input) : null
    if (amount !== null && !(amount > 0)) {
      setError('The budget must be above 0, or empty for none.')
      return
    }
    void run(() => updatePromotion(p.id, { monthly_budget: amount === null ? null : amount.toFixed(2) }))
  }

  return (
    <div>
      <p style={{ ...subStyle, marginTop: 0 }}>
        VoxEats-funded promotions. They apply only when the customer pays online in the app, stack on the store's own
        promotion, and come out of our commission (never more than the commission on the order). All amounts are
        computed by the backend.
      </p>
      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>New platform promotion</h2>
        </div>
        <form className="card-body" onSubmit={handleCreate}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Name customers see</label>
              <input className="form-input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Pay in the app, save 5%" />
            </div>
            <div className="form-group">
              <label className="form-label">Type</label>
              <select className="form-select" value={kind} onChange={(e) => setKind(e.target.value as PromotionKind)}>
                <option value="percent">Percent off</option>
                <option value="amount_off">Dollars off</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{kind === 'percent' ? 'Percent off (%)' : 'Dollars off ($)'}</label>
              <input className="form-input" type="number" min="0.01" step="0.01" value={value} onChange={(e) => setValue(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Minimum order, after store discount ($, optional)</label>
              <input className="form-input" type="number" min="0" step="0.01" value={minSubtotal} onChange={(e) => setMinSubtotal(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Applies to</label>
              <select className="form-select" value={channels} onChange={(e) => setChannels(e.target.value as PromotionChannels)}>
                <option value="app">App orders</option>
                <option value="all">App and phone (phone needs the SMS payment link, not built yet)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Start / end date (optional)</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="form-input" type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} />
                <input className="form-input" type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Uses per customer (optional)</label>
              <input className="form-input" type="number" min="1" step="1" value={perUser} onChange={(e) => setPerUser(e.target.value)} placeholder="No limit" />
            </div>
            <div className="form-group">
              <label className="form-label">Monthly budget ($, optional)</label>
              <input className="form-input" type="number" min="0.01" step="0.01" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="No limit" />
            </div>
          </div>
          <label className="form-check" style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '4px 0 12px' }}>
            <input type="checkbox" checked={firstOrderOnly} onChange={(e) => setFirstOrderOnly(e.target.checked)} />
            New customers only (first order)
          </label>
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
            Create promotion
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Platform promotions</h2>
        </div>
        <div className="card-body">
          {promos.map((p) => (
            <div
              key={p.id}
              style={{
                display: 'flex',
                gap: 12,
                alignItems: 'flex-start',
                padding: '10px 0',
                borderBottom: '1px solid var(--color-border, #f0f0f0)',
                opacity: p.is_active ? 1 : 0.55,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700 }}>{p.name}</div>
                <div>{terms(p)}</div>
                <div style={subStyle}>
                  {p.channels === 'app' ? 'App' : 'App and phone'} · {p.starts_on ?? '…'} → {p.ends_on ?? '…'} · {limits(p)} · used on{' '}
                  {p.orders_count} order(s)
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => handleBudget(p)}>
                Budget
              </button>
              <button
                className={`btn btn-sm ${p.is_active ? 'btn-secondary' : 'btn-primary'}`}
                disabled={busy}
                onClick={() => void run(() => updatePromotion(p.id, { is_active: !p.is_active }))}
              >
                {p.is_active ? 'Turn off' : 'Turn on'}
              </button>
              {p.orders_count === 0 && (
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={busy}
                  onClick={() => window.confirm(`Delete “${p.name}”?`) && void run(() => deletePromotion(p.id))}
                >
                  Delete
                </button>
              )}
            </div>
          ))}
          {!promos.length && <div style={subStyle}>No platform promotions yet.</div>}
        </div>
      </div>
    </div>
  )
}
