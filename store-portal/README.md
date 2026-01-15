# store-portal

Minimal React SPA for the store web portal.

## Auth model (clean + simple)
- Access token is kept in memory (not localStorage).
- Refresh token + session id are httpOnly cookies set by the backend.
- On 401, the client calls `/store/auth/refresh` with credentials and retries once.

## Prerequisites
- Node.js + npm installed.

## Run (dev)
1. Copy env file:
   - `cp .env.example .env`
2. Install deps:
   - `npm install`
3. Start dev server:
   - `npm run dev`

## Local dev backend (recommended)
From the repo root:
- `cd backend && docker compose up --build`

This portal is configured to proxy API calls to the backend in dev:
- Browser calls `http://localhost:5174/store/...`
- Vite proxies to `http://localhost:8000/store/...` and forces Host to `store-api.local`

So you don't need to edit `/etc/hosts` for local testing.

## Backend requirements
- Backend must set store cookies on login/refresh.
- CORS must allow the portal origin and credentials.
