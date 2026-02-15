# auth_template

Full-stack auth template with:
- **Backend**: FastAPI + Postgres (Docker Compose)
- **User portal**: Flutter mobile app ("user")
- **Store portal**: React (Vite) web app ("store")

This repo intentionally demonstrates **two separate principals** (User vs Store) and a clean session model:
- **Access tokens** are JWTs (short-lived).
- **Refresh tokens** are opaque and stored/rotated server-side.
- **User (mobile)** refresh uses a JSON body (`session_id` + `refresh_token`).
- **Store (web)** refresh uses **httpOnly cookies**.

## Repo layout

- `backend/` — FastAPI API + DB models + Alembic migrations + tests
- `user-portal/` — Flutter user mobile app
- `store-portal/` — React store web portal

## Quick start (recommended)

### 1) Start backend (Postgres + API)

```bash
cd backend
docker compose up --build
```

Backend:
- Health: http://localhost:8000/health

### 2) Start store portal (web)

```bash
cd store-portal
cp .env.example .env
npm install
npm run dev
```

Then open the printed URL (by default Vite uses localhost).

## Voice service (planned)

The voice pipeline will run inside the backend and expose websocket + telephony endpoints.

Planned backend settings (in backend/.env):
- VOICE_PROVIDER_STT, VOICE_PROVIDER_TTS, VOICE_PROVIDER_LLM, VOICE_LLM_MODEL
- VOICE_WS_MAX_SECONDS, VOICE_WS_MAX_PAYLOAD_KB, VOICE_AUDIO_SAMPLE_RATE_HZ
- TELEPHONY_PROVIDER, TELEPHONY_DAILY_API_KEY, TELEPHONY_DAILY_ROOM_URL
- TELEPHONY_TWILIO_ACCOUNT_SID, TELEPHONY_TWILIO_AUTH_TOKEN, TELEPHONY_TWILIO_APP_SID

Note: endpoints and routes will be added in Phase 2. For now, the backend can start normally.

## Host-based API partitioning (important)

The backend enforces **host-based routing** (to keep portals isolated):
- **User API host**: `user-api.local`
- **Store API host**: `store-api.local`

These are configured in `backend/app/core/config.py` via:
- `USER_API_HOSTS` (default `user-api.local`)
- `STORE_API_HOSTS` (default `store-api.local`)

### Local dev options

- **Company portal (recommended):** `company-portal` is configured to proxy API calls in dev and forces the `Host: company-api.local` header, so you **do not** need to edit `/etc/hosts`.
- **Store portal (recommended):** `store-portal` is configured to proxy API calls in dev and forces the `Host: store-api.local` header, so you **do not** need to edit `/etc/hosts`.
- **Manual testing (curl/Postman):** include a Host header, e.g.

```bash
curl -sS -H 'Host: store-api.local' http://localhost:8000/health
```

## API overview

### User (mobile)
- `POST /user/auth/signup` → `{access_token, refresh_token, session_id}`
- `POST /user/auth/login` → `{access_token, refresh_token, session_id}`
- `POST /user/auth/refresh` → rotates refresh token, returns new `{access_token, refresh_token, session_id}`
- `POST /user/auth/logout` → revoke current/all sessions
- `GET /user/me` → current user

### Store (web)
- `POST /store/auth/signup` → `{access_token}` + sets httpOnly cookies
- `POST /store/auth/login` → `{access_token}` + sets httpOnly cookies
- `POST /store/auth/refresh` → rotates refresh cookie and returns `{access_token}`
- `POST /store/auth/logout` → revokes current session and clears cookies
- `GET /store/me` → current store

## Backend development

### Run without Docker (optional)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pytest -q
```

## Notes

- Real secrets should be provided via `backend/.env` (ignored by git). Do not commit `.env` files.
- `store-portal` keeps the access token in memory (not localStorage). Refresh is cookie-based.
- Refresh token reuse detection is implemented for both user and store sessions.
