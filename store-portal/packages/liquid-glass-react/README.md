# @liquid-glass/react

Liquid glass UI primitives for React.

## Install
```bash
pnpm add @liquid-glass/react
```

## Usage
```tsx
import { GlassSurface, GlassThemeProvider } from '@liquid-glass/react';
import '@liquid-glass/react/styles.css';

export function Example() {
  return (
    <GlassThemeProvider theme="dark">
      <GlassSurface preset="frosted" interactive style={{ padding: 24 }}>
        Hello glass
      </GlassSurface>
    </GlassThemeProvider>
  );
}
```

## Themes
Theme switching is attribute-based: set `data-glass-theme` on any container, or use `GlassThemeProvider`.

Built-in themes: `light`, `dark`, `ocean`, `sunset`, `forest`, `contrast`.

## Presets
Built-in presets on `GlassSurface`: `subtle`, `frosted`, `crystal`, `vibrant`, `contrast`.

## Playground (workspace)
If you’re using the monorepo in this repo:
```bash
pnpm dev
```
