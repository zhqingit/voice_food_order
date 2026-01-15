import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from './auth/tokenStore'
import { getMe, login, logout, refresh, signup, type StoreMe } from './auth/authApi'

export function App(): React.JSX.Element {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [token, setToken] = useState<string | null>(getAccessToken())
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [me, setMe] = useState<StoreMe | null>(null)

  useEffect(() => {
    const id = window.setInterval(() => {
      setToken(getAccessToken())
    }, 250)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (!token) {
      setMe(null)
      return
    }
    void (async () => {
      try {
        const result = await getMe()
        setMe(result)
      } catch {
        // Ignore: user might be authenticated but backend unreachable.
      }
    })()
  }, [token])

  async function handleLogin(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    setError(null)
    setMessage(null)
    try {
      await login(email, password)
      setToken(getAccessToken())
      setMessage('Login succeeded.')
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
      setToken(getAccessToken())
      setMessage('Signup succeeded.')
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

  async function handleRefresh(): Promise<void> {
    setError(null)
    setMessage(null)
    try {
      await refresh()
      setToken(getAccessToken())
      const result = await getMe()
      setMe(result)
      setMessage('Refresh succeeded.')
    } catch {
      setError('Refresh failed')
    }
  }

  async function handleLogout(): Promise<void> {
    setError(null)
    setMessage(null)
    try {
      await logout()
      setToken(getAccessToken())
      setMe(null)
      setMessage('Logged out.')
    } catch {
      setError('Logout failed')
    }
  }

  async function handleLoadMe(): Promise<void> {
    setError(null)
    setMessage(null)
    try {
      const result = await getMe()
      setMe(result)
      setMessage('Loaded /store/me successfully.')
    } catch {
      setError('Failed to load /store/me')
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>store-portal</h1>

      {token ? (
        <>
          <h2>Test page</h2>
          <p>Authenticated (access token in memory; refresh via httpOnly cookie).</p>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={handleRefresh}>Refresh</button>
            <button onClick={handleLoadMe}>Load /store/me</button>
            <button onClick={handleLogout}>Logout</button>
          </div>

          <div style={{ marginTop: 12 }}>
            <p style={{ marginBottom: 6 }}>Signup/login proof:</p>
            {me ? (
              <pre style={{ padding: 12, background: '#f6f6f6', overflowX: 'auto' }}>
                {JSON.stringify(me, null, 2)}
              </pre>
            ) : (
              <p style={{ color: '#555' }}>
                Not loaded yet. Click “Load /store/me” to confirm.
              </p>
            )}
          </div>
        </>
      ) : (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button
              type="button"
              onClick={() => {
                setMode('login')
                setError(null)
              }}
              disabled={mode === 'login'}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('signup')
                setError(null)
              }}
              disabled={mode === 'signup'}
            >
              Sign up
            </button>
          </div>

          {mode === 'login' ? (
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <label>
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </label>
              <button type="submit">Login</button>
            </form>
          ) : (
            <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <label>
                Store name
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label>
                Phone (optional)
                <input value={phone} onChange={(e) => setPhone(e.target.value)} />
              </label>
              <label>
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </label>
              <button type="submit">Create account</button>
            </form>
          )}
        </>
      )}

      {message ? <p style={{ color: 'green' }}>{message}</p> : null}
      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}
    </div>
  )
}
