## Liquid Glass UI Package Plan
**Goal:** Build a reusable, independent React UI package that delivers the “liquid glass” aesthetic with the warm neutral palette (beige/greige base, sage/olive accents, orange highlights), and can be reused across projects.

### Design constraints
- No runtime dependency on the referenced repos; only borrow ideas.
- Theme tokens must be customizable but ship with a default palette matching the attachment.
- Accessibility: maintain readable contrast; provide reduced‑motion and low‑blur options.

---

## Phase 0 — Product definition
**Deliverables:**
- Component inventory: `GlassSurface`, `GlassCard`, `GlassButton`, `GlassInput`, `GlassBadge`, `GlassNav`, `GlassTabs`.
- Token list: `glass.blur`, `glass.opacity`, `glass.border`, `glass.shadow`, `accent.orange`, `accent.sage`, `neutral.base`, `neutral.text`.
- API decisions: CSS variables for theming + React props for per‑component overrides.

---

## Phase 1 — Package scaffolding
**Deliverables:**
- New package workspace (e.g., `packages/liquid-glass-ui`).
- Build setup with TS + bundler (Vite/Rollup) + CSS output.
- Storybook/demo for visual testing.

---

## Phase 2 — Core primitives
**Deliverables:**
- `GlassProvider` for theme tokens and motion preferences.
- `GlassSurface` base component (blur, saturation, highlight, border).
- `GlassLayer` utility for background gradients and noise overlay.

---

## Phase 3 — Interactive components
**Deliverables:**
- `GlassButton` and `GlassInput` with focus/hover states.
- `GlassCard` with title/subtitle slots.
- `GlassBadge` and `GlassTabs`.

---

## Phase 4 — Motion + polish
**Deliverables:**
- Optional “liquid” hover shift effect (reduced‑motion friendly).
- Edge highlights and soft glow tuned to the warm palette.
- Dark/light surface variants.

---

## Phase 5 — Integration into store-portal
**Deliverables:**
- Replace current portal UI with liquid glass components.
- Layout inspired by the attachment: wide glass hero panel, warm CTA, subtle sage accents.
- Ensure theme tokens shared across portal pages.

---

## Phase 6 — Documentation
**Deliverables:**
- README with usage examples and theme customization.
- Token reference table + best practices (contrast, blur limits, motion).
