# Implementation roadmap (file-by-file)

## Scope
Build a production-grade AI voice food ordering system using only backend (FastAPI), store-portal (React), and user-portal (Flutter). No separate voice_agent folder; all voice/agent logic lives in backend, with UI in portals.

---

## Phase 0 — Baseline alignment
**Goal:** Establish shared configuration and ownership boundaries.

- backend/app/core/config.py
  - Add settings for voice pipeline (STT/TTS/LLM provider keys), websocket audio limits, and telephony provider credentials.
  - **Reason:** Centralize configuration to avoid inconsistent runtime behavior across services.
- README_run.md
  - Add run instructions for voice websocket + telephony callbacks (doc-only).
  - **Reason:** Make dev/test setup repeatable for the team.

---

## Phase 1 — Backend data model & API foundation
**Goal:** Persist menus, orders, and session state. Expose stable APIs for portals and voice pipeline.

### Phase 1.1 — Store profile extensions
- backend/app/models/store.py
  - Extend with address, timezone, and ordering rules (pickup/delivery, min order).
  - **Reason:** Voice and ordering flows require store constraints.
- backend/app/schemas/store/store.py
  - Extend StoreOut with address/timezone/ordering rules.
  - **Reason:** Store portal needs full profile data.
- backend/alembic/versions/xxxx_add_store_profile_fields.py (new)
  - Migration for new store columns.
  - **Reason:** Keep schema changes explicit and reversible.

### Phase 1.2 — Menu data model + CRUD
- backend/app/models/menu.py (new)
  - Menu: store_id, name, active, version, updated_at.
  - **Reason:** Versioned menus reduce race conditions and enable caching.
- backend/app/models/menu_item.py (new)
  - MenuItem: menu_id, name, price, description, tags, availability, modifiers JSON.
  - **Reason:** Tooling needs canonical IDs and pricing details.
- backend/app/schemas/menu/menu.py (new)
  - MenuOut, MenuItemOut, MenuCreate, MenuItemCreate/Update.
  - **Reason:** Standardize client/server payloads.
- backend/app/services/menu_service.py (new)
  - Fetch menu by store + version, resolve item IDs.
  - **Reason:** Single source of truth for menu logic.
- backend/app/api/routers/store/menu.py (new)
  - CRUD menus/items with store auth.
  - **Reason:** Store portal requires menu management.
- backend/alembic/versions/xxxx_add_menu_tables.py (new)
  - Menu + menu_item tables + indexes.
  - **Reason:** Schema migration for menu features.

### Phase 1.3 — Order data model + draft lifecycle
- backend/app/models/order.py (new)
  - Order: store_id, user_id (nullable), status, channel, totals, notes, created_at.
  - **Reason:** Persist drafts and finalized orders for both portals.
- backend/app/models/order_item.py (new)
  - OrderItem: order_id, menu_item_id, quantity, price_snapshot.
  - **Reason:** Snapshot pricing for audit and history.
- backend/app/schemas/order/order.py (new)
  - OrderOut, OrderCreate, OrderItemCreate, OrderStatusUpdate.
  - **Reason:** Clear contract for order lifecycle.
- backend/app/services/order_service.py (new)
  - Create draft order, add/remove items, recalc totals, finalize.
  - **Reason:** Keep business logic out of routers.
- backend/alembic/versions/xxxx_add_order_tables.py (new)
  - Order + order_item tables + indexes.
  - **Reason:** Schema migration for order tracking.

### Phase 1.4 — Voice session data model
- backend/app/models/voice_session.py (new)
  - VoiceSession: store_id, user_id, channel, status, started_at, ended_at.
  - **Reason:** Track call lifecycle and associate orders to sessions.
- backend/app/schemas/voice/voice.py (new)
  - VoiceSessionCreate, VoiceSessionOut, VoiceEventIn/Out.
  - **Reason:** Normalize events between voice pipeline and UI.
- backend/app/services/voice_session_service.py (new)
  - Manage session lifecycle, associate orders, emit events.
  - **Reason:** Stable orchestration for live calls.
- backend/alembic/versions/xxxx_add_voice_session_tables.py (new)
  - Voice session table + indexes.
  - **Reason:** Schema migration for call tracking.

### Phase 1.5 — API routers for portals + voice pipeline
- backend/app/api/routers/store/orders.py (new)
  - List/update order status.
  - **Reason:** Store portal needs order operations.
- backend/app/api/routers/user/orders.py (new)
  - Create/read orders for mobile user.
  - **Reason:** User portal needs order history.
- backend/app/api/routers/voice/sessions.py (new)
  - Create session, start/stop, websocket bootstrap.
  - **Reason:** Voice pipeline needs a session entry point.
- backend/app/api/routers/voice/orders.py (new)
  - Draft order tool endpoints: add/remove items, summary, finalize.
  - **Reason:** Tool calls must be server-authoritative.
- backend/app/main.py
  - Register new routers.
  - **Reason:** Ensure endpoints are reachable.

---

## Phase 2 — Backend voice pipeline (no separate service)
**Goal:** Implement voice orchestration inside backend (websocket + telephony).
**Note:** You may borrow implementation patterns from the legacy `voice_agent` folder, but that folder will be removed and must not be a runtime dependency.

### Phase 2.1 — Core pipeline scaffolding
- backend/app/voice/pipeline.py (new)
  - Build STT → LLM → tools → TTS chain using provider SDKs.
  - **Reason:** Centralized orchestration avoids duplicated logic.
- backend/app/voice/prompts.py (new)
  - System prompts, safety guidelines, and response style.
  - **Reason:** Consistent conversation behavior.
- backend/app/voice/config.py (new)
  - Provider selection, model mapping, and runtime knobs (read from settings).
  - **Reason:** Keep pipeline configuration explicit and testable.

### Phase 2.2 — Tooling layer (server-authoritative)
- backend/app/voice/tools.py (new)
  - Tool schemas + handlers that call menu/order services.
  - **Reason:** Enforce tool outputs from server-side state.
- backend/app/voice/tool_router.py (new)
  - Registry/dispatcher for tool calls and structured responses.
  - **Reason:** Keeps LLM tooling deterministic and auditable.

### Phase 2.3 — Websocket transport (user app)
- backend/app/voice/transports/websocket.py (new)
  - Audio input/output over websockets, VAD settings.
  - **Reason:** Supports user-portal voice UI.
- backend/app/api/routers/voice/ws.py (new)
  - Websocket endpoint for live audio stream.
  - **Reason:** Real-time audio channel to the pipeline.

### Phase 2.4 — Telephony transport (phone calls)
- backend/app/voice/transports/daily.py (new)
  - WebRTC bridge or telephony provider integration.
  - **Reason:** Phone call support is core to requirements.
- backend/app/api/routers/voice/telephony.py (new)
  - Webhooks to start/stop sessions and join a room.
  - **Reason:** Provider callbacks must be handled in backend.

### Phase 2.5 — Observability & safety hooks (voice-only)
- backend/app/voice/events.py (new)
  - Voice event types, logging hooks, and session correlation IDs.
  - **Reason:** Debugging and compliance for voice workflows.
- backend/app/voice/guards.py (new)
  - Rate limiting, max-duration enforcement, and content safety checks.
  - **Reason:** Prevent abuse and control costs early.

---

## Phase 3 — Store portal (web)
**Goal:** Menu management and order operations, built on the vendored liquid-glass UI primitives.

**UI foundation (already installed):** `@zhqingit/liquid-glass-react` vendored under `store-portal/packages/liquid-glass-react`.

- store-portal/src/main.tsx
  - Import `@zhqingit/liquid-glass-react/styles.css` globally.
  - Wrap the app with `GlassThemeProvider`.
  - **Reason:** Establish one consistent glass baseline and theme scope.
- Theme selection (user choice)
  - Provide a UI control in the Store portal (e.g., top-right menu) that lets the store user choose a theme.
  - Persist the selected theme in `localStorage`.
  - Apply the theme via `GlassThemeProvider` (or `data-glass-theme` attribute).
  - **Reason:** Store users can pick a theme (light/dark/etc.) without code changes.

### Phase 3.1 — API client foundations
- store-portal/src/api/client.ts
  - Add typed helpers for menu/order endpoints.
  - **Reason:** Keep API calls consistent and retryable.
- store-portal/src/api/menuApi.ts (new)
  - list/create/update menu items.
  - **Reason:** Separation of concerns.
- store-portal/src/api/orderApi.ts (new)
  - fetch orders, update status.
  - **Reason:** Encapsulate order operations.

### Phase 3.2 — App shell and routing
- store-portal/src/App.tsx
  - Replace auth test page with routes: Menu, Orders, Profile.
  - **Reason:** Turn demo into real workflow.
- store-portal/src/routes/* (new)
  - Route config, layout shell, and navigation.
  - **Reason:** Shared layout and navigation across screens.
- store-portal/src/components/shell/* (new)
  - Glass-based layout primitives (header/sidebar/surface wrappers) using `GlassSurface` / `GlassButton`.
  - Include theme switcher control in the shell.
  - **Reason:** Centralize navigation + theme selection once.

### Phase 3.3 — Menu management UI
- store-portal/src/menu/* (new)
  - Menu list, item editor, availability toggles.
  - **Reason:** Store-facing menu control.

### Phase 3.4 — Order operations UI
- store-portal/src/orders/* (new)
  - Live order list, status updates, details.
  - **Reason:** Store fulfillment workflow.

### Phase 3.5 — Profile & settings UI
- store-portal/src/profile/* (new)
  - Store profile editor (address, rules, contact).
  - **Reason:** Keep store data accurate for voice ordering.

---

## Phase 4 — User portal (Flutter)
**Goal:** Voice session UI + order summary.

**UI direction:** Build liquid-glass UI in Flutter (not React).

- Use `liquid_glass_flutter` (already added to `pubspec.yaml`) as the rendering/effect layer where appropriate.
- Build a small, token-driven glass design system on top (consistent blur/tint/noise/radius/shadow) so the app is cohesive and easy to theme.
- Visual baseline: match the LuxLunch theme from `liquid_glass_react/apps/playground` (gradients, accent orange, stage background treatment) and translate it into Flutter tokens.

**Localization requirement:** User portal supports multiple languages end-to-end with a user-selectable language.

- Supported locales (for now): `en`, `zh`.
- Default language: `en`.
- Users can change language in Settings; selection is persisted.

### Phase 4.1 — App foundations (Flutter)
- user-portal/pubspec.yaml
  - Add dependencies for localization (`flutter_localizations`, `intl`) and networking (existing choice: `dio` or `http`).
  - **Reason:** Enable i18n and stable API calls.
- user-portal/lib/core/config/* (new)
  - Configure API base URLs for user portal (dev default should match backend host policy, e.g. `http://user-api.local:8000`).
  - **Reason:** Avoid `invalid_host` issues and centralize env config.
- user-portal/lib/core/routing/* (new or adapt existing)
  - Define navigation structure: Stores → Voice Order → Order Confirmation/History → Settings.
  - **Reason:** Keep navigation predictable and testable.

### Phase 4.2 — Localization (multi-language)
- user-portal/l10n/app_en.arb (new)
- user-portal/l10n/app_zh.arb (new)
- user-portal/lib/core/l10n/* (new)
  - Enable Flutter gen-l10n, define locale resolution + fallback (default `en`), and expose `AppLocalizations` helpers.
  - **Reason:** Real multi-language support, not hardcoded strings.
- user-portal/lib/features/settings/language_settings.dart (new)
  - Language selector UI (dropdown/list), persisted (e.g., `shared_preferences`).
  - **Reason:** Users can switch language without rebuilding.
- RTL readiness
  - Ensure layouts don’t break under RTL locales and large text scale.
  - **Reason:** Internationalization quality bar.

### Phase 4.3 — Liquid-glass UI system (Flutter)
- user-portal/lib/ui/glass/* (new)
  - Core primitives: `GlassSurface`, `GlassCard`, `GlassButton`, `GlassScaffold`.
  - Implementation:
    - Prefer `liquid_glass_flutter` for the “liquid glass” effect on hero/stage surfaces.
    - Use `BackdropFilter` / `ImageFilter.blur` + gradient tint overlays + subtle noise overlay for standard surfaces.
    - Keep consistent radii, borders, shadows, and spacing.
  - **Reason:** Reusable glass look across all screens.
- user-portal/lib/ui/theme/* (new)
  - Token sets for themes (start with `luxlunch` + a small set like `dark`), and a theme switcher persisted in settings.
  - LuxLunch theme guidance: mirror accent orange, stage background glows, and typography feel from `liquid_glass_react/apps/playground`.
  - **Reason:** Match the LuxLunch direction and allow user preference.
- user-portal/lib/features/settings/appearance_settings.dart (new)
  - Theme selector UI + persistence.
  - **Reason:** Let users choose theme without rebuild.

### Phase 4.4 — Data layer & repositories
- user-portal/lib/data/menu_repository.dart (new)
  - Fetch store list + menus.
  - **Reason:** Show real store data.
- user-portal/lib/data/order_repository.dart (new)
  - Create draft order, apply changes, finalize.
  - **Reason:** Keep UI thin, logic centralized.
- user-portal/lib/data/voice_session_repository.dart (new)
  - Start/end session, connect websocket.
  - **Reason:** Isolate voice session management.
- user-portal/lib/data/auth/* (optional)
  - If user auth is required for history, add login/refresh flow consistent with backend.
  - **Reason:** Enable persisted order history per user.

### Phase 4.5 — Stores & selection UI
- user-portal/lib/features/store/stores_screen.dart
  - Populate store list from API; allow selecting a store.
  - **Reason:** Replace hardcoded store.
- user-portal/lib/features/store/store_details_screen.dart (optional)
  - Show store profile basics (hours/address rules) using glass cards.
  - **Reason:** Improves trust and reduces ordering errors.

### Phase 4.6 — Voice ordering UI (core)
- user-portal/lib/features/voice/voice_order_screen.dart
  - Live voice session UI: mic controls, connection state, transcript preview.
  - Order summary panel: items, totals, and status (draft/finalized).
  - **Reason:** Core voice UX.
- Audio/Websocket integration
  - Websocket connect to backend voice endpoint; stream microphone audio; play TTS audio.
  - **Reason:** End-to-end voice loop in-app.

### Phase 4.7 — Orders: confirmation & history
- user-portal/lib/features/order/confirm_screen.dart (new)
  - Show final order summary + success state.
  - **Reason:** Clear end-state after voice.
- user-portal/lib/features/order/history_screen.dart (new)
  - List past orders, details, and status.
  - **Reason:** Users need visibility after order.

### Phase 4.8 — Polish & QA gates (Flutter)
- Accessibility
  - Verify contrast in glass surfaces, focus states, large text scale.
  - **Reason:** Usability on real devices.
- Localization QA
  - Verify all strings are localized and no overflows in supported locales.
  - **Reason:** Multi-language requirement.

---

## Phase 5 — Reliability, security, and observability
**Goal:** Production hardening and safe operation.

- backend/app/core/security.py
  - Service-to-service auth for voice websocket/telephony endpoints.
  - **Reason:** Prevent unauthorized session creation.
- backend/app/core/logging.py (new)
  - Structured logging, correlation IDs.
  - **Reason:** Debug voice sessions and order flows.
- backend/app/core/rate_limits.py (new)
  - Per-store/session limits for LLM/STT usage.
  - **Reason:** Cost and abuse control.
- backend/tests/*
  - Add tests for menu/order/voice endpoints.
  - **Reason:** Protect critical ordering flows.

---

## Deliverables checklist
- DB migrations for menus, orders, and voice sessions.
- Voice pipeline integrated into backend with websocket + telephony endpoints.
- Store portal manages menus and order status.
- User portal supports voice ordering and summary/confirmation.
- Logging, security, and rate limits in place.
