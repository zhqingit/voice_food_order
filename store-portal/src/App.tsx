import React, { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import axios from 'axios'

import { getAccessToken } from './auth/tokenStore'
import { getMe, login, logout, refresh, signup } from './auth/authApi'
import { addItemToMenu, createMenu, createStoreItem, listMenuItems, listMenus, listStoreItems } from './api/menuApi'
import { Shell } from './components/shell/Shell'
import { MenuRoute } from './routes/MenuRoute'
import { OrdersRoute } from './routes/OrdersRoute'
import { ProfileRoute } from './routes/ProfileRoute'

export function App(): React.JSX.Element {
  const [bootstrapped, setBootstrapped] = useState(false)
  const [token, setToken] = useState<string | null>(getAccessToken())

  useEffect(() => {
    void (async () => {
      try {
        if (!getAccessToken()) {
          await refresh()
        }
      } catch {
        // ignore
      } finally {
        setToken(getAccessToken())
        setBootstrapped(true)
      }
    })()
  }, [])

  if (!bootstrapped) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: '#6b7280' }}>
        Loading...
      </div>
    )
  }

  return token ? (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Navigate to="/menu" replace />} />
          <Route path="/menu" element={<MenuRoute />} />
          <Route path="/orders" element={<OrdersRoute />} />
          <Route path="/profile" element={<ProfileRoute />} />
          <Route path="*" element={<Navigate to="/menu" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  ) : (
    <AuthPage onAuthed={() => setToken(getAccessToken())} />
  )
}

function AuthPage({ onAuthed }: { onAuthed: () => void }): React.JSX.Element {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setError(null)
    setMessage(null)
  }, [mode])

  async function seedDemoData(): Promise<void> {
    const menus = await listMenus()
    let menu = menus[0]
    if (!menu) {
      menu = await createMenu({ name: 'Lunch Menu', active: true })
    }
    let poolItems = await listStoreItems()
    if (poolItems.length === 0) {
      const demoItems = [
        { name: 'Classic Burger', price: 12.99, description: 'Juicy beef patty, lettuce, tomato' },
        { name: 'Pepperoni Pizza', price: 18.99, description: 'Hand-tossed with house-made marinara' },
        { name: 'Caesar Salad', price: 10.99, description: 'Romaine, parmesan, croutons' },
        { name: 'Crispy Fries', price: 4.99, description: 'Golden fries with sea salt' },
        { name: 'Sparkling Water', price: 2.99, description: 'Chilled sparkling mineral water' },
      ]
      poolItems = await Promise.all(
        demoItems.map((item) => createStoreItem({ ...item, availability: true })),
      )
    }
    const menuItems = await listMenuItems(menu.id)
    if (menuItems.length === 0) {
      await Promise.all(poolItems.map((item) => addItemToMenu(menu.id, item.id)))
    }
  }

  async function handleDemoAccount(): Promise<void> {
    if (!import.meta.env.DEV) return
    setError(null)
    setMessage(null)
    setBusy(true)

    const demoEmail = 'demo@store.local'
    const demoPassword = 'demo123456'
    const demoName = 'Demo Store'

    try {
      try {
        await login(demoEmail, demoPassword)
      } catch {
        try {
          await signup({ email: demoEmail, password: demoPassword, name: demoName })
        } catch {
          await login(demoEmail, demoPassword)
        }
      }
      try { await getMe() } catch {}
      try { await seedDemoData() } catch {}
      setMessage('Signed in with demo account.')
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        setError(data?.detail ?? data?.code ?? 'Demo sign-in failed')
      } else {
        setError('Demo sign-in failed')
      }
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!import.meta.env.DEV) return
    const flag = (import.meta.env.VITE_STORE_PORTAL_DEMO_AUTO_LOGIN ?? '').toLowerCase()
    if (flag === '1' || flag === 'true' || flag === 'yes') {
      void handleDemoAccount()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleLogin(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    setError(null)
    setMessage(null)
    try {
      await login(email, password)
      try { await getMe() } catch {}
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        setError(data?.detail ?? data?.code ?? 'Login failed')
      } else {
        setError('Login failed')
      }
    }
  }

  async function handleSignup(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    setError(null)
    setMessage(null)
    try {
      await signup({ email, password, name, phone: phone.trim() || undefined })
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        setError(data?.detail ?? data?.code ?? 'Signup failed')
      } else {
        setError('Signup failed')
      }
    }
  }

  async function handleClearSession(): Promise<void> {
    setError(null)
    try {
      await logout()
      setMessage('Session cleared.')
    } catch {
      setError('Failed to clear session')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div style={{ padding: '24px 20px 16px', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span className="sidebar-brand-dot" />
            <span style={{ fontSize: 18, fontWeight: 700 }}>Store Portal</span>
          </div>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: 13 }}>
            Manage your restaurant
          </p>
        </div>

        <div className="auth-tabs">
          <button className={`auth-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>
            Login
          </button>
          <button className={`auth-tab ${mode === 'signup' ? 'active' : ''}`} onClick={() => setMode('signup')}>
            Sign Up
          </button>
        </div>

        <form className="auth-form" onSubmit={mode === 'login' ? handleLogin : handleSignup}>
          {mode === 'signup' && (
            <>
              <div className="form-group">
                <label className="form-label">Store Name</label>
                <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone (optional)</label>
                <input className="form-input" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </>
          )}
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input className="form-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '10px 16px' }}>
            {mode === 'login' ? 'Login' : 'Create Account'}
          </button>

          {import.meta.env.DEV && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => void handleDemoAccount()} disabled={busy}>
                {busy ? 'Signing in...' : 'Demo Account'}
              </button>
              <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>DEV only</span>
            </div>
          )}
        </form>

        {message && <div className="alert alert-success" style={{ margin: '0 20px 16px' }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ margin: '0 20px 16px' }}>{error}</div>}

        <div style={{ padding: '0 20px 16px', textAlign: 'center' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleClearSession()}>
            Clear session
          </button>
        </div>
      </div>
    </div>
  )
}
