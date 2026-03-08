import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { logout } from '../../auth/authApi'
import { setAccessToken } from '../../auth/tokenStore'
import { getMe } from '../../api/storeApi'
import { changeLanguage, SUPPORTED_LANGUAGES } from '../../i18n'

const navKeys = [
  { to: '/menu', labelKey: 'nav.menu', icon: menuIcon },
  { to: '/orders', labelKey: 'nav.orders', icon: ordersIcon },
  { to: '/profile', labelKey: 'nav.profile', icon: profileIcon },
]

export function Shell({ children }: { children: React.ReactNode }): React.JSX.Element {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [storeName, setStoreName] = useState<string>(t('auth.title'))
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    void getMe()
      .then((me) => {
        setStoreId(me.id)
        if (me.name) setStoreName(me.name)
      })
      .catch(() => {})
  }, [])

  function handleCopyId(): void {
    if (!storeId) return
    void navigator.clipboard.writeText(storeId).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  async function handleLogout(): Promise<void> {
    try { await logout() } finally {
      setAccessToken(null)
      window.location.assign('/')
    }
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>
            <span className="sidebar-brand-dot" />
            {storeName}
          </h1>
        </div>

        <nav className="sidebar-nav">
          {navKeys.map((item) => {
            const active = location.pathname.startsWith(item.to)
            return (
              <Link key={item.to} to={item.to} className={active ? 'active' : undefined}>
                {item.icon()}
                {t(item.labelKey)}
              </Link>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          {/* Language switcher */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                className={`btn btn-sm ${i18n.language === lang.code ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => changeLanguage(lang.code)}
                style={{ flex: 1, minWidth: 0 }}
              >
                {lang.label}
              </button>
            ))}
          </div>
          {storeId && (
            <button className="sidebar-store-id" onClick={handleCopyId} title="Click to copy store ID">
              {copied ? t('common.copied') : t('common.storeIdPrefix', { id: storeId.slice(0, 8) })}
            </button>
          )}
          <button className="btn btn-secondary btn-sm" style={{ width: '100%' }} onClick={() => void handleLogout()}>
            {t('nav.logout')}
          </button>
        </div>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  )
}

function menuIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M3 12h18M3 18h18" />
    </svg>
  )
}

function ordersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

function profileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M5.5 21a7.5 7.5 0 0 1 13 0" />
    </svg>
  )
}
