import React, { useEffect, useState } from 'react'
import {
  addPlatformCost,
  deletePlatformCost,
  downloadMonthlyCsv,
  getMonthlyStats,
  type CostCategory,
  type MonthlyStats,
} from '../api/statsApi'

const thStyle: React.CSSProperties = { padding: '8px 10px', fontWeight: 600, whiteSpace: 'nowrap', textAlign: 'right' }
const tdStyle: React.CSSProperties = { padding: '8px 10px', whiteSpace: 'nowrap', textAlign: 'right' }
const subStyle: React.CSSProperties = { fontSize: 11, color: 'var(--color-text-secondary)' }

const CATEGORIES: { value: CostCategory; label: string }[] = [
  { value: 'server', label: 'Server' },
  { value: 'phone_numbers', label: 'Phone numbers' },
  { value: 'domain', label: 'Domain' },
  { value: 'other', label: 'Other' },
]

function currentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function usd(v: string | number): string {
  const n = Number(v)
  const s = Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return n < 0 ? `-$${s}` : `$${s}`
}

function netColor(v: string): string {
  return Number(v) < 0 ? '#dc2626' : '#16a34a'
}

function Tile({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }): React.JSX.Element {
  return (
    <div className="card" style={{ padding: '14px 16px', flex: '1 1 180px' }}>
      <div className="meta-label">{label}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={subStyle}>{sub}</div>}
    </div>
  )
}

export function StatsRoute(): React.JSX.Element {
  const [month, setMonth] = useState(currentMonth())
  const [stats, setStats] = useState<MonthlyStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [category, setCategory] = useState<CostCategory>('server')
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)

  async function reload(m: string = month): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      setStats(await getMonthlyStats(m))
    } catch {
      setError('Failed to load stats.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload(month)
  }, [month])

  async function handleAddCost(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    const value = Number(amount)
    if (!(value > 0)) {
      setError('Enter an amount above 0.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await addPlatformCost({ month, category, amount: value.toFixed(2), note: note.trim() || undefined })
      setAmount('')
      setNote('')
      await reload()
    } catch {
      setError('Failed to add the cost.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteCost(id: string): Promise<void> {
    if (!window.confirm('Delete this cost?')) return
    try {
      await deletePlatformCost(id)
      await reload()
    } catch {
      setError('Failed to delete the cost.')
    }
  }

  async function handleExport(): Promise<void> {
    try {
      await downloadMonthlyCsv(month)
    } catch {
      setError('Failed to export CSV.')
    }
  }

  const t = stats?.totals

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          className="form-input"
          type="month"
          value={month}
          onChange={(e) => e.target.value && setMonth(e.target.value)}
          style={{ width: 170 }}
        />
        <button className="btn btn-secondary btn-sm" onClick={() => void reload()} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={() => void handleExport()} disabled={!stats}>
          Export CSV
        </button>
        <span style={subStyle}>Revenue counts completed orders only. Twilio cost is estimated.</span>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      {t && (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
          <Tile label="Completed orders" value={String(t.orders)} sub={`GMV ${usd(t.gmv)} (pre-tax, after ${usd(t.discounts)} store discounts)`} />
          <Tile
            label="Revenue"
            value={usd(t.revenue)}
            sub={`Commission ${usd(t.commission)} + monthly fees ${usd(t.monthly_fees)}`}
          />
          <Tile
            label="Commission"
            value={usd(t.commission)}
            sub={`${usd(t.commission_online)} collected online · ${usd(t.commission_to_invoice)} to invoice`}
          />
          <Tile
            label="Costs"
            value={usd(t.costs)}
            sub={`AI ${usd(t.ai_cost)} · Twilio ${usd(t.telephony_cost)} · Stripe ${usd(Number(t.stripe_fees) + Number(t.invoice_fees))} · Promotions ${usd(t.platform_discounts)} · Fixed ${usd(t.fixed_costs)}`}
          />
          <Tile
            label="Invoiced to stores"
            value={usd(t.invoiced)}
            sub={`${usd(t.invoice_paid)} paid · ${usd(t.invoice_outstanding)} unpaid${Number(t.invoice_overdue) > 0 ? ` · ${usd(t.invoice_overdue)} overdue` : ''}`}
            color={Number(t.invoice_overdue) > 0 ? '#dc2626' : undefined}
          />
          <Tile label="Net profit" value={usd(t.net)} color={netColor(t.net)} />
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>By store</h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                <th style={{ ...thStyle, textAlign: 'left' }}>Store</th>
                <th style={thStyle}>App orders</th>
                <th style={thStyle}>Phone orders</th>
                <th style={thStyle}>Commission</th>
                <th style={thStyle}>Monthly fee</th>
                <th style={thStyle}>AI</th>
                <th style={thStyle}>Twilio</th>
                <th style={thStyle}>Stripe</th>
                <th style={thStyle}>Net</th>
              </tr>
            </thead>
            <tbody>
              {stats?.stores.map((s) => (
                <tr key={s.store_id} style={{ borderBottom: '1px solid var(--color-border, #f0f0f0)' }}>
                  <td style={{ ...tdStyle, textAlign: 'left', fontWeight: 600 }}>{s.store_name}</td>
                  <td style={tdStyle}>
                    {s.app.orders} · {usd(s.app.gmv)}
                    <div style={subStyle}>commission {usd(s.app.commission)}</div>
                  </td>
                  <td style={tdStyle}>
                    {s.phone.orders} · {usd(s.phone.gmv)}
                    <div style={subStyle}>commission {usd(s.phone.commission)}</div>
                  </td>
                  <td style={tdStyle}>
                    {usd(Number(s.app.commission) + Number(s.phone.commission))}
                    <div style={subStyle}>
                      online {usd(s.commission_online)} · invoice {usd(s.commission_to_invoice)}
                    </div>
                  </td>
                  <td style={tdStyle}>{usd(s.monthly_fee)}</td>
                  <td style={tdStyle}>{usd(s.ai_cost)}</td>
                  <td style={tdStyle}>
                    {usd(s.telephony_cost)}
                    <div style={subStyle}>
                      {s.phone_calls} calls · {s.phone_minutes} min
                    </div>
                  </td>
                  <td style={tdStyle}>{usd(Number(s.stripe_fees) + Number(s.invoice_fees))}</td>
                  <td style={{ ...tdStyle, fontWeight: 700, color: netColor(s.net) }}>{usd(s.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {stats && !stats.stores.length && (
            <div className="empty-state" style={{ padding: 24 }}>No activity this month.</div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <h2>Fixed costs ({month})</h2>
        </div>
        <div className="card-body">
          {stats?.fixed_costs.map((c) => (
            <div key={c.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '6px 0' }}>
              <span style={{ width: 130 }}>{CATEGORIES.find((x) => x.value === c.category)?.label ?? c.category}</span>
              <span style={{ width: 90, fontWeight: 600 }}>{usd(c.amount)}</span>
              <span style={{ flex: 1, color: 'var(--color-text-secondary)' }}>{c.note}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => void handleDeleteCost(c.id)}>
                Delete
              </button>
            </div>
          ))}
          {stats && !stats.fixed_costs.length && <div style={subStyle}>None entered for this month.</div>}

          <form
            onSubmit={(e) => void handleAddCost(e)}
            style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 12 }}
          >
            <select
              className="form-select"
              value={category}
              onChange={(e) => setCategory(e.target.value as CostCategory)}
              style={{ width: 150 }}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <input
              className="form-input"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Amount $"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              style={{ width: 120 }}
            />
            <input
              className="form-input"
              placeholder="Note (optional)"
              maxLength={255}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={{ flex: 1, minWidth: 160 }}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
              Add cost
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
