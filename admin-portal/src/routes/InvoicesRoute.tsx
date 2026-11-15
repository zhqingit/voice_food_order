import React, { useEffect, useState } from 'react'
import {
  addAdjustment,
  deleteDraft,
  generateInvoices,
  getInvoice,
  invoiceAction,
  listInvoices,
  removeAdjustment,
  type Invoice,
  type InvoiceDetail,
} from '../api/invoicesApi'

const thStyle: React.CSSProperties = { padding: '8px 10px', fontWeight: 600, whiteSpace: 'nowrap', textAlign: 'left' }
const tdStyle: React.CSSProperties = { padding: '8px 10px', whiteSpace: 'nowrap' }
const right: React.CSSProperties = { textAlign: 'right' }
const subStyle: React.CSSProperties = { fontSize: 11, color: 'var(--color-text-secondary)' }

// Invoices are made for the month that just ended.
function lastMonth(): string {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function usd(v: string | number): string {
  const n = Number(v)
  const s = Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return n < 0 ? `-$${s}` : `$${s}`
}

function errorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { detail?: string; code?: string } } }).response?.data
  return data?.detail ?? data?.code ?? fallback
}

function statusPill(inv: Invoice): React.JSX.Element {
  const [label, bg, fg] = inv.overdue
    ? ['Overdue', '#fef2f2', '#dc2626']
    : {
        draft: ['Draft', '#f3f4f6', '#6b7280'],
        open: ['Sent', '#eff6ff', '#2563eb'],
        paid: [inv.paid_out_of_band ? 'Paid (outside Stripe)' : 'Paid', '#dcfce7', '#16a34a'],
        void: ['Void', '#f3f4f6', '#6b7280'],
        uncollectible: ['Uncollectible', '#fffbeb', '#92400e'],
      }[inv.status]
  return (
    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: bg, color: fg }}>
      {label}
    </span>
  )
}

export function InvoicesRoute(): React.JSX.Element {
  const [period, setPeriod] = useState(lastMonth())
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [selected, setSelected] = useState<InvoiceDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [adjText, setAdjText] = useState('')
  const [adjAmount, setAdjAmount] = useState('')

  async function reload(p: string = period): Promise<void> {
    try {
      setInvoices(await listInvoices(p))
    } catch {
      setError('Failed to load invoices.')
    }
  }

  useEffect(() => {
    setSelected(null)
    void reload(period)
  }, [period])

  // Runs an action, shows its error, refreshes the list.
  async function run(fn: () => Promise<void>, done?: string): Promise<void> {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await fn()
      if (done) setMessage(done)
      await reload()
    } catch (err) {
      setError(errorMessage(err, 'Something went wrong.'))
    } finally {
      setBusy(false)
    }
  }

  function handleGenerate(): void {
    void run(async () => {
      const created = await generateInvoices(period)
      setMessage(created.length ? `${created.length} draft(s) created.` : 'Nothing new to invoice.')
    })
  }

  async function open(id: string): Promise<void> {
    setError(null)
    try {
      setSelected(await getInvoice(id))
    } catch {
      setError('Failed to load the invoice.')
    }
  }

  function act(action: 'send' | 'void' | 'mark-paid', confirmText: string, done: string): void {
    if (!selected || !window.confirm(confirmText)) return
    void run(async () => setSelected(await invoiceAction(selected.id, action)), done)
  }

  function handleDelete(): void {
    if (!selected || !window.confirm('Delete this draft? Its orders will be billed by the next draft generated.')) return
    void run(async () => {
      await deleteDraft(selected.id)
      setSelected(null)
    }, 'Draft deleted.')
  }

  function handleAddAdjustment(e: React.FormEvent): void {
    e.preventDefault()
    const amount = Number(adjAmount)
    if (!selected || !adjText.trim() || !amount) {
      setError('Enter a description and a non-zero amount (negative = credit).')
      return
    }
    void run(async () => {
      setSelected(await addAdjustment(selected.id, adjText.trim(), amount.toFixed(2)))
      setAdjText('')
      setAdjAmount('')
    })
  }

  const isDraft = selected?.status === 'draft'

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          className="form-input"
          type="month"
          value={period}
          onChange={(e) => e.target.value && setPeriod(e.target.value)}
          style={{ width: 170 }}
        />
        <button className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={busy}>
          Generate drafts
        </button>
        <span style={subStyle}>
          Bills commission on completed orders paid at the store (not taken online), plus monthly fees. Under $1 rolls
          over. Net 15.
        </span>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}

      <div className="card">
        <div className="card-header">
          <h2>Invoices for {period}</h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                <th style={thStyle}>Store</th>
                <th style={thStyle}>Status</th>
                <th style={{ ...thStyle, ...right }}>Orders</th>
                <th style={{ ...thStyle, ...right }}>Total</th>
                <th style={thStyle}>Due</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr
                  key={inv.id}
                  onClick={() => void open(inv.id)}
                  style={{
                    borderBottom: '1px solid var(--color-border, #f0f0f0)',
                    cursor: 'pointer',
                    background: inv.id === selected?.id ? 'var(--color-bg-selected, #f0f7ff)' : undefined,
                  }}
                >
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{inv.store_name}</td>
                  <td style={tdStyle}>{statusPill(inv)}</td>
                  <td style={{ ...tdStyle, ...right }}>{inv.order_count}</td>
                  <td style={{ ...tdStyle, ...right, fontWeight: 600 }}>{usd(inv.total)}</td>
                  <td style={tdStyle}>{inv.due_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!invoices.length && (
            <div className="empty-state" style={{ padding: 24 }}>
              No invoices for this month. Click “Generate drafts”.
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header">
            <h2>
              {selected.store_name} · {selected.period} {statusPill(selected)}
            </h2>
            <span style={{ fontSize: 18, fontWeight: 800 }}>{usd(selected.total)}</span>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              {isDraft && (
                <>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={busy}
                    onClick={() => act('send', `Send ${usd(selected.total)} to ${selected.store_name} through Stripe?`, 'Invoice sent.')}
                  >
                    Send via Stripe
                  </button>
                  <button className="btn btn-secondary btn-sm" disabled={busy} onClick={handleDelete}>
                    Delete draft
                  </button>
                </>
              )}
              {(selected.status === 'open' || selected.status === 'uncollectible') && (
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={busy}
                  onClick={() => act('mark-paid', 'Mark as paid outside Stripe (check, cash, bank transfer)?', 'Marked paid.')}
                >
                  Mark paid (outside Stripe)
                </button>
              )}
              {['draft', 'open', 'uncollectible'].includes(selected.status) && (
                <button
                  className="btn btn-danger btn-sm"
                  disabled={busy}
                  onClick={() => act('void', 'Void this invoice? Its orders will NOT be billed again.', 'Invoice voided.')}
                >
                  Void (write off)
                </button>
              )}
              {selected.hosted_url && (
                <a className="btn btn-ghost btn-sm" href={selected.hosted_url} target="_blank" rel="noreferrer">
                  Stripe invoice page
                </a>
              )}
              {selected.pdf_url && (
                <a className="btn btn-ghost btn-sm" href={selected.pdf_url} target="_blank" rel="noreferrer">
                  PDF
                </a>
              )}
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                    <th style={thStyle}>Item</th>
                    <th style={{ ...thStyle, ...right }}>Subtotal</th>
                    <th style={{ ...thStyle, ...right }}>Rate</th>
                    <th style={{ ...thStyle, ...right }}>Commission</th>
                    <th style={{ ...thStyle, ...right }}>Paid online</th>
                    <th style={{ ...thStyle, ...right }}>Billed</th>
                    <th style={thStyle} />
                  </tr>
                </thead>
                <tbody>
                  {selected.lines.map((line) => (
                    <tr key={line.id} style={{ borderBottom: '1px solid var(--color-border, #f0f0f0)' }}>
                      <td style={tdStyle}>{line.description}</td>
                      <td style={{ ...tdStyle, ...right }}>{line.subtotal != null ? usd(line.subtotal) : ''}</td>
                      <td style={{ ...tdStyle, ...right }}>{line.commission_bps != null ? `${line.commission_bps / 100}%` : ''}</td>
                      <td style={{ ...tdStyle, ...right }}>{line.commission != null ? usd(line.commission) : ''}</td>
                      <td style={{ ...tdStyle, ...right }}>
                        {line.collected_online != null && Number(line.collected_online) > 0 ? usd(line.collected_online) : ''}
                      </td>
                      <td style={{ ...tdStyle, ...right, fontWeight: 600 }}>{usd(line.amount)}</td>
                      <td style={tdStyle}>
                        {isDraft && line.kind === 'adjustment' && (
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={busy}
                            onClick={() => void run(async () => setSelected(await removeAdjustment(selected.id, line.id)))}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {isDraft && (
              <form
                onSubmit={handleAddAdjustment}
                style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 12 }}
              >
                <input
                  className="form-input"
                  placeholder="Adjustment (e.g. Promo credit)"
                  maxLength={255}
                  value={adjText}
                  onChange={(e) => setAdjText(e.target.value)}
                  style={{ flex: 1, minWidth: 200 }}
                />
                <input
                  className="form-input"
                  type="number"
                  step="0.01"
                  placeholder="Amount (− = credit)"
                  value={adjAmount}
                  onChange={(e) => setAdjAmount(e.target.value)}
                  style={{ width: 160 }}
                />
                <button type="submit" className="btn btn-secondary btn-sm" disabled={busy}>
                  Add adjustment
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
