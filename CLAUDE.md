# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered voice food ordering system with three components:
- **Backend** (`backend/`): FastAPI + PostgreSQL REST API with voice pipeline
- **Store Portal** (`store-portal/`): React (Vite + TypeScript) web app for store managers
- **User Portal** (`user-portal/`): Flutter mobile app for customers

## Development Commands

### Backend (FastAPI)

```bash
# Start with Docker (Postgres + API, auto-runs migrations)
cd backend && docker compose up --build
# Health check: http://localhost:8000/health

# Run without Docker
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload

# Database migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"

# Tests
cd backend && pytest -q
```

### Store Portal (React)

```bash
cd store-portal
cp .env.example .env
npm install
npm run dev      # Dev server (Vite proxies API to localhost:8000)
npm run build    # tsc -b && vite build
```

### User Portal (Flutter)

```bash
cd user-portal
flutter pub get
flutter run
flutter build apk   # Android release
flutter build ios    # iOS release
```

## Architecture

### Host-Based API Partitioning

The backend uses host headers to isolate portals — this is critical to understand:
- `user-api.local` → User portal endpoints (`/user/...`)
- `store-api.local` → Store portal endpoints (`/store/...`)

Configured in `backend/app/core/config.py`. The store-portal Vite dev server proxies and sets the `Host: store-api.local` header automatically. For manual testing with curl, add `-H 'Host: store-api.local'`.

### Authentication Model

Two separate auth flows sharing the same JWT infrastructure:
- **User (mobile)**: Refresh tokens sent as JSON body with `session_id`
- **Store (web)**: Refresh tokens stored in httpOnly cookies

JWT tokens include `role` (user/store) and `audience` (mobile/web) claims to prevent cross-portal token reuse. Refresh tokens are opaque, server-side stored, rotated on use with reuse detection. Core auth logic in `backend/app/core/security.py`.

### Voice Ordering Flow

1. User app creates a voice session (`POST /voice/sessions`)
2. WebSocket connects to `/voice/ws?store_id=X&order_id=Y` with bearer token
3. Audio frames (PCM16, 16kHz) stream over WebSocket
4. Backend runs Pipecat pipeline: Google STT → Gemini LLM → Google TTS
5. LLM has tools: `add_item`, `remove_item`, `get_summary`, `checkout`
6. Tool calls execute against order service (draft → submitted)
7. TTS audio returned to client for playback

Key voice files:
- `backend/app/voice/pipeline.py` — Pipecat orchestration
- `backend/app/voice/tool_router.py` — Tool dispatch to order service
- `backend/app/voice/tools.py` — Tool schemas for Gemini
- `backend/app/api/routers/voice/ws.py` — WebSocket endpoint
- `backend/app/api/routers/voice/telephony.py` — Daily.co phone integration

Telephony (phone calls) uses Daily.co WebRTC via `POST /voice/telephony/daily/start`.

### Database Schema

PostgreSQL with Alembic migrations in `backend/alembic/versions/`. Key relationships:
- `stores` → `menus` → `menu_items`
- `stores` → `orders` → `order_items` → `menu_items` (price snapshot)
- `users` → `orders`, `voice_sessions`
- `stores` → `voice_sessions`
- `refresh_sessions` → `refresh_tokens`

Orders use price snapshots in `order_items` to preserve pricing at time of order.

### Backend Structure

```
backend/app/
├── api/routers/     # HTTP endpoints (store/, user/, voice/)
├── core/            # Config, security, errors, logging
├── db/              # Database session, base model
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic (menu, order, voice session)
└── voice/           # Voice pipeline (Pipecat, tools, config)
```

### Store Portal Structure

```
store-portal/src/
├── api/             # Axios API clients (menuApi, orderApi, storeApi)
├── auth/            # Token management
├── routes/          # Page components (MenuRoute, OrdersRoute, ProfileRoute)
├── components/      # Reusable UI components
└── app/             # Routing and theme provider
```

Uses vendored `@zhqingit/liquid-glass-react` package from `packages/liquid-glass-react/`.

### User Portal Structure

```
user-portal/lib/
├── core/            # Config, theme, settings
├── data/            # API client, repositories, WebSocket/audio
├── features/        # Screens (auth, stores, voice, settings)
├── ui/              # Glass design system components
└── gen_l10n/        # Generated localization (en, zh)
```

State management: Riverpod. HTTP: Dio. Localization: ARB files in `l10n/`.

## Key Environment Variables

Backend (`backend/.env`):
- `DATABASE_URL` — Postgres connection string
- `JWT_SECRET`, `REFRESH_TOKEN_PEPPER` — Auth secrets
- `CORS_ORIGINS` — Allowed origins
- `VOICE_PROVIDER_STT`, `VOICE_PROVIDER_TTS`, `VOICE_PROVIDER_LLM` — Voice providers (default: google)
- `VOICE_LLM_MODEL` — LLM model (default: gemini-3.0-flash-preview)
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` — For voice services
- `TELEPHONY_DAILY_API_KEY`, `TELEPHONY_DAILY_ROOM_URL` — For phone ordering
