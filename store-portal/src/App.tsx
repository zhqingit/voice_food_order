import React, { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'

import { getAccessToken } from './auth/tokenStore'
import { getMe, login, logout, refresh, signup } from './auth/authApi'
import { addItemToMenu, createMenu, createStoreItem, listMenuItems, listMenus, listStoreItems } from './api/menuApi'
import { Shell } from './components/shell/Shell'
import { MenuRoute } from './routes/MenuRoute'
import { OrdersRoute } from './routes/OrdersRoute'
import { ProfileRoute } from './routes/ProfileRoute'
import { AIRoute } from './routes/AIRoute'
import { changeLanguage, SUPPORTED_LANGUAGES } from './i18n'

export function App(): React.JSX.Element {
  const { t } = useTranslation()
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
        {t('common.loading')}
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
          <Route path="/ai" element={<AIRoute />} />
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
  const { t, i18n } = useTranslation()
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
      setMessage(t('auth.signedInDemo'))
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        setError(data?.detail ?? data?.code ?? t('auth.demoSignInFailed'))
      } else {
        setError(t('auth.demoSignInFailed'))
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
        setError(data?.detail ?? data?.code ?? t('auth.loginFailed'))
      } else {
        setError(t('auth.loginFailed'))
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
        setError(data?.detail ?? data?.code ?? t('auth.signupFailed'))
      } else {
        setError(t('auth.signupFailed'))
      }
    }
  }

  async function handleClearSession(): Promise<void> {
    setError(null)
    try {
      await logout()
      setMessage(t('auth.sessionCleared'))
    } catch {
      setError(t('auth.clearSessionFailed'))
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div style={{ padding: '24px 20px 16px', textAlign: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <img src="/logo.png" alt="VoxEats" style={{ width: 96, height: 96, objectFit: 'contain' }} />
            <span style={{ fontSize: 18, fontWeight: 700 }}>{t('auth.title')}</span>
          </div>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: 13 }}>
            {t('auth.subtitle')}
          </p>
        </div>

        {/* Language switcher */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 4, marginBottom: 8 }}>
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              className={`btn btn-sm ${i18n.language === lang.code ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => changeLanguage(lang.code)}
              style={{ minWidth: 44 }}
            >
              {lang.label}
            </button>
          ))}
        </div>

        <div className="auth-tabs">
          <button className={`auth-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>
            {t('auth.login')}
          </button>
          <button className={`auth-tab ${mode === 'signup' ? 'active' : ''}`} onClick={() => setMode('signup')}>
            {t('auth.signup')}
          </button>
        </div>

        <form className="auth-form" onSubmit={mode === 'login' ? handleLogin : handleSignup}>
          {mode === 'signup' && (
            <>
              <div className="form-group">
                <label className="form-label">{t('auth.storeName')}</label>
                <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('auth.phone')}</label>
                <input className="form-input" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </>
          )}
          <div className="form-group">
            <label className="form-label">{t('auth.email')}</label>
            <input className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">{t('auth.password')}</label>
            <input className="form-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '10px 16px' }}>
            {mode === 'login' ? t('auth.login') : t('auth.createAccount')}
          </button>

          {import.meta.env.DEV && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => void handleDemoAccount()} disabled={busy}>
                {busy ? t('auth.signingIn') : t('auth.demoAccount')}
              </button>
              <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{t('auth.devOnly')}</span>
            </div>
          )}
        </form>

        {message && <div className="alert alert-success" style={{ margin: '0 20px 16px' }}>{message}</div>}
        {error && <div className="alert alert-error" style={{ margin: '0 20px 16px' }}>{error}</div>}

        <div style={{ padding: '0 20px 16px', textAlign: 'center' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => void handleClearSession()}>
            {t('auth.clearSession')}
          </button>
        </div>
      </div>
    </div>
  )
}
