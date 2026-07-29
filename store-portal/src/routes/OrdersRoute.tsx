import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  type OrderItemOut,
  type OrderOut,
  type OrderUsage,
  getOrderUsage,
  listOrderItems,
  listOrders,
  updateOrderStatus,
} from '../api/orderApi'

const COMMON_STATUSES = ['draft', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']
const POLL_INTERVAL_MS = 10_000

let _audioCtx: AudioContext | null = null
function getAudioCtx(): AudioContext {
  if (!_audioCtx || _audioCtx.state === 'closed') _audioCtx = new AudioContext()
  if (_audioCtx.state === 'suspended') void _audioCtx.resume()
  return _audioCtx
}

function playBeep() {
  try {
    const ctx = getAudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.frequency.value = 880
    osc.type = 'sine'
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4)
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.4)
  } catch { /* audio not available */ }
}

// Warm up AudioContext on first user interaction (browser autoplay policy)
if (typeof document !== 'undefined') {
  const warmUp = () => {
    getAudioCtx()
    document.removeEventListener('click', warmUp)
    document.removeEventListener('keydown', warmUp)
  }
  document.addEventListener('click', warmUp, { once: true })
  document.addEventListener('keydown', warmUp, { once: true })
}

function localTime(iso: string): string {
  const s = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  return new Date(s).toLocaleString()
}

const thStyle: React.CSSProperties = { padding: '8px 12px', fontWeight: 600, whiteSpace: 'nowrap' }
const thSortStyle: React.CSSProperties = { ...thStyle, cursor: 'pointer', userSelect: 'none' }
const tdStyle: React.CSSProperties = { padding: '8px 12px', whiteSpace: 'nowrap' }

type SortKey = 'status' | 'created_at' | 'channel' | 'subtotal' | 'tax' | 'total'
type SortDir = 'asc' | 'desc'

function sortIndicator(col: SortKey, active: SortKey, dir: SortDir): string {
  if (col !== active) return ' ↕'
  return dir === 'asc' ? ' ↑' : ' ↓'
}

export function OrdersRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [orders, setOrders] = useState<OrderOut[]>([])
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'created_at' ? 'desc' : 'asc')
    }
  }

  const sortedOrders = useMemo(() => {
    const sorted = [...orders].sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'status':
        case 'channel':
          cmp = (a[sortKey] ?? '').localeCompare(b[sortKey] ?? '')
          break
        case 'created_at':
          cmp = a.created_at.localeCompare(b.created_at)
          break
        case 'subtotal':
        case 'tax':
        case 'total':
          cmp = Number(a[sortKey]) - Number(b[sortKey])
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [orders, sortKey, sortDir])

  const selectedOrder = useMemo(
    () => orders.find((o) => o.id === selectedOrderId) ?? null,
    [orders, selectedOrderId],
  )

  const [items, setItems] = useState<OrderItemOut[]>([])
  const [usage, setUsage] = useState<OrderUsage | null>(null)
  const knownStatuses = useRef<Map<string, string> | null>(null)

  const reloadOrders = useCallback(async (selectId?: string): Promise<void> => {
    const data = await listOrders()
    if (knownStatuses.current !== null) {
      const shouldBeep = data.some((o) => {
        const prev = knownStatuses.current!.get(o.id)
        // New non-draft order, or status changed from draft to something else
        return o.status !== 'draft' && (prev === undefined || prev === 'draft')
      })
      if (shouldBeep) playBeep()
    }
    knownStatuses.current = new Map(data.map((o) => [o.id, o.status]))
    setOrders(data)
    setSelectedOrderId((prev) => selectId ?? prev ?? (data[0]?.id ?? null))
  }, [])

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await reloadOrders()
      } catch {
        setError(t('orders.failedLoadOrders'))
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const id = setInterval(() => { void reloadOrders().catch(() => {}) }, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [reloadOrders])

  useEffect(() => {
    if (!selectedOrderId) {
      setItems([])
      setUsage(null)
      return
    }
    void (async () => {
      setError(null)
      try {
        const [data, usageData] = await Promise.all([
          listOrderItems(selectedOrderId),
          getOrderUsage(selectedOrderId).catch(() => null),
        ])
        setItems(data)
        setUsage(usageData)
      } catch {
        setError(t('orders.failedLoadItems'))
      }
    })()
  }, [selectedOrderId])

  function handlePrint(): void {
    if (!selectedOrder) return
    const rows = items.map((it) =>
      `<tr>
        <td style="padding:4px 8px">${it.name ?? 'Unknown item'}${it.note ? `<br/><span style="font-size:11px;color:#666;font-style:italic">${it.note}</span>` : ''}</td>
        <td style="padding:4px 8px;text-align:center">${it.quantity}</td>
        <td style="padding:4px 8px;text-align:right">$${String(it.price_snapshot)}</td>
        <td style="padding:4px 8px;text-align:right">$${(Number(it.price_snapshot) * it.quantity).toFixed(2)}</td>
      </tr>`
    ).join('')
    const orderNote = selectedOrder.notes ? `<div style="margin-top:12px;font-style:italic;font-size:12px;color:#666">Note: ${selectedOrder.notes}</div>` : ''

    const html = `<!DOCTYPE html><html><head><title>Order ${selectedOrder.short_code}</title>
      <style>
        body { font-family: sans-serif; padding: 24px; max-width: 400px; margin: 0 auto; }
        h2 { margin: 0 0 4px; font-size: 18px; }
        .meta { font-size: 12px; color: #666; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
        th { text-align: left; padding: 4px 8px; border-bottom: 2px solid #ccc; font-size: 12px; }
        td { border-bottom: 1px solid #eee; }
        .totals { margin-top: 12px; font-size: 13px; }
        .totals .row { display: flex; justify-content: space-between; padding: 2px 0; }
        .totals .total { font-weight: 700; font-size: 15px; border-top: 2px solid #333; margin-top: 4px; padding-top: 4px; }
        @media print { body { padding: 0; } }
      </style></head><body>
      <h2>Order #${selectedOrder.short_code}</h2>
      <div class="meta">
        ${localTime(selectedOrder.created_at)}<br/>
        Status: ${selectedOrder.status} &nbsp; Channel: ${selectedOrder.channel}
        ${selectedOrder.customer_name ? `<br/>Customer: <strong>${selectedOrder.customer_name}</strong>` : ''}
        ${selectedOrder.user_email ? `<br/>Account: ${selectedOrder.user_email}` : ''}
      </div>
      <table>
        <thead><tr>
          <th>Item</th><th style="text-align:center">Qty</th>
          <th style="text-align:right">Price</th><th style="text-align:right">Total</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${orderNote}
      <div class="totals">
        <div class="row"><span>Subtotal</span><span>$${String(selectedOrder.subtotal)}</span></div>
        <div class="row"><span>Tax</span><span>$${String(selectedOrder.tax)}</span></div>
        <div class="row total"><span>Total</span><span>$${String(selectedOrder.total)}</span></div>
      </div>
      <script>window.onload=function(){window.print()}<\/script>
    </body></html>`

    const w = window.open('', '_blank')
    if (w) { w.document.write(html); w.document.close() }
  }

  async function handleUpdateStatus(next: string): Promise<void> {
    if (!selectedOrder) return
    setError(null)
    try {
      const updated = await updateOrderStatus(selectedOrder.id, next)
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
    } catch {
      setError(t('orders.failedUpdateOrder'))
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>{t('orders.title')}</h1>
        <p>{t('orders.subtitle')}</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Orders table */}
      <div className="card">
        <div className="card-header">
          <h2>{t('orders.orders')}</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => void reloadOrders()}>
            {t('common.refresh')}
          </button>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)', textAlign: 'left' }}>
                <th style={thSortStyle} onClick={() => toggleSort('status')}>{t('orders.status')}{sortIndicator('status', sortKey, sortDir)}</th>
                <th style={thSortStyle} onClick={() => toggleSort('created_at')}>{t('orders.created')}{sortIndicator('created_at', sortKey, sortDir)}</th>
                <th style={thSortStyle} onClick={() => toggleSort('channel')}>{t('orders.channel')}{sortIndicator('channel', sortKey, sortDir)}</th>
                <th style={thStyle}>Account</th>
                <th style={{ ...thSortStyle, textAlign: 'right' }} onClick={() => toggleSort('subtotal')}>{t('orders.subtotal')}{sortIndicator('subtotal', sortKey, sortDir)}</th>
                <th style={{ ...thSortStyle, textAlign: 'right' }} onClick={() => toggleSort('tax')}>{t('orders.tax')}{sortIndicator('tax', sortKey, sortDir)}</th>
                <th style={{ ...thSortStyle, textAlign: 'right' }} onClick={() => toggleSort('total')}>{t('orders.total')}{sortIndicator('total', sortKey, sortDir)}</th>
                <th style={thStyle}>{t('orders.orderId')}</th>
              </tr>
            </thead>
            <tbody>
              {sortedOrders.map((o) => (
                <tr
                  key={o.id}
                  onClick={() => setSelectedOrderId(o.id)}
                  style={{
                    borderBottom: '1px solid var(--color-border, #f0f0f0)',
                    cursor: 'pointer',
                    background: o.id === selectedOrderId ? 'var(--color-bg-selected, #f0f7ff)' : undefined,
                  }}
                  onMouseEnter={(e) => { if (o.id !== selectedOrderId) e.currentTarget.style.background = 'var(--color-bg-hover, #fafafa)' }}
                  onMouseLeave={(e) => { if (o.id !== selectedOrderId) e.currentTarget.style.background = '' }}
                >
                  <td style={tdStyle}><span className={`badge badge-${o.status}`}>{o.status}</span></td>
                  <td style={tdStyle}>{localTime(o.created_at)}</td>
                  <td style={tdStyle}>{o.channel}</td>
                  <td style={{ ...tdStyle, fontSize: 12, color: 'var(--color-text-secondary)' }}>{o.user_email ?? '—'}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>${String(o.subtotal)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>${String(o.tax)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>${String(o.total)}</td>
                  <td style={{ ...tdStyle, fontSize: 14, fontWeight: 700, letterSpacing: 1 }} className="mono">{o.short_code}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!orders.length && !loading && <div className="empty-state" style={{ padding: 24 }}>{t('orders.noOrders')}</div>}
        </div>
      </div>

      {/* Order details (shown when an order is selected) */}
      {selectedOrder && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header">
            <h2>{t('orders.orderDetails')}</h2>
            <button className="btn btn-secondary btn-sm" onClick={handlePrint}>
              {t('orders.print')}
            </button>
          </div>
          <div className="card-body">
            <div className="grid-2">
              <div className="form-group">
                <span className="meta-label">{t('orders.orderId')}</span>
                <span className="mono">{selectedOrder.id}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">Account</span>
                <span>{selectedOrder.user_email ?? '—'}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">{t('orders.created')}</span>
                <span>{localTime(selectedOrder.created_at)}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">{t('orders.totals')}</span>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <span>{t('orders.subtotal')}: ${String(selectedOrder.subtotal)}</span>
                  <span>{t('orders.tax')}: ${String(selectedOrder.tax)}</span>
                  <span style={{ fontWeight: 700 }}>{t('orders.total')}: ${String(selectedOrder.total)}</span>
                </div>
              </div>
            </div>

            {selectedOrder.customer_name && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">Customer</span>
                <span style={{ fontWeight: 600 }}>{selectedOrder.customer_name}</span>
              </div>
            )}

            {selectedOrder.fulfillment_type && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">{t('orders.fulfillment')}</span>
                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{selectedOrder.fulfillment_type}</span>
              </div>
            )}

            {selectedOrder.fulfillment_type === 'delivery' && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">{t('orders.deliveryAddress')}</span>
                <span style={{ whiteSpace: 'pre-wrap' }}>
                  {selectedOrder.delivery_address ? selectedOrder.delivery_address : <em style={{ color: 'var(--color-text-secondary)' }}>{t('orders.deliveryAddressMissing')}</em>}
                </span>
              </div>
            )}

            {selectedOrder.notes && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">{t('orders.orderNote')}</span>
                <span style={{ fontStyle: 'italic' }}>{selectedOrder.notes}</span>
              </div>
            )}

            {usage && usage.total_tokens > 0 && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">{t('orders.aiUsage')}</span>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
                  <span>{t('orders.promptTokens')}: {usage.prompt_tokens.toLocaleString()}</span>
                  <span>{t('orders.completionTokens')}: {usage.completion_tokens.toLocaleString()}</span>
                  <span>{t('orders.totalTokens')}: {usage.total_tokens.toLocaleString()}</span>
                  <span style={{ fontWeight: 600 }}>{t('orders.llmCost')}: ${usage.llm_cost}</span>
                </div>
              </div>
            )}

            <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className="meta-label" style={{ marginBottom: 0 }}>{t('orders.status')}</span>
              <select
                className="form-select"
                value={selectedOrder.status}
                onChange={(e) => void handleUpdateStatus(e.target.value)}
              >
                {Array.from(new Set([selectedOrder.status, ...COMMON_STATUSES])).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div style={{ marginTop: 20 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>{t('orders.items')}</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)', textAlign: 'left' }}>
                    <th style={thStyle}>{t('orders.itemName')}</th>
                    <th style={thStyle}>{t('orders.note')}</th>
                    <th style={{ ...thStyle, textAlign: 'center' }}>{t('orders.qty')}</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>{t('orders.unitPrice')}</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>{t('orders.lineTotal')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id} style={{ borderBottom: '1px solid var(--color-border, #f0f0f0)' }}>
                      <td style={tdStyle}>
                        {it.name ?? 'Unknown item'}
                        {it.variant_name && (
                          <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--color-text-secondary)' }}>
                            ({it.variant_name})
                          </span>
                        )}
                      </td>
                      <td style={{ ...tdStyle, fontSize: 12, color: 'var(--color-text-secondary)', fontStyle: it.note ? 'italic' : undefined }}>{it.note ?? '—'}</td>
                      <td style={{ ...tdStyle, textAlign: 'center' }}>{it.quantity}</td>
                      <td style={{ ...tdStyle, textAlign: 'right' }}>${String(it.price_snapshot)}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>${(Number(it.price_snapshot) * it.quantity).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!items.length && <div className="empty-state" style={{ padding: '16px 0' }}>{t('orders.noItems')}</div>}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
