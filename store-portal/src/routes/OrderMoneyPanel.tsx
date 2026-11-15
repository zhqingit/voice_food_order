import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { useTranslation } from 'react-i18next'
import { formatPhone } from '../phone'
import {
  type CustomerNoticeOut,
  type OrderOut,
  type OrderPaymentsOut,
  getCustomerNotice,
  getOrderPayments,
  markCustomerNotified,
  recordInStorePayment,
  refundOrder,
} from '../api/orderApi'

const sectionTitle: React.CSSProperties = { margin: '0 0 12px', fontSize: 14, fontWeight: 600 }
const muted: React.CSSProperties = { color: 'var(--color-text-secondary)' }

function localTime(iso: string): string {
  const s = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  return new Date(s).toLocaleString()
}

function errorKey(err: unknown): string {
  const code = axios.isAxiosError(err) ? (err.response?.data as { code?: string } | undefined)?.code : undefined
  switch (code) {
    case 'refund_exceeds_paid':
    case 'refund_exceeds_card':
    case 'amount_exceeds_balance':
      return `orders.${code}`
    case 'stripe_error':
      return 'orders.stripeError'
    default:
      return 'orders.failedUpdateOrder'
  }
}

function moneyInput(value: string, onChange: (v: string) => void): React.JSX.Element {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      $
      <input
        className="form-input"
        type="number"
        min="0.01"
        step="0.01"
        style={{ width: 100 }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </span>
  )
}

type Props = {
  order: OrderOut
  // Bumped by the parent after any change to the order (items, status).
  version: number
  // A payment or refund was made: the parent reloads the order and its history.
  onChanged: () => void
}

/** What the customer paid and what is owed; refunds and payments taken at the counter. */
export function OrderPaymentsSection({ order, version, onChanged }: Props): React.JSX.Element | null {
  const { t } = useTranslation()
  const [data, setData] = useState<OrderPaymentsOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [refundAmount, setRefundAmount] = useState('')
  const [refundMethod, setRefundMethod] = useState<'card' | 'in_store'>('card')
  const [collectAmount, setCollectAmount] = useState('')

  // Reload when the order changes here or a webhook changes it (seen by the list's polling).
  useEffect(() => {
    let live = true
    getOrderPayments(order.id)
      .then((d) => { if (live) setData(d) })
      .catch(() => { if (live) setError(t('orders.failedLoadPayments')) })
    return () => { live = false }
  }, [order.id, order.payment_status, order.amount_paid, version, t])

  // Suggest the obvious amounts: the overpayment to refund, the balance to collect.
  useEffect(() => {
    if (!data) return
    setRefundAmount(Number(data.overpaid) > 0 ? String(data.overpaid) : '')
    setRefundMethod(Number(data.card_refundable) > 0 ? 'card' : 'in_store')
    setCollectAmount(Number(data.balance_due) > 0 ? String(data.balance_due) : '')
  }, [data])

  async function run(action: () => Promise<OrderPaymentsOut>): Promise<void> {
    setError(null)
    setBusy(true)
    try {
      setData(await action())
      onChanged()
    } catch (err) {
      setError(t(errorKey(err)))
    } finally {
      setBusy(false)
    }
  }

  function handleRefund(): void {
    const label = refundMethod === 'card' ? t('orders.toCard') : t('orders.inStore')
    if (!window.confirm(t('orders.confirmRefund', { amount: refundAmount, method: label }))) return
    void run(() => refundOrder(order.id, refundAmount, refundMethod))
  }

  if (!data) return error ? <div className="alert alert-error">{error}</div> : null

  const cancelled = order.status === 'cancelled'
  const kindLabel = (kind: string, method: string) =>
    `${kind === 'refund' ? t('orders.refund') : t('orders.payment')} · ${
      method === 'card' ? t('orders.card') : method === 'dispute' ? t('orders.dispute') : t('orders.inStore')
    }`

  return (
    <div style={{ marginTop: 20 }}>
      <h3 style={sectionTitle}>{t('orders.paymentsTitle')}</h3>
      {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
        <span>{t('orders.amountPaid')}: <strong>${data.net}</strong></span>
        {Number(data.refunded) > 0 && <span>{t('orders.amountRefunded')}: ${data.refunded}</span>}
        {Number(data.balance_due) > 0 && (
          <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{t('orders.balanceDue')}: ${data.balance_due}</span>
        )}
        {Number(data.overpaid) > 0 && (
          <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{t('orders.overpaid')}: ${data.overpaid}</span>
        )}
      </div>

      {data.payments.length > 0 && (
        <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: 13 }}>
          {data.payments.map((p) => (
            <li key={p.id} style={{ marginBottom: 2 }}>
              <span style={muted}>{localTime(p.created_at)}</span> · {kindLabel(p.kind, p.method)} · ${p.amount}
              {p.status !== 'succeeded' && <> · <em>{t(`orders.paymentStatus_${p.status}`)}</em></>}
              {p.failure_reason && <span style={muted}> ({p.failure_reason})</span>}
            </li>
          ))}
        </ul>
      )}

      {Number(data.net) > 0 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {moneyInput(refundAmount, setRefundAmount)}
          <select
            className="form-select"
            value={refundMethod}
            onChange={(e) => setRefundMethod(e.target.value as 'card' | 'in_store')}
          >
            <option value="card" disabled={Number(data.card_refundable) <= 0}>
              {t('orders.toCard')}{Number(data.card_refundable) > 0 ? ` (≤ $${data.card_refundable})` : ''}
            </option>
            <option value="in_store">{t('orders.inStore')}</option>
          </select>
          <button className="btn btn-danger btn-sm" disabled={busy || !(Number(refundAmount) > 0)} onClick={handleRefund}>
            {t('orders.refund')}
          </button>
        </div>
      )}

      {!cancelled && Number(data.balance_due) > 0 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {moneyInput(collectAmount, setCollectAmount)}
          <button
            className="btn btn-secondary btn-sm"
            disabled={busy || !(Number(collectAmount) > 0)}
            onClick={() => void run(() => recordInStorePayment(order.id, collectAmount))}
          >
            {t('orders.recordInStorePayment')}
          </button>
          {order.user_id && <span style={{ ...muted, fontSize: 12 }}>{t('orders.balancePayableInApp')}</span>}
        </div>
      )}
    </div>
  )
}

/** Remind staff to tell the customer about changes, with the message to read out (or text, later). */
export function CustomerNoticeSection({ order, version, onChanged }: Props): React.JSX.Element | null {
  const { t } = useTranslation()
  const [notice, setNotice] = useState<CustomerNoticeOut | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    getCustomerNotice(order.id).then((n) => { if (live) setNotice(n) }).catch(() => {})
    return () => { live = false }
  }, [order.id, order.status, order.payment_status, version])

  async function handleMarkCalled(): Promise<void> {
    setError(null)
    setBusy(true)
    try {
      setNotice(await markCustomerNotified(order.id, 'call'))
      onChanged()
    } catch {
      setError(t('orders.failedUpdateOrder'))
    } finally {
      setBusy(false)
    }
  }

  if (!notice) return null
  if (!notice.pending) {
    return notice.last_notified_at ? (
      <div style={{ marginTop: 20, fontSize: 13, ...muted }}>
        {t('orders.customerNotifiedAt', { time: localTime(notice.last_notified_at) })}
      </div>
    ) : null
  }

  return (
    <div
      style={{
        marginTop: 20,
        padding: 12,
        borderRadius: 10,
        background: '#fff7ed',
        border: '1px solid #fdba74',
      }}
    >
      <h3 style={{ ...sectionTitle, color: '#c2410c' }}>{t('orders.notifyTitle')}</h3>
      {error && <div className="alert alert-error" style={{ marginBottom: 8 }}>{error}</div>}
      <p style={{ margin: '0 0 8px', fontSize: 13 }}>{t('orders.notifyHint')}</p>
      <div style={{ padding: 10, background: 'var(--color-surface)', borderRadius: 8, fontSize: 13, whiteSpace: 'pre-wrap' }}>
        {notice.message}
      </div>
      <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {notice.phone ? (
          <a className="btn btn-secondary btn-sm" href={`tel:${notice.phone}`}>📞 {formatPhone(notice.phone)}</a>
        ) : (
          <span style={{ fontSize: 12, ...muted }}>{t('orders.noCustomerPhone')}</span>
        )}
        <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => void handleMarkCalled()}>
          {t('orders.markNotified')}
        </button>
        <button className="btn btn-secondary btn-sm" disabled title={t('orders.smsNotAvailable')}>
          {t('orders.sendText')}
        </button>
      </div>
    </div>
  )
}
