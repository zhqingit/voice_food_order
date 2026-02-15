import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GlassButton, GlassSurface, type GlassThemeName } from '@zhqingit/liquid-glass-react'
import { logout } from '../../auth/authApi'
import { setAccessToken } from '../../auth/tokenStore'
import { STORE_PORTAL_THEMES, useTheme } from '../../app/ThemeProvider'

const navItems: Array<{ to: string; label: string }> = [
  { to: '/menu', label: 'Menu' },
  { to: '/orders', label: 'Orders' },
  { to: '/profile', label: 'Profile' },
]

export function Shell({ children }: { children: React.ReactNode }): React.JSX.Element {
  const location = useLocation()
  const { theme, setTheme } = useTheme()

  async function handleLogout(): Promise<void> {
    try {
      await logout()
    } finally {
      setAccessToken(null)
      window.location.assign('/')
    }
  }

  return (
    <div style={{ minHeight: '100vh', padding: 20 }}>
      <div className="luxlunch-wrap">
        <GlassSurface preset="crystal" className="luxlunch-stage" style={{ padding: 0 }}>
          <div className="luxlunch-bg" />

          <div className="luxlunch-content">
            <div className="luxlunch-nav">
              <div className="luxlunch-brand">
                <span className="luxlunch-dot" aria-hidden />
                <span>Store Portal</span>
              </div>

              <nav className="luxlunch-links" aria-label="Primary">
                {navItems.map((item) => {
                  const active = location.pathname.startsWith(item.to)
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      className={active ? 'luxlunch-active' : undefined}
                    >
                      {item.label}
                    </Link>
                  )
                })}
              </nav>

              <div className="luxlunch-cta">
                <GlassButton
                  preset="subtle"
                  className="luxlunch-primary"
                  onClick={handleLogout}
                  style={{ padding: '8px 12px' }}
                >
                  Logout
                </GlassButton>
              </div>
            </div>

            <div className="luxlunch-controls" aria-label="Controls">
              <label>
                <span style={{ opacity: 0.75, fontSize: 12 }}>Theme</span>
                <select value={theme} onChange={(e) => setTheme(e.target.value as GlassThemeName)}>
                  {STORE_PORTAL_THEMES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="luxlunch-main">{children}</div>
          </div>
        </GlassSurface>
      </div>
    </div>
  )
}
