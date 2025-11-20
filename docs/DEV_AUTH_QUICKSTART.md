# Dev Auth Quick Start

## What's going wrong

- You're not authenticated, so all the `/api/v1/*/me`, `/sessions`, `/monitoring/metal4`, etc. endpoints return 401.
- Frontend always calls those endpoints assuming there's a JWT (`auth_token`) in `localStorage`.
- In dev, you need either:
  - The built-in Founder account, or
  - A regular user account you create via the UI.

## Quick fix (do this once per dev environment)

### 1. Set env for dev

In repo root create `.env` (or export vars) with at least:

```bash
ELOHIM_ENV=development
# optional but recommended:
# ELOHIM_FOUNDER_PASSWORD=ElohimOS_2024_Founder
# ELOHIMOS_JWT_SECRET_KEY=some-long-random-string
```

### 2. Start backend with dev env

**Option A: Using the dev launcher script (recommended)**

```bash
cd apps/backend
./dev_backend.sh
```

**Option B: Manual start**

```bash
cd apps/backend
ELOHIM_ENV=development python -m uvicorn api.main:app --reload
```

### 3. Login in the frontend

- Open http://localhost:4200
- Use either:
  - **Founder**: `elohim_founder` / `ElohimOS_2024_Founder` (dev default), or
  - Click **"Create account"** and register a normal user
- After login, `auth_token` is stored in `localStorage` and 401 spam stops

### 4. Optional sanity check

In browser console:

```javascript
localStorage.getItem('auth_token')
```

From shell:

```bash
TOKEN='<paste token>'
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
```

You should get a JSON user object back.

## Long-term dev habit

- **Stable Founder setup**: `.env` is pre-configured with:
  - Explicit Founder credentials (no hidden defaults)
  - Stable JWT secret (tokens survive backend restarts)
  - Token lifespan: 7 days
- **As long as**:
  - `ELOHIMOS_JWT_SECRET_KEY` stays the same, and
  - Token hasn't expired (7-day window),
  - You won't need to log in again; the token in `localStorage.auth_token` will keep working
- **If you start seeing 401s again**:
  - Token expired, or
  - You changed/deleted `ELOHIMOS_JWT_SECRET_KEY`
  - Fix: Just log out + log back in as Founder; no other setup needed

## Architecture Details

See full auth flow documentation:
- Backend auth: `apps/backend/api/auth_middleware.py`
- Auth routes: `apps/backend/api/auth_routes.py`
- Frontend auth: `apps/frontend/src/hooks/useAppBootstrap.ts`
- Login UI: `apps/frontend/src/components/Login.tsx`
