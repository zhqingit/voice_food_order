# Backend (FastAPI + Postgres)

Template backend with:
- Signup/Login
- Access JWT
- Opaque refresh token + rotation
- Postgres persistence
- Docker Compose for local dev

## Local dev (Docker)

```bash
cd backend
docker compose up --build
```

API: http://localhost:8000

## Quick curl walkthrough

Signup:

```bash
curl -sS -X POST http://localhost:8000/auth/signup \
	-H 'Content-Type: application/json' \
	-d '{"email":"demo@example.com","password":"password123"}'
```

The response contains `access_token`, `refresh_token`, `session_id`.

Me (replace `$ACCESS`):

```bash
curl -sS http://localhost:8000/me \
	-H "Authorization: Bearer $ACCESS"
```

Refresh (replace `$SESSION_ID` and `$REFRESH`):

```bash
curl -sS -X POST http://localhost:8000/auth/refresh \
	-H 'Content-Type: application/json' \
	-d '{"session_id":"'$SESSION_ID'","refresh_token":"'$REFRESH'"}'
```

Logout current session (replace `$ACCESS` and `$SESSION_ID`):

```bash
curl -sS -X POST http://localhost:8000/auth/logout \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $ACCESS" \
	-d '{"scope":"current","session_id":"'$SESSION_ID'"}'
```

Logout all sessions (replace `$ACCESS`):

```bash
curl -sS -X POST http://localhost:8000/auth/logout \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $ACCESS" \
	-d '{"scope":"all"}'
```

## Local dev (no Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Env vars

- `DATABASE_URL`
- `JWT_SECRET`
- `REFRESH_TOKEN_PEPPER`
- `ACCESS_TOKEN_TTL_MINUTES`
- `REFRESH_TOKEN_TTL_DAYS`
- `CORS_ORIGINS`
