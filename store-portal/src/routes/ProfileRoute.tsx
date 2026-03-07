import React, { useEffect, useState } from 'react'
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
    <>
      <div className="page-header">
        <h1>Profile & Settings</h1>
        <p>Manage your store information and preferences.</p>
      </div>

      {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}
      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ maxWidth: 900 }}>
        <div className="card-header">
          <h2>Store Information</h2>
        </div>

        {loading && (
          <div className="card-body">
            <div className="empty-state" style={{ padding: '16px 0' }}>Loading...</div>
          </div>
        )}

        {me && (
          <form className="card-body" onSubmit={(e) => void handleSave(e)}>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Store Name</label>
                <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>

              <div className="form-group grid-full">
                <label className="form-label">Email (read-only)</label>
                <input className="form-input" value={me.email} readOnly style={{ opacity: 0.7 }} />
              </div>

              <div className="form-group grid-full">
                <label className="form-label">Address Line 1</label>
                <input className="form-input" value={address1} onChange={(e) => setAddress1(e.target.value)} />
              </div>
              <div className="form-group grid-full">
                <label className="form-label">Address Line 2</label>
                <input className="form-input" value={address2} onChange={(e) => setAddress2(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">City</label>
                <input className="form-input" value={city} onChange={(e) => setCity(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">State</label>
                <input className="form-input" value={state} onChange={(e) => setState(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Postal Code</label>
                <input className="form-input" value={postal} onChange={(e) => setPostal(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Country</label>
                <input className="form-input" value={country} onChange={(e) => setCountry(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Timezone</label>
                <input className="form-input" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Min Order Amount</label>
                <input className="form-input" value={minOrder} onChange={(e) => setMinOrder(e.target.value)} inputMode="decimal" placeholder="0.00" />
              </div>

              <div className="form-group">
                <label className="form-check">
                  <input type="checkbox" checked={allowPickup} onChange={(e) => setAllowPickup(e.target.checked)} />
                  Allow Pickup
                </label>
              </div>
              <div className="form-group">
                <label className="form-check">
                  <input type="checkbox" checked={allowDelivery} onChange={(e) => setAllowDelivery(e.target.checked)} />
                  Allow Delivery
                </label>
              </div>

              <div className="flex-end grid-full">
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </div>
          </form>
        )}
      </div>
    </>
  )
}
