import React, { useEffect, useState } from 'react'
import { GlassButton, GlassCard } from '@zhqingit/liquid-glass-react'
import { getMe, updateMe, type StoreMe } from '../api/storeApi'

export function ProfileRoute(): React.JSX.Element {
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

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getMe()
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
      } catch {
        setError('Failed to load profile')
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
      setError('Min order amount must be a non-negative number')
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
      })
      setMe(updated)
      setMessage('Saved.')
    } catch {
      setError('Failed to save profile')
    }
  }

  return (
    <GlassCard preset="frosted" style={{ padding: 16, maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ marginTop: 0 }}>Profile & Settings</h2>

      {loading ? <div style={{ opacity: 0.75 }}>Loading…</div> : null}

      {me ? (
        <form onSubmit={handleSave} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <label style={labelStyle}>
            Store name
            <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            Phone
            <input value={phone} onChange={(e) => setPhone(e.target.value)} style={inputStyle} />
          </label>

          <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
            Email (read-only)
            <input value={me.email} readOnly style={{ ...inputStyle, opacity: 0.8 }} />
          </label>

          <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
            Address line 1
            <input value={address1} onChange={(e) => setAddress1(e.target.value)} style={inputStyle} />
          </label>
          <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
            Address line 2
            <input value={address2} onChange={(e) => setAddress2(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            City
            <input value={city} onChange={(e) => setCity(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            State
            <input value={state} onChange={(e) => setState(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            Postal code
            <input value={postal} onChange={(e) => setPostal(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            Country
            <input value={country} onChange={(e) => setCountry(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            Timezone
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            Min order amount
            <input value={minOrder} onChange={(e) => setMinOrder(e.target.value)} style={inputStyle} inputMode="decimal" />
          </label>

          <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={allowPickup} onChange={(e) => setAllowPickup(e.target.checked)} />
            Allow pickup
          </label>
          <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={allowDelivery} onChange={(e) => setAllowDelivery(e.target.checked)} />
            Allow delivery
          </label>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <GlassButton type="submit" style={{ padding: '10px 14px', fontWeight: 800 }}>
              Save
            </GlassButton>
          </div>
        </form>
      ) : null}

      {message ? <div style={{ marginTop: 12, color: 'green' }}>{message}</div> : null}
      {error ? <div style={{ marginTop: 12, color: 'crimson' }}>{error}</div> : null}
    </GlassCard>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.22)',
  background: 'rgba(255,255,255,0.08)',
  color: 'inherit',
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  fontSize: 13,
  opacity: 0.95,
}
