import React, { createContext, useContext } from 'react'
import {
  GlassThemeName,
  GlassThemeProvider,
} from '@zhqingit/liquid-glass-react'
import { useLocalStorageState } from './useLocalStorage'

type ThemeContextValue = {
  theme: GlassThemeName
  setTheme: (theme: GlassThemeName) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export const STORE_PORTAL_THEME_KEY = 'store-portal.glassTheme'

export const STORE_PORTAL_THEMES: GlassThemeName[] = [
  'dark',
  'light',
  'ocean',
  'sunset',
  'forest',
  'contrast',
]

export function ThemeProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [theme, setThemeRaw] = useLocalStorageState<GlassThemeName>(
    STORE_PORTAL_THEME_KEY,
    'dark',
    {
      serialize: (v) => v,
      deserialize: (raw) => raw as GlassThemeName,
    },
  )

  const setTheme = (next: GlassThemeName) => {
    setThemeRaw(next)
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <GlassThemeProvider theme={theme}>{children}</GlassThemeProvider>
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return ctx
}
