import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { connectPayments, getPaymentStatus, type PaymentStatus } from '../api/paymentApi'

export function PaymentsCard(): React.JSX.Element {
  const { t } = useTranslation()
  const [status, setStatus] = useState<PaymentStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        setStatus(await getPaymentStatus())
      } catch {
        setError(t('payments.loadError'))
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleConnect(): Promise<void> {
    setConnecting(true)
    setError(null)
    try {
      // Open Stripe onboarding in a new tab so the store keeps this page open.
      // Stripe's return/refresh URLs point back here; re-fetch status on mount.
      const here = window.location.href
      const { url } = await connectPayments(here, here)
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch {
      setError(t('payments.connectError'))
    } finally {
      setConnecting(false)
    }
  }

  const feePct = status ? status.fee_bps / 100 : null

  return (
    <div className="card" style={{ maxWidth: 900, marginTop: 24 }}>
      <div className="card-header">
        <h2>{t('payments.title')}</h2>
      </div>
      <div className="card-body">
        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
        {loading && <div className="empty-state" style={{ padding: '16px 0' }}>{t('common.loading')}</div>}

        {status && (
          <>
            {/* Not connected — call to action */}
            {!status.connected && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text-secondary)' }}>
                  {t('payments.notConnected')}
                </p>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={connecting}
                  onClick={() => void handleConnect()}
                >
                  {connecting ? t('common.loading') : t('payments.connectBtn')}
                </button>
              </div>
            )}

            {/* Connected but not yet able to charge — warning */}
            {status.connected && !status.charges_enabled && (
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  background: '#fffbeb',
                  border: '1px solid #fde68a',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 16,
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <strong style={{ fontSize: 14, color: '#92400e' }}>⚠ {t('payments.incompleteTitle')}</strong>
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: '#92400e' }}>
                    {status.details_submitted ? t('payments.inReview') : t('payments.incompleteDesc')}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={connecting}
                  onClick={() => void handleConnect()}
                >
                  {connecting ? t('common.loading') : t('payments.continueBtn')}
                </button>
              </div>
            )}

            {/* Fully active */}
            {status.connected && status.charges_enabled && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    padding: '3px 10px',
                    borderRadius: 999,
                    background: '#dcfce7',
                    color: '#16a34a',
                  }}
                >
                  ✓ {t('payments.activeTitle')}
                </span>
                <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{t('payments.activeDesc')}</span>
              </div>
            )}

            {/* Commission (read-only) */}
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--color-border, #f0f0f0)' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span className="meta-label" style={{ marginBottom: 0 }}>{t('payments.platformFee')}</span>
                <span style={{ fontSize: 18, fontWeight: 700 }}>{feePct}%</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '6px 0 0' }}>
                {t('payments.feeDesc')}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
