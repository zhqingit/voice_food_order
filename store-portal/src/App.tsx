import React, { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import axios from 'axios'
import { GlassButton, GlassCard, type GlassThemeName } from '@zhqingit/liquid-glass-react'

import { getAccessToken } from './auth/tokenStore'
import { getMe, login, logout, refresh, signup } from './auth/authApi'
import { Shell } from './components/shell/Shell'
import { MenuRoute } from './routes/MenuRoute'
import { OrdersRoute } from './routes/OrdersRoute'
import { ProfileRoute } from './routes/ProfileRoute'
import { STORE_PORTAL_THEMES, useTheme } from './app/ThemeProvider'

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
      <div style={{ padding: 32, textAlign: 'center', opacity: 0.8 }}>
        Booting store-portal…
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
    <AuthPage
      onAuthed={() => {
        setToken(getAccessToken())
      }}
    />
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
  const { theme, setTheme } = useTheme()

  useEffect(() => {
    setError(null)
    setMessage(null)
  }, [mode])

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
          await signup({
            email: demoEmail,
            password: demoPassword,
            name: demoName,
          })
        } catch {
          await login(demoEmail, demoPassword)
        }
      }

      try {
        await getMe()
      } catch {
        // ignore
      }

      setMessage('Signed in with demo account.')
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        const detail = typeof data?.detail === 'string' ? data.detail : null
        const code = typeof data?.code === 'string' ? data.code : null
        setError(detail ?? code ?? 'Demo sign-in failed')
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
      try {
        await getMe()
      } catch {
        // ignore
      }
      setMessage('Login succeeded.')
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        const detail = typeof data?.detail === 'string' ? data.detail : null
        const code = typeof data?.code === 'string' ? data.code : null
        setError(detail ?? code ?? 'Login failed')
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
      await signup({
        email,
        password,
        name,
        phone: phone.trim() ? phone.trim() : undefined,
      })
      setMessage('Signup succeeded.')
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        const detail = typeof data?.detail === 'string' ? data.detail : null
        const code = typeof data?.code === 'string' ? data.code : null
        setError(detail ?? code ?? 'Signup failed')
      } else {
        setError('Signup failed')
      }
    }
  }

  async function handleClearSession(): Promise<void> {
    setError(null)
    setMessage(null)
    try {
      await logout()
      setMessage('Session cleared.')
    } catch {
      setError('Failed to clear session')
    }
  }

  return (
    <div style={{ minHeight: '100vh', padding: 20 }}>
      <div className="luxlunch-wrap">
        <GlassCard preset="crystal" className="luxlunch-stage" style={{ padding: 0, width: '100%' }}>
          <div className="luxlunch-bg" />

          <div className="luxlunch-content">
            <div className="luxlunch-nav">
              <div className="luxlunch-brand">
                <span className="luxlunch-dot" aria-hidden />
                <span>Store Portal</span>
              </div>
              <div className="luxlunch-links" aria-label="Auth mode">
                <a
                  href="#"
                  className={mode === 'login' ? 'luxlunch-active' : undefined}
                  onClick={(e) => {
                    e.preventDefault()
                    setMode('login')
                  }}
                >
                  Login
                </a>
                <a
                  href="#"
                  className={mode === 'signup' ? 'luxlunch-active' : undefined}
                  onClick={(e) => {
                    e.preventDefault()
                    setMode('signup')
                  }}
                >
                  Sign up
                </a>
              </div>
              <div className="luxlunch-cta">
                <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ opacity: 0.75, fontSize: 12 }}>Theme</span>
                  <select
                    value={theme}
                    onChange={(e) => setTheme(e.target.value as GlassThemeName)}
                  >
                    {STORE_PORTAL_THEMES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <GlassButton
                  preset="subtle"
                  style={{ padding: '6px 10px' }}
                  onClick={() => void handleClearSession()}
                >
                  Clear session
                </GlassButton>
              </div>
            </div>

            <div className="luxlunch-auth-center">
              <GlassCard preset="frosted" style={{ width: 460, maxWidth: '100%', padding: 18 }}>

                {import.meta.env.DEV ? (
                  <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                    <GlassButton
                      type="button"
                      preset="subtle"
                      className="luxlunch-primary"
                      style={{ padding: '8px 12px' }}
                      onClick={() => void handleDemoAccount()}
                      disabled={busy}
                    >
                      {busy ? 'Signing in…' : 'Use demo account'}
                    </GlassButton>
                    <div style={{ fontSize: 12, opacity: 0.75, alignSelf: 'center' }}>
                      DEV-only: auto-creates/logs in demo@store.local
                    </div>
                  </div>
                ) : null}

        {mode === 'login' ? (
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
            <label style={labelStyle}>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </label>
            <GlassButton type="submit" className="luxlunch-primary" style={{ padding: '10px 14px' }}>
              Login
            </GlassButton>
          </form>
        ) : (
          <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
            <label style={labelStyle}>
              Store name
              <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Phone (optional)
              <input value={phone} onChange={(e) => setPhone(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </label>
            <GlassButton type="submit" className="luxlunch-primary" style={{ padding: '10px 14px' }}>
              Create account
            </GlassButton>
          </form>
        )}

                {message ? <p style={{ color: 'lightgreen', marginTop: 12 }}>{message}</p> : null}
                {error ? <p style={{ color: 'crimson', marginTop: 12 }}>{error}</p> : null}
              </GlassCard>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.16)',
  background: 'rgba(255,255,255,0.08)',
  color: 'rgba(255, 255, 255, 0.92)',
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  fontSize: 13,
  opacity: 0.95,
}
