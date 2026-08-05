import React, { useEffect, useMemo, useState } from 'react'
import {
  getStore,
  listStores,
  updateStore,
  type AdminStore,
  type AdminStoreDetail,
} from '../api/storesApi'

const thStyle: React.CSSProperties = { padding: '8px 12px', fontWeight: 600, whiteSpace: 'nowrap', textAlign: 'left' }
const tdStyle: React.CSSProperties = { padding: '8px 12px', whiteSpace: 'nowrap' }

function pill(label: string, color: 'green' | 'gray' | 'amber' | 'red'): React.JSX.Element {
  const palette = {
    green: { bg: '#dcfce7', fg: '#16a34a' },
    gray: { bg: '#f3f4f6', fg: '#6b7280' },
    amber: { bg: '#fffbeb', fg: '#92400e' },
    red: { bg: '#fef2f2', fg: '#dc2626' },
  }[color]
  return (
    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: palette.bg, color: palette.fg }}>
      {label}
    </span>
  )
}

function localTime(iso: string): string {
  const s = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  return new Date(s).toLocaleString()
}

export function StoresRoute(): React.JSX.Element {
  const [stores, setStores] = useState<AdminStore[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AdminStoreDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [feeInput, setFeeInput] = useState('')
  const [saving, setSaving] = useState(false)

  const selected = useMemo(() => stores.find((s) => s.id === selectedId) ?? null, [stores, selectedId])

  async function reload(): Promise<void> {
    setError(null)
    try {
      setStores(await listStores())
    } catch {
      setError('Failed to load stores.')
    }
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      await reload()
      setLoading(false)
    })()
  }, [])

  // Load live detail (incl. live Stripe status) when a store is selected.
  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    void (async () => {
      setDetailLoading(true)
      setError(null)
      try {
        const d = await getStore(selectedId)
        setDetail(d)
        setFeeInput(d.platform_fee_bps != null ? String(d.platform_fee_bps / 100) : '')
      } catch {
        setError('Failed to load store detail.')
      } finally {
        setDetailLoading(false)
      }
    })()
  }, [selectedId])

  function applyUpdated(d: AdminStoreDetail): void {
    setDetail(d)
    setStores((prev) => prev.map((s) => (s.id === d.id ? { ...s, ...d } : s)))
  }

  async function patch(id: string, body: Parameters<typeof updateStore>[1], okMsg: string): Promise<void> {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      applyUpdated(await updateStore(id, body))
      setMessage(okMsg)
    } catch {
      setError('Update failed.')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveFee(id: string): Promise<void> {
    const raw = feeInput.trim()
    let bps: number | null
    if (!raw) {
      bps = null // clear override → platform default
    } else {
      const pct = Number(raw)
      if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
        setError('Fee must be between 0 and 100%.')
        return
      }
      bps = Math.round(pct * 100)
    }
    await patch(id, { platform_fee_bps: bps }, 'Commission updated.')
  }

  return (
    <>
      <div className="page-header">
        <h1>Stores</h1>
        <p>Review stores, approve them for go-live, suspend, and set commission.</p>
      </div>

      {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}
      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card">
        <div className="card-header">
          <h2>All Stores</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => void reload()}>Refresh</button>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                <th style={thStyle}>Name</th>
                <th style={thStyle}>Email</th>
                <th style={thStyle}>Approved</th>
                <th style={thStyle}>Active</th>
                <th style={thStyle}>Published</th>
                <th style={thStyle}>Payments</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Fee</th>
                <th style={thStyle}>Created</th>
              </tr>
            </thead>
            <tbody>
              {stores.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  style={{
                    borderBottom: '1px solid var(--color-border, #f0f0f0)',
                    cursor: 'pointer',
                    background: s.id === selectedId ? 'var(--color-bg-selected, #f0f7ff)' : undefined,
                  }}
                >
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{s.name}</td>
                  <td style={{ ...tdStyle, color: 'var(--color-text-secondary)' }}>{s.email}</td>
                  <td style={tdStyle}>{s.is_approved ? pill('Approved', 'green') : pill('Pending', 'amber')}</td>
                  <td style={tdStyle}>{s.is_active ? pill('Active', 'green') : pill('Suspended', 'red')}</td>
                  <td style={tdStyle}>{s.is_published ? pill('Published', 'green') : pill('Hidden', 'gray')}</td>
                  <td style={tdStyle}>
                    {!s.stripe_account_id
                      ? pill('Not connected', 'gray')
                      : s.stripe_charges_enabled
                        ? pill('Ready', 'green')
                        : pill('Incomplete', 'amber')}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    {s.effective_fee_bps / 100}%
                    {s.platform_fee_bps == null && (
                      <span style={{ marginLeft: 4, fontSize: 10, color: 'var(--color-text-secondary)' }}>(default)</span>
                    )}
                  </td>
                  <td style={{ ...tdStyle, color: 'var(--color-text-secondary)' }}>{localTime(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!stores.length && !loading && <div className="empty-state" style={{ padding: 24 }}>No stores yet.</div>}
          {loading && <div className="empty-state" style={{ padding: 24 }}>Loading…</div>}
        </div>
      </div>

      {selected && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header">
            <h2>{selected.name}</h2>
          </div>
          <div className="card-body">
            <div className="grid-2">
              <div className="form-group">
                <span className="meta-label">Email</span>
                <span>{selected.email}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">Phone</span>
                <span>{selected.phone ?? '—'}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">Store ID</span>
                <span className="mono" style={{ fontSize: 12 }}>{selected.id}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">Stripe account</span>
                <span className="mono" style={{ fontSize: 12 }}>{selected.stripe_account_id ?? '— not connected'}</span>
              </div>
            </div>

            {/* Live Stripe status */}
            <div className="form-group" style={{ marginTop: 12 }}>
              <span className="meta-label">Stripe status {detailLoading && '(loading…)'}</span>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {detail?.stripe_charges_enabled ? pill('Charges enabled', 'green') : pill('Charges disabled', 'gray')}
                {detail?.stripe_details_submitted != null &&
                  (detail.stripe_details_submitted ? pill('Details submitted', 'green') : pill('Details pending', 'amber'))}
                {detail?.stripe_payouts_enabled != null &&
                  (detail.stripe_payouts_enabled ? pill('Payouts enabled', 'green') : pill('Payouts disabled', 'gray'))}
              </div>
            </div>

            {/* Controls */}
            <div style={{ marginTop: 20, display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <div>
                <span className="meta-label">Approval (go-live)</span>
                <div>
                  <button
                    className={`btn btn-sm ${selected.is_approved ? 'btn-secondary' : 'btn-primary'}`}
                    disabled={saving}
                    onClick={() => void patch(selected.id, { is_approved: !selected.is_approved }, selected.is_approved ? 'Approval revoked.' : 'Store approved.')}
                  >
                    {selected.is_approved ? 'Revoke approval' : 'Approve'}
                  </button>
                </div>
              </div>

              <div>
                <span className="meta-label">Account</span>
                <div>
                  <button
                    className="btn btn-sm"
                    style={selected.is_active ? { background: '#dc2626', borderColor: '#dc2626', color: '#fff' } : { background: '#16a34a', borderColor: '#16a34a', color: '#fff' }}
                    disabled={saving}
                    onClick={() => void patch(selected.id, { is_active: !selected.is_active }, selected.is_active ? 'Store suspended.' : 'Store reactivated.')}
                  >
                    {selected.is_active ? 'Suspend' : 'Reactivate'}
                  </button>
                </div>
              </div>

              <div>
                <span className="meta-label">Commission (%)</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    className="form-input"
                    value={feeInput}
                    onChange={(e) => setFeeInput(e.target.value)}
                    inputMode="decimal"
                    placeholder="default"
                    style={{ width: 100 }}
                  />
                  <button className="btn btn-primary btn-sm" disabled={saving} onClick={() => void handleSaveFee(selected.id)}>
                    Save
                  </button>
                </div>
                <p style={{ fontSize: 11, color: 'var(--color-text-secondary)', margin: '4px 0 0' }}>
                  Leave blank to use the platform default. Effective: {selected.effective_fee_bps / 100}%
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
