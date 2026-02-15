import React, { useEffect, useMemo, useState } from 'react'
import { GlassButton, GlassCard, GlassSurface } from '@zhqingit/liquid-glass-react'
import {
  type OrderItemOut,
  type OrderOut,
  listOrderItems,
  listOrders,
  updateOrderStatus,
} from '../api/orderApi'

const COMMON_STATUSES = ['draft', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']

export function OrdersRoute(): React.JSX.Element {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [orders, setOrders] = useState<OrderOut[]>([])
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const selectedOrder = useMemo(
    () => orders.find((o) => o.id === selectedOrderId) ?? null,
    [orders, selectedOrderId],
  )

  const [items, setItems] = useState<OrderItemOut[]>([])

  async function reloadOrders(selectId?: string): Promise<void> {
    const data = await listOrders()
    setOrders(data)
    const nextSel = selectId ?? selectedOrderId ?? (data[0]?.id ?? null)
    setSelectedOrderId(nextSel)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await reloadOrders()
      } catch {
        setError('Failed to load orders')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedOrderId) {
      setItems([])
      return
    }
    void (async () => {
      setError(null)
      try {
        const data = await listOrderItems(selectedOrderId)
        setItems(data)
      } catch {
        setError('Failed to load order items')
      }
    })()
  }, [selectedOrderId])

  async function handleUpdateStatus(next: string): Promise<void> {
    if (!selectedOrder) return
    setError(null)
    try {
      const updated = await updateOrderStatus(selectedOrder.id, next)
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
    } catch {
      setError('Failed to update order')
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 16 }}>
      <GlassCard preset="frosted" style={{ padding: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h2 style={{ marginTop: 0 }}>Orders</h2>
          <GlassButton preset="subtle" style={{ padding: '6px 10px' }} onClick={() => void reloadOrders()}>
            Refresh
          </GlassButton>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {orders.map((o) => {
            const active = o.id === selectedOrderId
            return (
              <GlassSurface
                key={o.id}
                preset={active ? 'vibrant' : 'subtle'}
                interactive
                onClick={() => setSelectedOrderId(o.id)}
                style={{ padding: 12, cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 800 }}>{o.status}</div>
                    <div style={{ opacity: 0.75, fontSize: 12 }}>
                      {new Date(o.created_at).toLocaleString()} · {o.channel}
                    </div>
                  </div>
                  <div style={{ fontWeight: 800 }}>${String(o.total)}</div>
                </div>
              </GlassSurface>
            )
          })}
          {!orders.length && !loading ? <div style={{ opacity: 0.7 }}>No orders yet.</div> : null}
        </div>
      </GlassCard>

      <GlassCard preset="frosted" style={{ padding: 14 }}>
        <h2 style={{ marginTop: 0 }}>Order details</h2>
        {selectedOrder ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <div style={metaLabel}>Order ID</div>
                <div style={mono}>{selectedOrder.id}</div>
              </div>
              <div>
                <div style={metaLabel}>User ID</div>
                <div style={mono}>{selectedOrder.user_id ?? '—'}</div>
              </div>
              <div>
                <div style={metaLabel}>Created</div>
                <div>{new Date(selectedOrder.created_at).toLocaleString()}</div>
              </div>
              <div>
                <div style={metaLabel}>Totals</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <span>Subtotal: ${String(selectedOrder.subtotal)}</span>
                  <span>Tax: ${String(selectedOrder.tax)}</span>
                  <span style={{ fontWeight: 800 }}>Total: ${String(selectedOrder.total)}</span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ opacity: 0.8, fontSize: 12 }}>Status</div>
              <select
                value={selectedOrder.status}
                onChange={(e) => void handleUpdateStatus(e.target.value)}
                style={selectStyle}
              >
                {Array.from(new Set([selectedOrder.status, ...COMMON_STATUSES])).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginTop: 14 }}>
              <h3 style={{ marginTop: 0 }}>Items</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {items.map((it) => (
                  <GlassSurface key={it.id} preset="subtle" style={{ padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <div>
                        <div style={{ fontWeight: 800 }}>x{it.quantity}</div>
                        <div style={{ opacity: 0.75, fontSize: 12 }}>menu_item_id: {it.menu_item_id}</div>
                      </div>
                      <div style={{ fontWeight: 800 }}>${String(it.price_snapshot)}</div>
                    </div>
                  </GlassSurface>
                ))}
                {!items.length ? <div style={{ opacity: 0.7 }}>No items.</div> : null}
              </div>
            </div>
          </>
        ) : (
          <div style={{ opacity: 0.75 }}>Select an order.</div>
        )}

        {error ? <div style={{ marginTop: 12, color: 'crimson' }}>{error}</div> : null}
      </GlassCard>
    </div>
  )
}

const metaLabel: React.CSSProperties = { opacity: 0.7, fontSize: 12 }
const mono: React.CSSProperties = { fontFamily: 'ui-monospace, SFMono-Regular', fontSize: 12, opacity: 0.9 }

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.22)',
  background: 'rgba(255,255,255,0.10)',
  color: 'inherit',
}
