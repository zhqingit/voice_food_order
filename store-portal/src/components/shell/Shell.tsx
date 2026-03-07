import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { logout } from '../../auth/authApi'
import { setAccessToken } from '../../auth/tokenStore'
import { getMe } from '../../api/storeApi'

const navItems = [
  { to: '/menu', label: 'Menu', icon: menuIcon },
  { to: '/orders', label: 'Orders', icon: ordersIcon },
  { to: '/profile', label: 'Profile', icon: profileIcon },
]

export function Shell({ children }: { children: React.ReactNode }): React.JSX.Element {
  const location = useLocation()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [storeName, setStoreName] = useState<string>('Store Portal')
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
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.to)
            return (
              <Link key={item.to} to={item.to} className={active ? 'active' : undefined}>
                {item.icon()}
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          {storeId && (
            <button className="sidebar-store-id" onClick={handleCopyId} title="Click to copy store ID">
              {copied ? 'Copied!' : `ID: ${storeId.slice(0, 8)}...`}
            </button>
          )}
          <button className="btn btn-secondary btn-sm" style={{ width: '100%' }} onClick={() => void handleLogout()}>
            Logout
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
