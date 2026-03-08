import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  type OrderItemOut,
  type OrderOut,
  listOrderItems,
  listOrders,
  updateOrderStatus,
} from '../api/orderApi'

const COMMON_STATUSES = ['draft', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']

export function OrdersRoute(): React.JSX.Element {
  const { t } = useTranslation()
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
        setError(t('orders.failedLoadOrders'))
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
        setError(t('orders.failedLoadItems'))
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

      <div className="panel-layout">
        {/* Left: Orders list */}
        <div className="card">
          <div className="card-header">
            <h2>{t('orders.orders')}</h2>
            <button className="btn btn-secondary btn-sm" onClick={() => void reloadOrders()}>
              {t('common.refresh')}
            </button>
          </div>
          <div>
            {orders.map((o) => (
              <div
                key={o.id}
                className={`list-item ${o.id === selectedOrderId ? 'selected' : ''}`}
                onClick={() => setSelectedOrderId(o.id)}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span className={`badge badge-${o.status}`}>{o.status}</span>
                    <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>${String(o.total)}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                    {new Date(o.created_at).toLocaleString()} · {o.channel}
                  </div>
                </div>
              </div>
            ))}
            {!orders.length && !loading && <div className="empty-state">{t('orders.noOrders')}</div>}
          </div>
        </div>

        {/* Right: Order details */}
        <div className="card">
          <div className="card-header">
            <h2>{t('orders.orderDetails')}</h2>
          </div>
          {selectedOrder ? (
            <div className="card-body">
              <div className="grid-2">
                <div className="form-group">
                  <span className="meta-label">{t('orders.orderId')}</span>
                  <span className="mono">{selectedOrder.id}</span>
                </div>
                <div className="form-group">
                  <span className="meta-label">{t('orders.userId')}</span>
                  <span className="mono">{selectedOrder.user_id ?? '—'}</span>
                </div>
                <div className="form-group">
                  <span className="meta-label">{t('orders.created')}</span>
                  <span>{new Date(selectedOrder.created_at).toLocaleString()}</span>
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
                {items.map((it) => (
                  <div key={it.id} className="list-item" style={{ cursor: 'default' }}>
                    <div>
                      <span style={{ fontWeight: 600 }}>x{it.quantity}</span>
                      <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                        {it.menu_item_id}
                      </div>
                    </div>
                    <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>${String(it.price_snapshot)}</span>
                  </div>
                ))}
                {!items.length && <div className="empty-state" style={{ padding: '16px 0' }}>{t('orders.noItems')}</div>}
              </div>
            </div>
          ) : (
            <div className="card-body">
              <div className="empty-state" style={{ padding: '16px 0' }}>{t('orders.selectOrder')}</div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
