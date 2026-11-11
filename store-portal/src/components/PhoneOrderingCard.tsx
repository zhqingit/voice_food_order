import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { updateMe, type StoreMe } from '../api/storeApi'
import { formatPhone } from '../phone'

type Props = {
  me: StoreMe
  onUpdated: (me: StoreMe) => void
}

function errorKey(err: unknown): string {
  const res = (err as { response?: { status?: number; data?: { code?: string } } }).response
  if (res?.status === 422) return 'phone.invalidNumber'
  if (res?.data?.code === 'phone_staff_number_invalid') return 'phone.staffSameAsAi'
  if (res?.data?.code === 'phone_ai_number_missing') return 'phone.noNumberYet'
  return 'phone.saveFailed'
}

export function PhoneOrderingCard({ me, onUpdated }: Props): React.JSX.Element {
  const { t } = useTranslation()
  const [staffNumber, setStaffNumber] = useState(me.phone_staff_number ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    setStaffNumber(me.phone_staff_number ?? '')
  }, [me.phone_staff_number])

  async function save(patch: Parameters<typeof updateMe>[0], okKey: string): Promise<void> {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      onUpdated(await updateMe(patch))
      setMessage(t(okKey))
    } catch (err) {
      setError(t(errorKey(err)))
    } finally {
      setSaving(false)
    }
  }

  const aiNumber = me.phone_ai_number
  const staffDirty = staffNumber.trim() !== (me.phone_staff_number ?? '')
  const hint: React.CSSProperties = { fontSize: 12, color: 'var(--color-text-secondary)', margin: '4px 0 0' }

  return (
    <div className="card" style={{ maxWidth: 900, marginTop: 24 }}>
      <div className="card-header">
        <h2>{t('phone.title')}</h2>
      </div>
      <div className="card-body">
        {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {!aiNumber ? (
          <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text-secondary)' }}>{t('phone.notSetUp')}</p>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <span className="meta-label">{t('phone.aiNumber')}</span>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{formatPhone(aiNumber)}</div>
              </div>
              <button
                type="button"
                className={`btn btn-sm ${me.phone_ai_enabled ? 'btn-primary' : 'btn-secondary'}`}
                style={{ minWidth: 100, ...(me.phone_ai_enabled ? { background: '#16a34a', borderColor: '#16a34a' } : {}) }}
                disabled={saving}
                onClick={() =>
                  void save(
                    { phone_ai_enabled: !me.phone_ai_enabled },
                    me.phone_ai_enabled ? 'phone.turnedOff' : 'phone.turnedOn',
                  )
                }
              >
                {me.phone_ai_enabled ? t('phone.on') : t('phone.off')}
              </button>
            </div>
            <p style={hint}>{me.phone_ai_enabled ? t('phone.onDesc') : t('phone.offDesc')}</p>

            <div className="form-group" style={{ marginTop: 20 }}>
              <label className="form-label">{t('phone.staffNumber')}</label>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                  className="form-input"
                  value={staffNumber}
                  onChange={(e) => setStaffNumber(e.target.value)}
                  inputMode="tel"
                  placeholder="+1 480 555 1234"
                  style={{ maxWidth: 240 }}
                />
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={saving || !staffDirty}
                  onClick={() => void save({ phone_staff_number: staffNumber.trim() || null }, 'phone.staffSaved')}
                >
                  {t('common.save')}
                </button>
              </div>
              <p style={hint}>{t('phone.staffDesc')}</p>
            </div>

            <div
              style={{
                marginTop: 20,
                padding: '12px 16px',
                borderRadius: 8,
                background: '#f5f3ff',
                border: '1px solid #ddd6fe',
                fontSize: 13,
              }}
            >
              <strong>{t('phone.setupTitle')}</strong>
              <ol style={{ margin: '8px 0 0', paddingLeft: 20, lineHeight: 1.6 }}>
                <li>{t('phone.setupForward', { number: formatPhone(aiNumber) })}</li>
                <li>{t('phone.setupTurnOn')}</li>
                <li>{t('phone.setupTest')}</li>
              </ol>
              <p style={{ ...hint, marginTop: 8 }}>{t('phone.paymentNote')}</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
