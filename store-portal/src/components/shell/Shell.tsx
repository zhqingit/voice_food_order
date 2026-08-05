import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { logout } from '../../auth/authApi'
import { setAccessToken } from '../../auth/tokenStore'
import { getMe } from '../../api/storeApi'
import type { StoreMe } from '../../api/storeApi'
import type { TFunction } from 'i18next'
import { changeLanguage, SUPPORTED_LANGUAGES } from '../../i18n'

const navKeys = [
  { to: '/menu', labelKey: 'nav.menu', icon: menuIcon },
  { to: '/orders', labelKey: 'nav.orders', icon: ordersIcon },
  { to: '/ai', labelKey: 'nav.ai', icon: aiIcon },
  { to: '/profile', labelKey: 'nav.profile', icon: profileIcon },
]

const MIN_WIDTH = 180
const MAX_WIDTH = 480
const DEFAULT_WIDTH = 240

export function Shell({ children }: { children: React.ReactNode }): React.JSX.Element {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [storeName, setStoreName] = useState<string>(t('auth.title'))
  const [me, setMe] = useState<StoreMe | null>(null)
  const [copied, setCopied] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebar-width')
    return saved ? Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Number(saved))) : DEFAULT_WIDTH
  })
  const dragging = React.useRef(false)

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!dragging.current) return
      const w = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX))
      setSidebarWidth(w)
    }
    function onMouseUp() {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      localStorage.setItem('sidebar-width', String(sidebarWidth))
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [sidebarWidth])

  useEffect(() => {
    void getMe()
      .then((data) => {
        setMe(data)
        setStoreId(data.id)
        if (data.name) setStoreName(data.name)
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
      <aside className="sidebar" style={{ width: sidebarWidth }}>
        <div className="sidebar-brand">
          <h1>
            <img src="/logo.png" alt="VoxEats" style={{ width: 28, height: 28, objectFit: 'contain', borderRadius: 6, verticalAlign: 'middle', marginRight: 8 }} />
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
              {copied ? t('common.copied') : `ID: ${storeId}`}
            </button>
          )}
          <button className="btn btn-secondary btn-sm" style={{ width: '100%' }} onClick={() => void handleLogout()}>
            {t('nav.logout')}
          </button>
        </div>
      </aside>

      <div
        className="sidebar-resize-handle"
        style={{ left: sidebarWidth - 2 }}
        onMouseDown={() => {
          dragging.current = true
          document.body.style.cursor = 'col-resize'
          document.body.style.userSelect = 'none'
        }}
      />
      <main className="main-content" style={{ marginLeft: sidebarWidth }}>
        <StoreStatusBanner me={me} t={t} />
        {children}
      </main>
    </div>
  )
}

// Highest-priority store status issue, shown as a banner on every page.
// Suspended (admin) > pending approval (admin) > unpublished (store's own toggle).
function StoreStatusBanner({ me, t }: { me: StoreMe | null; t: TFunction }): React.JSX.Element | null {
  if (!me) return null

  let tone: 'danger' | 'warning' | 'muted'
  let title: string
  let desc: string
  if (!me.is_active) {
    tone = 'danger'
    title = t('status.suspendedTitle')
    desc = t('status.suspendedDesc')
  } else if (!me.is_approved) {
    tone = 'warning'
    title = t('status.pendingTitle')
    desc = t('status.pendingDesc')
  } else if (!me.is_published) {
    tone = 'muted'
    title = t('status.unpublishedTitle')
    desc = t('status.unpublishedDesc')
  } else {
    return null
  }

  const palette = {
    danger: { bg: 'rgba(220,38,38,0.10)', border: 'rgba(220,38,38,0.35)', fg: '#b91c1c' },
    warning: { bg: 'rgba(217,119,6,0.10)', border: 'rgba(217,119,6,0.35)', fg: '#b45309' },
    muted: { bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.30)', fg: '#475569' },
  }[tone]

  return (
    <div
      role="status"
      style={{
        margin: '0 0 16px',
        padding: '12px 16px',
        borderRadius: 12,
        background: palette.bg,
        border: `1px solid ${palette.border}`,
      }}
    >
      <div style={{ fontWeight: 600, color: palette.fg }}>{title}</div>
      <div style={{ fontSize: 13, color: palette.fg, opacity: 0.85, marginTop: 2 }}>{desc}</div>
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

function aiIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="M4.93 4.93l1.41 1.41" />
      <path d="M17.66 17.66l1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="M4.93 19.07l1.41-1.41" />
      <path d="M17.66 6.34l1.41-1.41" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  )
}
