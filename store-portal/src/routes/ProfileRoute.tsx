import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getMe, updateMe, uploadLogo, getHours, updateHours, type StoreMe, type DayHours } from '../api/storeApi'
import { MAX_UPLOAD_BYTES, MAX_UPLOAD_SIZE_LABEL } from '../config'

const DAY_KEYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const

function defaultHours(): DayHours[] {
  return Array.from({ length: 7 }, (_, i) => ({
    day_of_week: i,
    open_time: '09:00',
    close_time: '21:00',
    is_closed: false,
  }))
}

export function ProfileRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [me, setMe] = useState<StoreMe | null>(null)

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [address1, setAddress1] = useState('')
  const [address2, setAddress2] = useState('')
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [postal, setPostal] = useState('')
  const [country, setCountry] = useState('')
  const [timezone, setTimezone] = useState('')
  const [allowPickup, setAllowPickup] = useState<boolean>(true)
  const [allowDelivery, setAllowDelivery] = useState<boolean>(true)
  const [minOrder, setMinOrder] = useState('')
  const [taxRate, setTaxRate] = useState('')
  const logoInputRef = useRef<HTMLInputElement>(null)

  // Working hours state
  const [hours, setHours] = useState<DayHours[]>([])
  const [hoursSaving, setHoursSaving] = useState(false)

  // Track whether any field differs from saved state
  const isDirty = useMemo(() => {
    if (!me) return false
    return (
      name !== me.name ||
      phone !== (me.phone ?? '') ||
      address1 !== (me.address_line1 ?? '') ||
      address2 !== (me.address_line2 ?? '') ||
      city !== (me.city ?? '') ||
      state !== (me.state ?? '') ||
      postal !== (me.postal_code ?? '') ||
      country !== (me.country ?? '') ||
      timezone !== (me.timezone ?? '') ||
      allowPickup !== Boolean(me.allow_pickup ?? true) ||
      allowDelivery !== Boolean(me.allow_delivery ?? true) ||
      minOrder !== (me.min_order_amount != null ? String(me.min_order_amount) : '') ||
      taxRate !== String(Number(me.tax_rate ?? 0) * 100)
    )
  }, [me, name, phone, address1, address2, city, state, postal, country, timezone, allowPickup, allowDelivery, minOrder, taxRate])

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const [data, hoursData] = await Promise.all([getMe(), getHours()])
        setMe(data)
        setName(data.name)
        setPhone(data.phone ?? '')
        setAddress1(data.address_line1 ?? '')
        setAddress2(data.address_line2 ?? '')
        setCity(data.city ?? '')
        setState(data.state ?? '')
        setPostal(data.postal_code ?? '')
        setCountry(data.country ?? '')
        setTimezone(data.timezone ?? '')
        setAllowPickup(Boolean(data.allow_pickup ?? true))
        setAllowDelivery(Boolean(data.allow_delivery ?? true))
        setMinOrder(data.min_order_amount != null ? String(data.min_order_amount) : '')
        setTaxRate(String(Number(data.tax_rate ?? 0) * 100))
        setHours(hoursData)
      } catch {
        setError(t('profile.failedLoad'))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function handleSave(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    setError(null)
    setMessage(null)

    const minOrderParsed = minOrder.trim() ? Number(minOrder) : null
    if (minOrderParsed != null && (!Number.isFinite(minOrderParsed) || minOrderParsed < 0)) {
      setError(t('profile.invalidMinOrder'))
      return
    }

    const taxRateParsed = taxRate.trim() ? Number(taxRate) / 100 : 0
    if (!Number.isFinite(taxRateParsed) || taxRateParsed < 0 || taxRateParsed > 1) {
      setError(t('profile.invalidTaxRate'))
      return
    }

    try {
      const updated = await updateMe({
        name: name.trim() ? name.trim() : undefined,
        phone: phone.trim() ? phone.trim() : null,
        address_line1: address1.trim() ? address1.trim() : null,
        address_line2: address2.trim() ? address2.trim() : null,
        city: city.trim() ? city.trim() : null,
        state: state.trim() ? state.trim() : null,
        postal_code: postal.trim() ? postal.trim() : null,
        country: country.trim() ? country.trim() : null,
        timezone: timezone.trim() ? timezone.trim() : null,
        allow_pickup: allowPickup,
        allow_delivery: allowDelivery,
        min_order_amount: minOrderParsed,
        tax_rate: taxRateParsed,
      })
      setMe(updated)
      setMessage(t('profile.saved'))
    } catch {
      setError(t('profile.failedSave'))
    }
  }

  async function handleTogglePublish(): Promise<void> {
    if (!me) return
    setError(null)
    setMessage(null)
    try {
      const updated = await updateMe({ is_published: !me.is_published })
      setMe(updated)
      setMessage(updated.is_published ? t('profile.publishedOn') : t('profile.publishedOff'))
    } catch {
      setError(t('profile.failedSave'))
    }
  }

  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setMessage(null)
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(t('common.fileTooLarge', { names: file.name, max: MAX_UPLOAD_SIZE_LABEL }))
      if (logoInputRef.current) logoInputRef.current.value = ''
      return
    }
    try {
      const updated = await uploadLogo(file)
      setMe(updated)
      setMessage(t('profile.logoUploaded'))
    } catch {
      setError(t('profile.logoUploadFailed'))
    } finally {
      if (logoInputRef.current) logoInputRef.current.value = ''
    }
  }

  // ── Hours helpers ────────────────────────────────────────────────────────

  function updateDay(dayIndex: number, patch: Partial<DayHours>): void {
    setHours((prev) => prev.map((d) => (d.day_of_week === dayIndex ? { ...d, ...patch } : d)))
  }

  async function handleSaveHours(): Promise<void> {
    setError(null)
    setMessage(null)
    setHoursSaving(true)
    try {
      const saved = await updateHours(hours)
      setHours(saved)
      setMessage(t('profile.hoursSaved'))
    } catch {
      setError(t('profile.hoursFailedSave'))
    } finally {
      setHoursSaving(false)
    }
  }

  function handleSetDefaultHours(): void {
    setHours(defaultHours())
  }

  return (
    <>
      <div className="page-header">
        <h1>{t('profile.title')}</h1>
        <p>{t('profile.subtitle')}</p>
      </div>

      {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}
      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Publish Toggle Card */}
      {me && (
        <div className="card" style={{ maxWidth: 900, marginBottom: 24 }}>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 16 }}>{t('profile.publishTitle')}</h3>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {t('profile.publishDesc')}
              </p>
            </div>
            <button
              type="button"
              className={`btn btn-sm ${me.is_published ? 'btn-primary' : 'btn-secondary'}`}
              style={{
                minWidth: 100,
                ...(me.is_published ? { background: '#16a34a', borderColor: '#16a34a' } : {}),
              }}
              onClick={() => void handleTogglePublish()}
            >
              {me.is_published ? t('profile.published') : t('profile.unpublished')}
            </button>
          </div>
        </div>
      )}

      <div className="card" style={{ maxWidth: 900 }}>
        <div className="card-header">
          <h2>{t('profile.storeInfo')}</h2>
        </div>

        {loading && (
          <div className="card-body">
            <div className="empty-state" style={{ padding: '16px 0' }}>{t('common.loading')}</div>
          </div>
        )}

        {me && (
          <form className="card-body" onSubmit={(e) => void handleSave(e)}>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">{t('profile.storeName')}</label>
                <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('profile.phone')}</label>
                <input className="form-input" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>

              <div className="form-group grid-full">
                <label className="form-label">{t('profile.emailReadOnly')}</label>
                <input className="form-input" value={me.email} readOnly style={{ opacity: 0.7 }} />
              </div>

              <div className="form-group grid-full">
                <label className="form-label">{t('profile.addressLine1')}</label>
                <input className="form-input" value={address1} onChange={(e) => setAddress1(e.target.value)} />
              </div>
              <div className="form-group grid-full">
                <label className="form-label">{t('profile.addressLine2')}</label>
                <input className="form-input" value={address2} onChange={(e) => setAddress2(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">{t('profile.city')}</label>
                <input className="form-input" value={city} onChange={(e) => setCity(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('profile.state')}</label>
                <input className="form-input" value={state} onChange={(e) => setState(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">{t('profile.postalCode')}</label>
                <input className="form-input" value={postal} onChange={(e) => setPostal(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('profile.country')}</label>
                <input className="form-input" value={country} onChange={(e) => setCountry(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">{t('profile.timezone')}</label>
                <input className="form-input" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('profile.minOrderAmount')}</label>
                <input className="form-input" value={minOrder} onChange={(e) => setMinOrder(e.target.value)} inputMode="decimal" placeholder="0.00" />
              </div>
              <div className="form-group">
                <label className="form-label">{t('profile.taxRate')}</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input className="form-input" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} inputMode="decimal" placeholder="0" style={{ flex: 1 }} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-secondary)' }}>%</span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--color-text-secondary)', margin: '4px 0 0' }}>{t('profile.taxRateDesc')}</p>
              </div>

              <div className="form-group grid-full" style={{ flexDirection: 'row', gap: 24 }}>
                <label className="form-check">
                  <input type="checkbox" checked={allowPickup} onChange={(e) => setAllowPickup(e.target.checked)} />
                  {t('profile.allowPickup')}
                </label>
                <label className="form-check">
                  <input type="checkbox" checked={allowDelivery} onChange={(e) => setAllowDelivery(e.target.checked)} />
                  {t('profile.allowDelivery')}
                </label>
              </div>

              <div className="form-group grid-full">
                <label className="form-label">{t('profile.storeLogo')}</label>
                <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '0 0 8px' }}>{t('profile.logoDesc')}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {me.logo_url && (
                    <img
                      src={me.logo_url}
                      alt="Store logo"
                      style={{ width: 64, height: 64, borderRadius: 12, objectFit: 'cover', border: '1px solid #e5e7eb' }}
                    />
                  )}
                  <div>
                    <input
                      ref={logoInputRef}
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      onChange={(e) => void handleLogoUpload(e)}
                    />
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => logoInputRef.current?.click()}>
                      {me.logo_url ? t('profile.changeLogo') : t('profile.uploadLogo')}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex-end grid-full">
                <button
                  type="submit"
                  className={`btn ${isDirty ? 'btn-warning' : 'btn-primary'}`}
                  style={isDirty ? { animation: 'none', background: '#f59e0b', color: '#fff' } : undefined}
                >
                  {isDirty ? `● ${t('common.save')}` : t('common.save')}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* Working Hours Card */}
      {!loading && me && (
        <div className="card" style={{ maxWidth: 900, marginTop: 24 }}>
          <div className="card-header">
            <h2>{t('profile.workingHours')}</h2>
          </div>
          <div className="card-body">
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '0 0 16px' }}>{t('profile.workingHoursDesc')}</p>

            {hours.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: 12 }}>{t('profile.noHoursSet')}</p>
                <button type="button" className="btn btn-primary btn-sm" onClick={handleSetDefaultHours}>
                  {t('profile.setDefaultHours')}
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {hours.map((day) => (
                    <div
                      key={day.day_of_week}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '8px 12px',
                        borderRadius: 8,
                        background: day.is_closed ? '#fef2f2' : '#f0fdf4',
                        border: `1px solid ${day.is_closed ? '#fecaca' : '#bbf7d0'}`,
                      }}
                    >
                      <span style={{ width: 100, fontWeight: 600, fontSize: 14 }}>
                        {t(`profile.${DAY_KEYS[day.day_of_week]}`)}
                      </span>

                      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={day.is_closed}
                          onChange={(e) => updateDay(day.day_of_week, { is_closed: e.target.checked })}
                        />
                        {t('profile.closed')}
                      </label>

                      {!day.is_closed && (
                        <>
                          <input
                            type="time"
                            value={day.open_time}
                            onChange={(e) => updateDay(day.day_of_week, { open_time: e.target.value })}
                            style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
                          />
                          <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{t('profile.to')}</span>
                          <input
                            type="time"
                            value={day.close_time}
                            onChange={(e) => updateDay(day.day_of_week, { close_time: e.target.value })}
                            style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
                          />
                        </>
                      )}
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={handleSetDefaultHours}>
                    {t('profile.setDefaultHours')}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={hoursSaving}
                    onClick={() => void handleSaveHours()}
                  >
                    {hoursSaving ? t('common.loading') : t('common.save')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
