# NALAM — VERCEL SINGLE-PROJECT MULTI-SERVICE DEPLOYMENT REPORT

**Application:** NALAM (formerly CareBridge) – AI-Powered Healthcare Accessibility Platform  
**Official Repository:** `https://github.com/Thirumugilathavan/TASPORA-24-Hr-HACKATHON`  
**Feature Branch:** `feature/nalam-vercel-services-deployment`  
**Delivered Remote Commit:** `b37ac70312073a67e4cbb725f063f0f187fdde62`  
**Overall Deployment Status:** **BLOCKED — USER ACTION REQUIRED** (Vercel Authentication / Project Link Required)  

---

## 1. Multi-Service Project Architecture

The repository has been configured to deploy the React/Vite frontend and FastAPI backend together as **ONE Vercel Project** (`nalam`) under **ONE shared production domain** using Vercel Multi-Service architecture.

### Service Layout & Mapping
```
TASPORA-24-Hr-HACKATHON (Root: .)
├── vercel.json                 <-- Vercel Multi-Service Project Configuration
├── app/                        <-- FastAPI Backend Service ('app')
│   └── main.py                 <-- ASGI Entrypoint ('app.main:app')
├── frontend/                   <-- React/Vite Frontend Service ('frontend')
│   ├── src/                    <-- Client-side application
│   └── dist/                   <-- Static build output
└── requirements.txt            <-- Python dependencies
```

| Service Name | Root Directory | Framework | Entrypoint / Build | Exposure |
| :--- | :--- | :--- | :--- | :--- |
| **`frontend`** | `frontend/` | `vite` | `npm run build` (`dist/`) | Public (`/(.*)`) |
| **`app`** | `.` | `fastapi` | `app.main:app` | Public (`/api/*`, `/docs`, `/openapi.json`, `/redoc`) |

---

## 2. Public Routing Matrix (`vercel.json`)

All traffic on the single production domain is routed via top-level rewrites:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "frontend": {
      "root": "frontend/",
      "framework": "vite"
    },
    "app": {
      "root": ".",
      "framework": "fastapi",
      "entrypoint": "app.main:app"
    }
  },
  "rewrites": [
    {
      "source": "/api",
      "destination": { "service": "app" }
    },
    {
      "source": "/api/(.*)",
      "destination": { "service": "app" }
    },
    {
      "source": "/docs",
      "destination": { "service": "app", "path": "/docs" }
    },
    {
      "source": "/openapi.json",
      "destination": { "service": "app", "path": "/openapi.json" }
    },
    {
      "source": "/redoc",
      "destination": { "service": "app", "path": "/redoc" }
    },
    {
      "source": "/(.*)",
      "destination": { "service": "frontend" }
    }
  ]
}
```

### Routing Precedence
1. `/api` & `/api/(.*)` $\rightarrow$ Routed directly to the FastAPI `app` service.
2. `/docs`, `/openapi.json`, `/redoc` $\rightarrow$ Routed to FastAPI documentation endpoints.
3. `/(.*)` $\rightarrow$ Routed to the React `frontend` service for client-side routing.

---

## 3. Frontend-to-Backend Same-Origin Configuration

In `frontend/src/lib/config.ts`:
- **Local Development:** When `import.meta.env.DEV` is true, defaults to `http://localhost:8000` (or `VITE_API_BASE_URL` if set).
- **Production (`import.meta.env.PROD`):** When `VITE_API_BASE_URL` is omitted, defaults to `""` (empty string).
- **Result:** All browser API calls (`/api/ai/chat`, `/api/facilities`, `/api/health`, etc.) use same-origin relative URLs on Vercel, completely avoiding CORS restrictions and eliminating hardcoded URLs.

---

## 4. Quality & Build Validation

### 4.1 Frontend Production Build
```powershell
cd frontend; npm run build
```
- **TypeScript Typecheck:** `tsc -b` passed with 0 errors.
- **Vite Bundle:** Built cleanly in 5.84s:
  - `dist/index.html` (0.83 kB)
  - `dist/assets/index-ryEUEosL.css` (48.29 kB)
  - `dist/assets/index-TT3Nd-of.js` (400.42 kB)
- **Status:** **SUCCESS**

### 4.2 Backend Test Suite
```powershell
.venv\Scripts\pytest.exe tests/test_health.py tests/test_gnani_voice.py tests/test_ai_agent.py tests/test_facilities_nearby.py tests/test_villages_search.py tests/test_ivr_live_telephony.py -v
```
- **Tests Executed:** 41 tests across Health, Base API Root, Gnani Voice, AI Agent, Nearby Facilities, Nationwide Location Search, and Telephony.
- **Pass Rate:** **41 / 41 passed (100%)** in 22.88s.
- **Status:** **SUCCESS**

### 4.3 Git & Remote Push Verification
- **Branch:** `feature/nalam-vercel-services-deployment`
- **Pushed Commit SHA:** `7cfa4dde722a2f72009b53e33066369545e25280`
- **Remote Verification:** Verified via `git ls-remote origin refs/heads/feature/nalam-vercel-services-deployment`.
- **Status:** **SUCCESS**

---

## 5. Deployment Status: BLOCKED — USER ACTION REQUIRED

### Reason for Block
The local CLI environment does not possess active Vercel user authentication (`Logged out`). Additionally, Windows file-system permissions block anonymous CLI builder symlink creation without Windows Developer Mode enabled.

### Exactly What You Need to Do (2-Minute Setup)

#### Option A: One-Click Git Import via Vercel Web Dashboard (Recommended)
1. Go to **[https://vercel.com/new](https://vercel.com/new)**.
2. Select your repository: **`Thirumugilathavan/TASPORA-24-Hr-HACKATHON`**.
3. Set the **Branch** to: `feature/nalam-vercel-services-deployment` (or merge to `main`).
4. Set the **Project Name** to: `nalam`.
5. Keep **Root Directory** as `./` (Vercel will detect `vercel.json` and configure both services automatically).
6. Under **Environment Variables**, add the required backend variables (see Section 6).
7. Click **Deploy**. Both services will build and deploy atomically under a single shared domain!

#### Option B: Deploy via CLI
Run the following in PowerShell:
```powershell
# 1. Log in to Vercel
npx vercel login

# 2. Link the project
npx vercel link --project nalam

# 3. Deploy to production
npx vercel deploy --prod
```

---

## 6. Required Vercel Environment Variables Checklist

Configure these in the Vercel Dashboard under **Project Settings $\rightarrow$ Environment Variables**:

| Variable | Recommended Value | Purpose |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `"NALAM"` | Project branding |
| `ENVIRONMENT` | `"production"` | Production mode |
| `SECRET_KEY` | `"<generate-random-32-char-string>"` | JWT security key |
| `DATABASE_URL` | `"postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>"` | **Required for persistent storage** (Neon, Supabase, or AWS RDS). *Note: SQLite does not persist across serverless cold starts.* |
| `GNANI_API_KEY` | `"<your-gnani-api-key>"` | Live Gnani Indic speech recognition & synthesis |
| `GNANI_STT_URL` | `"https://api.vachana.ai/stt/v3"` | Prisma STT endpoint |
| `GNANI_TTS_URL` | `"https://api.vachana.ai/api/v1/tts/inference"` | Timbre TTS endpoint |
| `GNANI_VOICE_NAME`| `"Nalini"` | Default voice |
| `GNANI_VOICE_MODEL`| `"timbre-v2.5"` | Voice model |
| `GNANI_STT_MODEL` | `"prisma-v3.0"` | STT model |
| `IVR_API_KEY` | `"<secure-random-key>"` | IVR telephony authentication |
| `TELEPHONY_PROVIDER` | `"twilio"` *(or "mock")* | Carrier integration |
| `TELEPHONY_AUTH_TOKEN`| `"<twilio-auth-token>"` | Webhook HMAC verification |
| `TELEPHONY_WEBHOOK_BASE_URL` | `"https://nalam.vercel.app"` | Carrier webhook routing |
