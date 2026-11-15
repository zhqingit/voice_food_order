import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import {
  createPromotion,
  deletePromotion,
  listPromotions,
  updatePromotion,
  type Promotion,
  type PromotionChannels,
  type PromotionKind,
} from '../api/promotionApi'

const tdStyle: React.CSSProperties = { padding: '10px 12px', verticalAlign: 'top' }

function money(v: string): string {
  return `$${Number(v).toFixed(2)}`
}

// "10% off orders of $20.00 or more" — display only; the backend computes every discount.
export function promotionTerms(p: Pick<Promotion, 'kind' | 'value' | 'min_subtotal'>, t: TFunction): string {
  const off =
    p.kind === 'percent'
      ? t('promotions.percentOff', { value: Number(p.value) })
      : t('promotions.amountOff', { value: money(p.value) })
  return Number(p.min_subtotal) > 0
    ? t('promotions.withMinimum', { off, min: money(p.min_subtotal) })
    : t('promotions.anyOrder', { off })
}

function errorCode(err: unknown): string | null {
  const res = (err as { response?: { status?: number; data?: { code?: string } } }).response
  if (res?.status === 422) return 'invalid'
  return res?.data?.code ?? null
}

export function PromotionsRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [promos, setPromos] = useState<Promotion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [name, setName] = useState('')
  const [kind, setKind] = useState<PromotionKind>('percent')
  const [value, setValue] = useState('')
  const [minSubtotal, setMinSubtotal] = useState('')
  const [channels, setChannels] = useState<PromotionChannels>('all')
  const [startsOn, setStartsOn] = useState('')
  const [endsOn, setEndsOn] = useState('')

  async function reload(): Promise<void> {
    try {
      setPromos(await listPromotions())
    } catch {
      setError(t('promotions.loadFailed'))
    }
  }

  useEffect(() => {
    void (async () => {
      await reload()
      setLoading(false)
    })()
  }, [])

  async function run(fn: () => Promise<void>): Promise<void> {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await reload()
    } catch (err) {
      const code = errorCode(err)
      setError(t(`promotions.errors.${code ?? 'generic'}`, { defaultValue: t('promotions.errors.generic') }))
    } finally {
      setBusy(false)
    }
  }

  function handleCreate(e: React.FormEvent): void {
    e.preventDefault()
    const v = Number(value)
    const min = minSubtotal ? Number(minSubtotal) : 0
    if (!name.trim() || !(v > 0) || (kind === 'percent' && v > 100) || min < 0) {
      setError(t('promotions.errors.invalid'))
      return
    }
    void run(async () => {
      await createPromotion({
        name: name.trim(),
        kind,
        value: v.toFixed(2),
        min_subtotal: min.toFixed(2),
        channels,
        starts_on: startsOn || null,
        ends_on: endsOn || null,
      })
      setName('')
      setValue('')
      setMinSubtotal('')
      setStartsOn('')
      setEndsOn('')
    })
  }

  function handleDelete(p: Promotion): void {
    if (!window.confirm(t('promotions.confirmDelete', { name: p.name }))) return
    void run(() => deletePromotion(p.id))
  }

  function dates(p: Promotion): string {
    if (!p.starts_on && !p.ends_on) return t('promotions.noEnd')
    return `${p.starts_on ?? '…'} → ${p.ends_on ?? '…'}`
  }

  return (
    <>
      <div className="page-header">
        <h1>{t('promotions.title')}</h1>
        <p>{t('promotions.subtitle')}</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ maxWidth: 900, marginBottom: 24 }}>
        <div className="card-header">
          <h2>{t('promotions.new')}</h2>
        </div>
        <form className="card-body" onSubmit={handleCreate}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">{t('promotions.name')}</label>
              <input
                className="form-input"
                maxLength={120}
                placeholder={t('promotions.namePlaceholder')}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">{t('promotions.type')}</label>
              <select className="form-select" value={kind} onChange={(e) => setKind(e.target.value as PromotionKind)}>
                <option value="percent">{t('promotions.typePercent')}</option>
                <option value="amount_off">{t('promotions.typeAmount')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{kind === 'percent' ? t('promotions.percent') : t('promotions.amount')}</label>
              <input
                className="form-input"
                type="number"
                min="0.01"
                max={kind === 'percent' ? '100' : undefined}
                step="0.01"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">{t('promotions.minSubtotal')}</label>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="0"
                value={minSubtotal}
                onChange={(e) => setMinSubtotal(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">{t('promotions.channels')}</label>
              <select
                className="form-select"
                value={channels}
                onChange={(e) => setChannels(e.target.value as PromotionChannels)}
              >
                <option value="all">{t('promotions.channelAll')}</option>
                <option value="app">{t('promotions.channelApp')}</option>
                <option value="phone">{t('promotions.channelPhone')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('promotions.dates')}</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="form-input" type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} />
                <input className="form-input" type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} />
              </div>
            </div>
          </div>
          <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '4px 0 12px' }}>
            {t('promotions.rules')}
          </p>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {t('promotions.create')}
          </button>
        </form>
      </div>

      <div className="card" style={{ maxWidth: 900 }}>
        <div className="card-header">
          <h2>{t('promotions.list')}</h2>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <tbody>
            {promos.map((p) => (
              <tr key={p.id} style={{ borderBottom: '1px solid var(--color-border, #f0f0f0)', opacity: p.is_active ? 1 : 0.55 }}>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 700 }}>{p.name}</div>
                  <div>{promotionTerms(p, t)}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                    {t(`promotions.channel${p.channels === 'all' ? 'All' : p.channels === 'app' ? 'App' : 'Phone'}`)} · {dates(p)} ·{' '}
                    {t('promotions.used', { count: p.orders_count })}
                  </div>
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button
                    className={`btn btn-sm ${p.is_active ? 'btn-secondary' : 'btn-primary'}`}
                    disabled={busy}
                    onClick={() => void run(async () => void (await updatePromotion(p.id, { is_active: !p.is_active })))}
                  >
                    {p.is_active ? t('promotions.turnOff') : t('promotions.turnOn')}
                  </button>{' '}
                  {p.orders_count === 0 && (
                    <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => handleDelete(p)}>
                      {t('promotions.delete')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !promos.length && <div className="empty-state" style={{ padding: 24 }}>{t('promotions.empty')}</div>}
      </div>
    </>
  )
}
