import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  downloadInvoiceCsv,
  getInvoice,
  listInvoices,
  type Invoice,
  type InvoiceDetail,
  type InvoiceLine,
} from '../api/invoiceApi'

const thStyle: React.CSSProperties = { padding: '8px 10px', fontWeight: 600, whiteSpace: 'nowrap', textAlign: 'left' }
const tdStyle: React.CSSProperties = { padding: '8px 10px', whiteSpace: 'nowrap' }
const right: React.CSSProperties = { textAlign: 'right' }

function usd(v: string | number): string {
  const n = Number(v)
  const s = Math.abs(n).toFixed(2)
  return n < 0 ? `-$${s}` : `$${s}`
}

function monthName(period: string, lang: string): string {
  const [y, m] = period.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString(lang, { year: 'numeric', month: 'long' })
}

export function BillingRoute(): React.JSX.Element {
  const { t, i18n } = useTranslation()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<InvoiceDetail | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        setInvoices(await listInvoices())
      } catch {
        setError(t('billing.loadFailed'))
      } finally {
        setLoading(false)
      }
    })()
  }, [t])

  async function open(id: string): Promise<void> {
    try {
      setSelected(await getInvoice(id))
    } catch {
      setError(t('billing.loadFailed'))
    }
  }

  function statusLabel(inv: Invoice): React.JSX.Element {
    const [key, bg, fg] = inv.overdue
      ? ['overdue', '#fef2f2', '#dc2626']
      : {
          open: ['open', '#eff6ff', '#2563eb'],
          paid: ['paid', '#dcfce7', '#16a34a'],
          void: ['void', '#f3f4f6', '#6b7280'],
          uncollectible: ['uncollectible', '#fffbeb', '#92400e'],
        }[inv.status]
    return (
      <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: bg, color: fg }}>
        {t(`billing.status.${key}`)}
      </span>
    )
  }

  function lineLabel(line: InvoiceLine): string {
    if (line.kind === 'monthly_fee') return t('billing.monthlyFee')
    if (line.kind === 'order') {
      const channel = t(line.channel === 'phone' ? 'billing.phoneOrder' : 'billing.appOrder')
      return `${channel} #${line.order_code} · ${line.order_day}`
    }
    return line.description
  }

  return (
    <>
      <div className="page-header">
        <h1>{t('billing.title')}</h1>
        <p>{t('billing.subtitle')}</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ maxWidth: 900 }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                <th style={thStyle}>{t('billing.month')}</th>
                <th style={thStyle}>{t('billing.statusLabel')}</th>
                <th style={{ ...thStyle, ...right }}>{t('billing.orders')}</th>
                <th style={{ ...thStyle, ...right }}>{t('billing.total')}</th>
                <th style={thStyle}>{t('billing.due')}</th>
                <th style={thStyle} />
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
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{monthName(inv.period, i18n.language)}</td>
                  <td style={tdStyle}>{statusLabel(inv)}</td>
                  <td style={{ ...tdStyle, ...right }}>{inv.order_count}</td>
                  <td style={{ ...tdStyle, ...right, fontWeight: 600 }}>{usd(inv.total)}</td>
                  <td style={tdStyle}>{inv.due_date ?? '—'}</td>
                  <td style={tdStyle}>
                    {inv.status === 'open' && inv.hosted_url && (
                      <a
                        className="btn btn-primary btn-sm"
                        href={inv.hosted_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {t('billing.payNow')}
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && !invoices.length && (
            <div className="empty-state" style={{ padding: 24 }}>{t('billing.empty')}</div>
          )}
        </div>
      </div>

      {selected && (
        <div className="card" style={{ maxWidth: 900, marginTop: 20 }}>
          <div className="card-header">
            <h2>
              {monthName(selected.period, i18n.language)} {statusLabel(selected)}
            </h2>
            <div style={{ display: 'flex', gap: 8 }}>
              {selected.pdf_url && (
                <a className="btn btn-secondary btn-sm" href={selected.pdf_url} target="_blank" rel="noreferrer">
                  PDF
                </a>
              )}
              <button className="btn btn-secondary btn-sm" onClick={() => void downloadInvoiceCsv(selected)}>
                {t('billing.downloadCsv')}
              </button>
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--color-border, #e5e7eb)' }}>
                  <th style={thStyle}>{t('billing.item')}</th>
                  <th style={{ ...thStyle, ...right }}>{t('billing.subtotal')}</th>
                  <th style={{ ...thStyle, ...right }}>{t('billing.rate')}</th>
                  <th style={{ ...thStyle, ...right }}>{t('billing.commission')}</th>
                  <th style={{ ...thStyle, ...right }}>{t('billing.paidOnline')}</th>
                  <th style={{ ...thStyle, ...right }}>{t('billing.billed')}</th>
                </tr>
              </thead>
              <tbody>
                {selected.lines.map((line) => (
                  <tr key={line.id} style={{ borderBottom: '1px solid var(--color-border, #f0f0f0)' }}>
                    <td style={tdStyle}>{lineLabel(line)}</td>
                    <td style={{ ...tdStyle, ...right }}>{line.subtotal != null ? usd(line.subtotal) : ''}</td>
                    <td style={{ ...tdStyle, ...right }}>{line.commission_bps != null ? `${line.commission_bps / 100}%` : ''}</td>
                    <td style={{ ...tdStyle, ...right }}>{line.commission != null ? usd(line.commission) : ''}</td>
                    <td style={{ ...tdStyle, ...right }}>
                      {line.collected_online != null && Number(line.collected_online) > 0 ? usd(line.collected_online) : ''}
                    </td>
                    <td style={{ ...tdStyle, ...right, fontWeight: 600 }}>{usd(line.amount)}</td>
                  </tr>
                ))}
                <tr>
                  <td style={{ ...tdStyle, fontWeight: 700 }} colSpan={5}>
                    {t('billing.total')}
                  </td>
                  <td style={{ ...tdStyle, ...right, fontWeight: 800 }}>{usd(selected.total)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}
