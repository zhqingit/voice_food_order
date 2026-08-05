import React, { useEffect, useState } from 'react'
import axios from 'axios'

import { getAccessToken } from './auth/tokenStore'
import { login, logout, refresh } from './auth/authApi'
import { StoresRoute } from './routes/StoresRoute'

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
        // no existing session — show login
      } finally {
        setToken(getAccessToken())
        setBootstrapped(true)
      }
    })()
  }, [])

  async function handleLogout(): Promise<void> {
    await logout()
    setToken(null)
  }

  if (!bootstrapped) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: '#6b7280' }}>
        Loading…
      </div>
    )
  }

  if (!token) {
    return <LoginPage onAuthed={() => setToken(getAccessToken())} />
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 24px',
          borderBottom: '1px solid var(--color-border, #e5e7eb)',
          background: '#fff',
        }}
      >
        <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: 0.3 }}>
          VoxEats <span style={{ color: 'var(--color-primary, #2563eb)' }}>Admin</span>
        </span>
        <button className="btn btn-ghost btn-sm" onClick={() => void handleLogout()}>
          Logout
        </button>
      </header>
      <main style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <StoresRoute />
      </main>
    </div>
  )
}

function LoginPage({ onAuthed }: { onAuthed: () => void }): React.JSX.Element {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleLogin(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      onAuthed()
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as any
        setError(data?.detail ?? data?.code ?? 'Login failed')
      } else {
        setError('Login failed')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div style={{ padding: '28px 20px 8px', textAlign: 'center' }}>
          <span style={{ fontSize: 20, fontWeight: 800 }}>
            VoxEats <span style={{ color: 'var(--color-primary, #2563eb)' }}>Admin</span>
          </span>
          <p style={{ margin: '6px 0 0', color: 'var(--color-text-secondary)', fontSize: 13 }}>
            Platform operations
          </p>
        </div>

        <form className="auth-form" onSubmit={(e) => void handleLogin(e)}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '10px 16px' }} disabled={busy}>
            {busy ? 'Signing in…' : 'Login'}
          </button>
        </form>

        {error && <div className="alert alert-error" style={{ margin: '0 20px 20px' }}>{error}</div>}
      </div>
    </div>
  )
}
