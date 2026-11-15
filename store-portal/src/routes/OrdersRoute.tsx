import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { formatPhone } from '../phone'
import {
  type OrderEventOut,
  type OrderItemOut,
  type OrderOut,
  type OrderUsage,
  addOrderItem,
  getOrderUsage,
  listOrderEvents,
  listOrderItems,
  listOrders,
  removeOrderItem,
  updateOrderItem,
  updateOrderStatus,
} from '../api/orderApi'
import { type MenuItemOut, listStoreItems } from '../api/menuApi'
import { CustomerNoticeSection, OrderPaymentsSection } from './OrderMoneyPanel'

const COMMON_STATUSES = ['draft', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']
const POLL_INTERVAL_MS = 10_000
// Orders arrive as "submitted"; accepting one moves it to "confirmed".
const NEW_STATUS = 'submitted'
const ACCEPTED_STATUS = 'confirmed'
const CANCELLED_STATUS = 'cancelled'
// Placed and not finished: staff can still edit these (matches the backend).
const EDITABLE_STATUSES = ['submitted', 'confirmed', 'preparing', 'ready']

type DayGroup = { day: string; orders: OrderOut[]; count: number; total: number }
type MonthGroup = { month: string; days: DayGroup[]; count: number; total: number }

// Day and month summaries count real orders: not drafts (live voice sessions) or cancelled ones.
function isCounted(o: OrderOut): boolean {
  return o.status !== 'draft' && o.status !== CANCELLED_STATUS
}

function summarize(orders: OrderOut[]): { count: number; total: number } {
  const counted = orders.filter(isCounted)
  return { count: counted.length, total: counted.reduce((sum, o) => sum + Number(o.total), 0) }
}

// Group by the order's day in the store's timezone (code_day, "YYYY-MM-DD"), newest first.
// Orders keep the table's sort order inside each day.
function groupByMonthAndDay(orders: OrderOut[]): MonthGroup[] {
  const byDay = new Map<string, OrderOut[]>()
  for (const o of orders) byDay.set(o.code_day, [...(byDay.get(o.code_day) ?? []), o])
  const months = new Map<string, DayGroup[]>()
  for (const day of [...byDay.keys()].sort().reverse()) {
    const dayOrders = byDay.get(day)!
    const month = day.slice(0, 7)
    months.set(month, [...(months.get(month) ?? []), { day, orders: dayOrders, ...summarize(dayOrders) }])
  }
  return [...months.entries()].map(([month, days]) => ({
    month,
    days,
    ...summarize(days.flatMap((d) => d.orders)),
  }))
}

function monthLabel(month: string, lang: string): string {
  const [y, m] = month.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString(lang, { year: 'numeric', month: 'long' })
}

function dayLabel(day: string, lang: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(lang, { month: 'long', day: 'numeric', weekday: 'short' })
}

function apiErrorCode(err: unknown): string | null {
  return axios.isAxiosError(err) ? ((err.response?.data as { code?: string } | undefined)?.code ?? null) : null
}

type NotificationState = NotificationPermission | 'unsupported'

function currentNotificationState(): NotificationState {
  return typeof Notification === 'undefined' ? 'unsupported' : Notification.permission
}

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

// OWASP HTML-body encoding for values interpolated into the print receipt HTML.
function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
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

function channelLabel(channel: string, t: TFunction): React.JSX.Element | string {
  return channel === 'phone' ? <span className="badge badge-phone">📞 {t('orders.channelPhone')}</span> : channel
}

// Who placed the order: app account email, or the caller's number for phone orders.
function accountCell(order: OrderOut): React.JSX.Element | string {
  if (order.user_email) return order.user_email
  if (order.customer_phone) return <a href={`tel:${order.customer_phone}`}>{formatPhone(order.customer_phone)}</a>
  return '—'
}

const PAYMENT_BADGES: Record<string, { label: string; background: string; color: string }> = {
  paid: { label: 'payments.paid', background: '#dcfce7', color: '#15803d' },
  partially_paid: { label: 'orders.badgeBalanceDue', background: '#fef3c7', color: '#b45309' },
  refunded: { label: 'orders.badgeRefunded', background: '#e5e7eb', color: '#374151' },
  unpaid: { label: 'payments.unpaid', background: '#fee2e2', color: '#b91c1c' },
}

function paymentBadge(paymentStatus: string, t: TFunction): React.JSX.Element {
  const badge = PAYMENT_BADGES[paymentStatus] ?? PAYMENT_BADGES.unpaid
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 700,
        padding: '2px 8px',
        borderRadius: 999,
        background: badge.background,
        color: badge.color,
        whiteSpace: 'nowrap',
      }}
    >
      {t(badge.label)}
    </span>
  )
}

export function OrdersRoute(): React.JSX.Element {
  const { t, i18n } = useTranslation()
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

  const monthGroups = useMemo(() => groupByMonthAndDay(sortedOrders), [sortedOrders])
  // Only the newest month starts open; these hold the months/days the user has toggled.
  const [toggledMonths, setToggledMonths] = useState<Set<string>>(new Set())
  const [closedDays, setClosedDays] = useState<Set<string>>(new Set())
  const isMonthOpen = (month: string) => (month === monthGroups[0]?.month) !== toggledMonths.has(month)

  function toggleIn(set: Set<string>, key: string): Set<string> {
    const next = new Set(set)
    if (!next.delete(key)) next.add(key)
    return next
  }

  const selectedOrder = useMemo(
    () => orders.find((o) => o.id === selectedOrderId) ?? null,
    [orders, selectedOrderId],
  )

  const closeDetails = useCallback(() => setSelectedOrderId(null), [])

  // While the details window is open: Esc closes it and the page behind doesn't scroll.
  useEffect(() => {
    if (!selectedOrderId) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeDetails() }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [selectedOrderId, closeDetails])

  const [items, setItems] = useState<OrderItemOut[]>([])
  const [usage, setUsage] = useState<OrderUsage | null>(null)
  const [events, setEvents] = useState<OrderEventOut[]>([])
  const [menuItems, setMenuItems] = useState<MenuItemOut[] | null>(null)
  const [busy, setBusy] = useState(false)
  // Bumped after every change so the payments and customer-notice sections reload.
  const [detailVersion, setDetailVersion] = useState(0)
  const [noteDraft, setNoteDraft] = useState<{ id: string; text: string } | null>(null)
  const [addForm, setAddForm] = useState({ itemId: '', variantId: '', quantity: 1, note: '' })
  const knownStatuses = useRef<Map<string, string> | null>(null)
  const [notificationState, setNotificationState] = useState<NotificationState>(currentNotificationState)
  const openNotifications = useRef(new Map<string, Notification>())

  const notifyNewOrder = useCallback((order: OrderOut): void => {
    if (currentNotificationState() !== 'granted') return
    try {
      const n = new Notification(t('orders.newOrderNotification', { code: order.short_code }), {
        body: `$${String(order.total)}${order.customer_name ? ` · ${order.customer_name}` : ''}${
          order.customer_phone ? ` · 📞 ${formatPhone(order.customer_phone)}` : ''
        }`,
        tag: order.id,
        requireInteraction: true,
      })
      n.onclick = () => {
        window.focus()
        setSelectedOrderId(order.id)
        n.close()
      }
      openNotifications.current.set(order.id, n)
    } catch { /* notifications not available */ }
  }, [t])

  const reloadOrders = useCallback(async (selectId?: string): Promise<void> => {
    const data = await listOrders()
    if (knownStatuses.current !== null) {
      // New non-draft order, or status changed from draft to something else
      const fresh = data.filter((o) => {
        const prev = knownStatuses.current!.get(o.id)
        return o.status !== 'draft' && (prev === undefined || prev === 'draft')
      })
      if (fresh.length) playBeep()
      fresh.filter((o) => o.status === NEW_STATUS).forEach(notifyNewOrder)
    }
    knownStatuses.current = new Map(data.map((o) => [o.id, o.status]))
    setOrders(data)
    if (selectId) setSelectedOrderId(selectId)
  }, [notifyNewOrder])

  // Oldest first: the order waiting longest is accepted first.
  const newOrders = useMemo(
    () => orders.filter((o) => o.status === NEW_STATUS).sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [orders],
  )

  // Flash the tab title while orders wait, so it shows from another tab too.
  useEffect(() => {
    if (!newOrders.length) return
    const baseTitle = document.title
    let flash = false
    const id = setInterval(() => {
      flash = !flash
      document.title = flash ? `🔔 (${newOrders.length}) ${t('orders.newOrderAlert')}` : baseTitle
    }, 1000)
    return () => {
      clearInterval(id)
      document.title = baseTitle
    }
  }, [newOrders.length, t])

  async function requestNotifications(): Promise<void> {
    if (typeof Notification === 'undefined') return
    setNotificationState(await Notification.requestPermission())
  }

  async function handleAccept(order: OrderOut): Promise<void> {
    setError(null)
    try {
      const updated = await updateOrderStatus(order.id, ACCEPTED_STATUS)
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
      openNotifications.current.get(order.id)?.close()
      openNotifications.current.delete(order.id)
    } catch {
      setError(t('orders.failedUpdateOrder'))
    }
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
    const id = setInterval(() => { void reloadOrders().catch(() => {}) }, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [reloadOrders])

  useEffect(() => {
    setNoteDraft(null)
    setAddForm({ itemId: '', variantId: '', quantity: 1, note: '' })
    if (!selectedOrderId) {
      setItems([])
      setUsage(null)
      setEvents([])
      return
    }
    void (async () => {
      setError(null)
      try {
        const [data, usageData, eventData] = await Promise.all([
          listOrderItems(selectedOrderId),
          getOrderUsage(selectedOrderId).catch(() => null),
          listOrderEvents(selectedOrderId).catch(() => []),
        ])
        setItems(data)
        setUsage(usageData)
        setEvents(eventData)
      } catch {
        setError(t('orders.failedLoadItems'))
      }
    })()
  }, [selectedOrderId])

  const editable = selectedOrder !== null && EDITABLE_STATUSES.includes(selectedOrder.status)

  // The menu is only needed to add items, so load it the first time an editable order is opened.
  useEffect(() => {
    if (!editable || menuItems !== null) return
    listStoreItems().then(setMenuItems).catch(() => setMenuItems([]))
  }, [editable, menuItems])

  // Run a staff edit, then show the new totals, items and change history.
  async function applyEdit(edit: (orderId: string) => Promise<OrderOut>): Promise<boolean> {
    if (!selectedOrder) return false
    const orderId = selectedOrder.id
    setError(null)
    setBusy(true)
    try {
      const updated = await edit(orderId)
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
      const [data, eventData] = await Promise.all([listOrderItems(orderId), listOrderEvents(orderId)])
      setItems(data)
      setEvents(eventData)
      setDetailVersion((v) => v + 1)
      return true
    } catch (err) {
      const code = apiErrorCode(err)
      setError(
        code === 'last_item' ? t('orders.lastItem')
          : code === 'order_not_editable' ? t('orders.notEditable')
          : t('orders.failedUpdateOrder'),
      )
      return false
    } finally {
      setBusy(false)
    }
  }

  // A payment, refund or "customer told" was recorded in the money sections.
  async function handleMoneyChanged(): Promise<void> {
    if (!selectedOrderId) return
    const orderId = selectedOrderId
    try {
      const [, eventData] = await Promise.all([reloadOrders(), listOrderEvents(orderId)])
      setEvents(eventData)
      setDetailVersion((v) => v + 1)
    } catch { /* the next poll catches up */ }
  }

  async function saveNote(): Promise<void> {
    if (!noteDraft) return
    const { id, text } = noteDraft
    setNoteDraft(null)
    if (text.trim() === (items.find((it) => it.id === id)?.note ?? '')) return
    await applyEdit((orderId) => updateOrderItem(orderId, id, { note: text }))
  }

  const addMenuItem = menuItems?.find((m) => m.id === addForm.itemId) ?? null
  const addOptions = (addMenuItem?.variants ?? []).filter((v) => v.availability)

  async function handleAddItem(): Promise<void> {
    if (!addMenuItem) return
    const ok = await applyEdit((orderId) => addOrderItem(orderId, {
      menu_item_id: addMenuItem.id,
      variant_id: addForm.variantId || null,
      quantity: addForm.quantity,
      note: addForm.note.trim() || null,
    }))
    if (ok) setAddForm({ itemId: '', variantId: '', quantity: 1, note: '' })
  }

  async function handleCancelOrder(): Promise<void> {
    if (!selectedOrder) return
    if (!window.confirm(t('orders.confirmCancelOrder', { code: selectedOrder.short_code }))) return
    await applyEdit((orderId) => updateOrderStatus(orderId, CANCELLED_STATUS))
  }

  function handlePrint(): void {
    if (!selectedOrder) return
    const rows = items.map((it) =>
      `<tr>
        <td style="padding:4px 8px">${escapeHtml(it.name ?? 'Unknown item')}${it.variant_name ? ` (${escapeHtml(it.variant_name)})` : ''}${it.note ? `<br/><span style="font-size:11px;color:#666;font-style:italic">${escapeHtml(it.note)}</span>` : ''}</td>
        <td style="padding:4px 8px;text-align:center">${escapeHtml(it.quantity)}</td>
        <td style="padding:4px 8px;text-align:right">$${escapeHtml(it.price_snapshot)}</td>
        <td style="padding:4px 8px;text-align:right">$${(Number(it.price_snapshot) * it.quantity).toFixed(2)}</td>
      </tr>`
    ).join('')
    const orderNote = selectedOrder.notes ? `<div style="margin-top:12px;font-style:italic;font-size:12px;color:#666">Note: ${escapeHtml(selectedOrder.notes)}</div>` : ''

    const html = `<!DOCTYPE html><html><head><title>Order ${escapeHtml(selectedOrder.short_code)}</title>
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
      <h2>Order #${escapeHtml(selectedOrder.short_code)}</h2>
      <div class="meta">
        ${escapeHtml(localTime(selectedOrder.created_at))}<br/>
        Status: ${escapeHtml(selectedOrder.status)} &nbsp; Channel: ${escapeHtml(selectedOrder.channel)}
        ${selectedOrder.customer_name ? `<br/>Customer: <strong>${escapeHtml(selectedOrder.customer_name)}</strong>` : ''}
        ${selectedOrder.user_email ? `<br/>Account: ${escapeHtml(selectedOrder.user_email)}` : ''}
        ${selectedOrder.customer_phone ? `<br/>Phone: <strong>${escapeHtml(formatPhone(selectedOrder.customer_phone))}</strong>` : ''}
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
        <div class="row"><span>Subtotal</span><span>$${escapeHtml(selectedOrder.subtotal)}</span></div>
        <div class="row"><span>Tax</span><span>$${escapeHtml(selectedOrder.tax)}</span></div>
        <div class="row total"><span>Total</span><span>$${escapeHtml(selectedOrder.total)}</span></div>
      </div>
      <script>window.onload=function(){window.print()}<\/script>
    </body></html>`

    const w = window.open('', '_blank')
    if (w) { w.document.write(html); w.document.close() }
  }

  async function handleUpdateStatus(next: string): Promise<void> {
    await applyEdit((orderId) => updateOrderStatus(orderId, next))
  }

  return (
    <>
      {newOrders.length > 0 && (
        <div className="new-order-overlay" role="alertdialog" aria-modal="true" aria-labelledby="new-order-title">
          <div className="new-order-card">
            <h2 id="new-order-title">{t('orders.newOrderAlert')}</h2>
            <p style={{ margin: '0 0 12px', color: 'var(--color-text-secondary)' }}>
              {t('orders.newOrdersWaiting', { count: newOrders.length })}
            </p>
            {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
            {newOrders.map((o) => (
              <div key={o.id} className="new-order-row">
                <div>
                  <div className="mono" style={{ fontSize: 20, fontWeight: 700, letterSpacing: 1 }}>#{o.short_code}</div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                    {localTime(o.created_at)}
                    {o.fulfillment_type && <span style={{ textTransform: 'capitalize' }}> · {o.fulfillment_type}</span>}
                    {o.customer_name && <> · {o.customer_name}</>}
                    {o.customer_phone && <> · 📞 {formatPhone(o.customer_phone)}</>}
                  </div>
                  <div style={{ fontWeight: 700, color: 'var(--color-primary)' }}>${String(o.total)}</div>
                </div>
                <button className="btn btn-primary" onClick={() => void handleAccept(o)}>
                  {t('orders.accept')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="page-header">
        <h1>{t('orders.title')}</h1>
        <p>{t('orders.subtitle')}</p>
        {notificationState === 'default' && (
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 8 }} onClick={() => void requestNotifications()}>
            {t('orders.enableNotifications')}
          </button>
        )}
        {notificationState === 'denied' && (
          <p style={{ marginTop: 8, fontSize: 12 }}>{t('orders.notificationsBlocked')}</p>
        )}
      </div>

      {error && !selectedOrder && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

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
                <th style={thStyle}>{t('orders.payment')}</th>
                <th style={thStyle}>{t('orders.orderId')}</th>
              </tr>
            </thead>
            <tbody>
              {monthGroups.map((mg) => (
                <React.Fragment key={mg.month}>
                  <tr
                    onClick={() => setToggledMonths((s) => toggleIn(s, mg.month))}
                    style={{ cursor: 'pointer', background: 'var(--color-bg)', borderBottom: '1px solid var(--color-border, #e5e7eb)' }}
                  >
                    <td colSpan={9} style={{ ...tdStyle, fontSize: 14, fontWeight: 700 }}>
                      {isMonthOpen(mg.month) ? '▾' : '▸'} {monthLabel(mg.month, i18n.language)}
                      <span style={{ marginLeft: 12, fontWeight: 500, color: 'var(--color-text-secondary)' }}>
                        {t('orders.orderCount', { count: mg.count })} · ${mg.total.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                  {isMonthOpen(mg.month) && mg.days.map((dg) => (
                    <React.Fragment key={dg.day}>
                      <tr
                        onClick={() => setClosedDays((s) => toggleIn(s, dg.day))}
                        style={{ cursor: 'pointer', borderBottom: '1px solid var(--color-border, #f0f0f0)' }}
                      >
                        <td colSpan={9} style={{ ...tdStyle, paddingLeft: 28, fontWeight: 600 }}>
                          {closedDays.has(dg.day) ? '▸' : '▾'} {dayLabel(dg.day, i18n.language)}
                          <span style={{ marginLeft: 12, fontWeight: 400, color: 'var(--color-text-secondary)' }}>
                            {t('orders.orderCount', { count: dg.count })} · ${dg.total.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                      {!closedDays.has(dg.day) && dg.orders.map((o) => (
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
                  <td style={tdStyle}>{channelLabel(o.channel, t)}</td>
                  <td style={{ ...tdStyle, fontSize: 12, color: 'var(--color-text-secondary)' }}>{accountCell(o)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>${String(o.subtotal)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>${String(o.tax)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>${String(o.total)}</td>
                  <td style={tdStyle}>{paymentBadge(o.payment_status, t)}</td>
                  <td style={{ ...tdStyle, fontSize: 14, fontWeight: 700, letterSpacing: 1 }} className="mono">{o.short_code}</td>
                </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
          {!orders.length && !loading && <div className="empty-state" style={{ padding: 24 }}>{t('orders.noOrders')}</div>}
        </div>
      </div>

      {/* Order details window (opens when an order is clicked) */}
      {selectedOrder && (
        <div className="order-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeDetails() }}>
        <div className="card order-modal" role="dialog" aria-modal="true" aria-labelledby="order-modal-title">
          <div className="card-header">
            <h2 id="order-modal-title">
              {t('orders.orderDetails')} <span className="mono" style={{ letterSpacing: 1 }}>#{selectedOrder.short_code}</span>
            </h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={handlePrint}>
                {t('orders.print')}
              </button>
              <button className="btn btn-secondary btn-sm" aria-label={t('orders.close')} title={t('orders.close')} onClick={closeDetails}>
                ✕
              </button>
            </div>
          </div>
          <div className="card-body">
            {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
            <div className="grid-2">
              <div className="form-group">
                <span className="meta-label">{t('orders.orderId')}</span>
                <span className="mono">{selectedOrder.id}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">Account</span>
                <span>{selectedOrder.channel === 'phone' ? channelLabel('phone', t) : (selectedOrder.user_email ?? '—')}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">{t('orders.created')}</span>
                <span>{localTime(selectedOrder.created_at)}</span>
              </div>
              <div className="form-group">
                <span className="meta-label">{t('orders.payment')}</span>
                <span>{paymentBadge(selectedOrder.payment_status, t)}</span>
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

            {selectedOrder.customer_phone && (
              <div className="form-group" style={{ marginTop: 12 }}>
                <span className="meta-label">{t('orders.callbackPhone')}</span>
                <a href={`tel:${selectedOrder.customer_phone}`} style={{ fontWeight: 600 }}>
                  {formatPhone(selectedOrder.customer_phone)}
                </a>
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
              {editable && (
                <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => void handleCancelOrder()}>
                  {t('orders.cancelOrder')}
                </button>
              )}
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
                    {editable && <th style={thStyle} />}
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
                      <td style={{ ...tdStyle, fontSize: 12, color: 'var(--color-text-secondary)', fontStyle: it.note ? 'italic' : undefined }}>
                        {noteDraft?.id === it.id ? (
                          <input
                            className="form-input"
                            autoFocus
                            maxLength={512}
                            value={noteDraft.text}
                            onChange={(e) => setNoteDraft({ id: it.id, text: e.target.value })}
                            onBlur={() => void saveNote()}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') void saveNote()
                              if (e.key === 'Escape') {
                                e.stopPropagation() // cancel the note edit, keep the window open
                                setNoteDraft(null)
                              }
                            }}
                          />
                        ) : (
                          <>
                            {it.note ?? '—'}
                            {editable && (
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ marginLeft: 6 }}
                                title={t('orders.editNote')}
                                disabled={busy}
                                onClick={() => setNoteDraft({ id: it.id, text: it.note ?? '' })}
                              >
                                ✏️
                              </button>
                            )}
                          </>
                        )}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'center' }}>
                        {editable && (
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={busy || it.quantity <= 1}
                            onClick={() => void applyEdit((orderId) => updateOrderItem(orderId, it.id, { quantity: it.quantity - 1 }))}
                          >
                            −
                          </button>
                        )}
                        <span style={{ margin: '0 8px' }}>{it.quantity}</span>
                        {editable && (
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={busy || it.quantity >= 99}
                            onClick={() => void applyEdit((orderId) => updateOrderItem(orderId, it.id, { quantity: it.quantity + 1 }))}
                          >
                            +
                          </button>
                        )}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right' }}>${String(it.price_snapshot)}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>${(Number(it.price_snapshot) * it.quantity).toFixed(2)}</td>
                      {editable && (
                        <td style={tdStyle}>
                          <button
                            className="btn btn-danger btn-sm"
                            disabled={busy}
                            onClick={() => void applyEdit((orderId) => removeOrderItem(orderId, it.id))}
                          >
                            {t('common.remove')}
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!items.length && <div className="empty-state" style={{ padding: '16px 0' }}>{t('orders.noItems')}</div>}

              {editable && (
                <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <select
                    className="form-select"
                    value={addForm.itemId}
                    onChange={(e) => setAddForm({ ...addForm, itemId: e.target.value, variantId: '' })}
                  >
                    <option value="">{t('orders.chooseItem')}</option>
                    {(menuItems ?? []).filter((m) => m.availability).map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}{m.variants?.length ? '' : ` — $${String(m.price)}`}
                      </option>
                    ))}
                  </select>
                  {addOptions.length > 0 && (
                    <select
                      className="form-select"
                      value={addForm.variantId}
                      onChange={(e) => setAddForm({ ...addForm, variantId: e.target.value })}
                    >
                      <option value="">{t('orders.chooseOption')}</option>
                      {addOptions.map((v) => (
                        <option key={v.id} value={v.id}>{v.name} — ${String(v.price)}</option>
                      ))}
                    </select>
                  )}
                  <input
                    className="form-input"
                    type="number"
                    min={1}
                    max={99}
                    style={{ width: 70 }}
                    value={addForm.quantity}
                    onChange={(e) => setAddForm({ ...addForm, quantity: Math.min(99, Math.max(1, Number(e.target.value) || 1)) })}
                  />
                  <input
                    className="form-input"
                    placeholder={t('orders.note')}
                    maxLength={512}
                    value={addForm.note}
                    onChange={(e) => setAddForm({ ...addForm, note: e.target.value })}
                  />
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={busy || !addMenuItem || (addOptions.length > 0 && !addForm.variantId)}
                    onClick={() => void handleAddItem()}
                  >
                    {t('orders.addItem')}
                  </button>
                </div>
              )}
            </div>

            <OrderPaymentsSection order={selectedOrder} version={detailVersion} onChanged={() => void handleMoneyChanged()} />
            <CustomerNoticeSection order={selectedOrder} version={detailVersion} onChanged={() => void handleMoneyChanged()} />

            <div style={{ marginTop: 20 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>{t('orders.history')}</h3>
              {events.length ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
                  {events.map((e) => (
                    <li key={e.id} style={{ marginBottom: 4 }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>{localTime(e.created_at)}</span>
                      {' · '}{e.detail}
                      {e.total_before !== null && e.total_after !== null && e.total_before !== e.total_after && (
                        <span style={{ marginLeft: 8, fontWeight: 600 }}>
                          ${String(e.total_before)} → ${String(e.total_after)}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{t('orders.noHistory')}</div>
              )}
            </div>
          </div>
        </div>
        </div>
      )}
    </>
  )
}
