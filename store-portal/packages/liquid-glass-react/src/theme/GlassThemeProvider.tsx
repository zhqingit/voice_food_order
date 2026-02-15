import * as React from 'react';

export type GlassThemeName =
  | 'light'
  | 'dark'
  | 'ocean'
  | 'sunset'
  | 'forest'
  | 'contrast';

export type GlassThemeProviderProps = {
  theme: GlassThemeName;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
};

export function GlassThemeProvider(props: GlassThemeProviderProps) {
  const { theme, children, className, style } = props;
  return (
    <div data-glass-theme={theme} className={className} style={style}>
      {children}
    </div>
  );
}

export function setGlassTheme(el: HTMLElement, theme: GlassThemeName) {
  el.setAttribute('data-glass-theme', theme);
}
