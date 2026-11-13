# NALAM — Two Vercel Projects with One Shared Domain Deployment Guide

## Architecture Overview

NALAM is deployed as **TWO SEPARATE Vercel Projects** connected under **ONE PUBLIC PRODUCTION DOMAIN** via Vercel Reverse Proxy Rewrites:

```
                                  PUBLIC INTERNET
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Shared Domain: nalam.vercel.app   │
                      │    (or custom production domain)     │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │          PROJECT 1: nalam-frontend             │
                 │      (React + Vite SPA - Root: frontend/)      │
                 └───────┬────────────────────────────────┬───────┘
                         │                                │
        Public Routes:   │                                │  API / Docs Routes:
        /, /login,       │                                │  /api, /api/*,
        /facilities,     │                                │  /docs, /openapi.json,
        /appointments    ▼                                │  /redoc
                 ┌───────────────┐                        ▼
                 │ Static Bundle │             ┌─────────────────────┐
                 │ (/index.html) │             │ Vercel Edge Rewrite │
                 └───────────────┘             └──────────┬──────────┘
                                                          │
                                        Reverse Proxy     │  HTTPS (Server-Side)
                                        Headers Preserved │  (Method, Auth, Body)
                                                          ▼
                                       ┌─────────────────────────────────────┐
                                       │       PROJECT 2: nalam-backend      │
                                       │    (FastAPI ASGI - Root: .)         │
                                       │   https://nalam-backend.vercel.app  │
                                       └──────────────────┬──────────────────┘
                                                          │
                                         Database Queries │  External AI Calls
                                                          ▼
                                            ┌─────────────────────────┐
                                            │ Managed PostgreSQL &    │
                                            │ Gnani AI STT/TTS APIs   │
                                            └─────────────────────────┘
```

---

## 1. Project Specifications

| Configuration Item | Project 1: `nalam-frontend` | Project 2: `nalam-backend` |
| :--- | :--- | :--- |
| **Vercel Project Name** | `nalam-frontend` *(or `nalam`)* | `nalam-backend` |
| **GitHub Repository** | `Thirumugilathavan/TASPORA-24-Hr-HACKATHON` | `Thirumugilathavan/TASPORA-24-Hr-HACKATHON` |
| **Branch** | `feature/nalam-vercel-services-deployment` | `feature/nalam-vercel-services-deployment` |
| **Root Directory** | `frontend/` | `./` (repo root) |
| **Framework** | `Vite` | `Other` (Python Serverless Function) |
| **Build Command** | `npm run build` | *None (Auto-detected)* |
| **Output Directory** | `dist` | *None (Serverless Function)* |
| **Configuration File** | `frontend/vercel.json` | `vercel.json` |
| **Entrypoint** | `frontend/src/main.tsx` $\rightarrow$ `dist/` | `api/index.py` $\rightarrow$ `app.main:app` |
| **Role** | Public entrypoint & Single Page Application | Private/Protected REST API & AI Engine |

---

## 2. Public Routing Table (Configured in `frontend/vercel.json`)

| Route Pattern | Destination Target | Reverse Proxy Behavior |
| :--- | :--- | :--- |
| `/api` | `https://nalam-backend.vercel.app/api` | Proxied to FastAPI backend |
| `/api/:path*` | `https://nalam-backend.vercel.app/api/:path*` | Exact path, query params, HTTP method & auth headers preserved |
| `/docs` | `https://nalam-backend.vercel.app/docs` | Proxied to FastAPI Swagger UI |
| `/openapi.json` | `https://nalam-backend.vercel.app/openapi.json` | Proxied to OpenAPI schema |
| `/redoc` | `https://nalam-backend.vercel.app/redoc` | Proxied to FastAPI ReDoc UI |
| `/(.*)` *(catch-all)* | `/index.html` | Client-side routing handled by React Router |

---

## 3. Step-by-Step Deployment Instructions

Deploy in the following order:

### Step 3.1: Deploy `nalam-backend` (First)
1. Go to **[https://vercel.com/new](https://vercel.com/new)**.
2. Select repository: **`Thirumugilathavan/TASPORA-24-Hr-HACKATHON`**.
3. Set **Project Name**: `nalam-backend`.
4. Set **Branch**: `feature/nalam-vercel-services-deployment`.
5. Keep **Root Directory**: `./` (leave default).
6. Under **Environment Variables**, add the required backend variables (see Section 4).
7. Click **Deploy**.
8. Note the assigned deployment URL (e.g., `https://nalam-backend.vercel.app` or similar).

### Step 3.2: Verify Backend URL in `frontend/vercel.json`
If Vercel assigned your backend a different domain name than `https://nalam-backend.vercel.app` (e.g., `https://nalam-backend-thirumugilathavans-projects.vercel.app`):
- Open [`frontend/vercel.json`](file:///frontend/vercel.json).
- Replace `https://nalam-backend.vercel.app` with your actual backend URL.
- Commit and push to `feature/nalam-vercel-services-deployment`.

### Step 3.3: Deploy `nalam-frontend` (Second)
1. Go to **[https://vercel.com/new](https://vercel.com/new)**.
2. Select repository: **`Thirumugilathavan/TASPORA-24-Hr-HACKATHON`**.
3. Set **Project Name**: `nalam-frontend` (or `nalam`).
4. Set **Branch**: `feature/nalam-vercel-services-deployment`.
5. Set **Root Directory**: `frontend`.
6. Framework Preset will auto-detect as **Vite**.
7. Click **Deploy**.
8. In **Project Settings $\rightarrow$ Domains**, attach your primary shared domain (e.g., `nalam.vercel.app` or your custom domain).

---

## 4. Production Environment Variables Reference

### Backend Project (`nalam-backend`)
Configure in Vercel under `nalam-backend` $\rightarrow$ Settings $\rightarrow$ Environment Variables:

| Variable | Value / Description |
| :--- | :--- |
| `PROJECT_NAME` | `"NALAM"` |
| `ENVIRONMENT` | `"production"` |
| `SECRET_KEY` | `"<generate-random-32-character-secret>"` |
| `DATABASE_URL` | `"postgresql+asyncpg://<user>:<password>@<host>:5432/<db>"` (e.g., Neon or Supabase) |
| `CORS_ORIGINS` | `["https://nalam.vercel.app", "https://nalam-frontend.vercel.app"]` |
| `GNANI_API_KEY` | `"<your-gnani-api-key>"` |
| `GNANI_STT_URL` | `"https://api.vachana.ai/stt/v3"` |
| `GNANI_TTS_URL` | `"https://api.vachana.ai/api/v1/tts/inference"` |
| `GNANI_VOICE_NAME` | `"Nalini"` |
| `GNANI_VOICE_MODEL` | `"timbre-v2.5"` |
| `GNANI_STT_MODEL` | `"prisma-v3.0"` |
| `IVR_API_KEY` | `"<secure-random-key>"` |
| `TELEPHONY_PROVIDER` | `"twilio"` *(or "mock")* |
| `TELEPHONY_AUTH_TOKEN` | `"<twilio-auth-token>"` |
| `TELEPHONY_WEBHOOK_BASE_URL` | `"https://nalam.vercel.app"` |

### Frontend Project (`nalam-frontend`)
*None required!* The frontend communicates via same-origin relative URLs (`/api/...`) routed by Vercel edge reverse proxy. All secrets remain strictly inside the backend project.

---

## 5. Post-Deployment Verification Checklist

Test on your shared domain `https://YOUR-NALAM-DOMAIN`:

- [ ] **`https://YOUR-NALAM-DOMAIN/`**: Loads NALAM Single Page Application.
- [ ] **`https://YOUR-NALAM-DOMAIN/facilities`**: Direct URL refresh loads correctly (SPA catch-all works).
- [ ] **`https://YOUR-NALAM-DOMAIN/api`**: Returns HTTP 200 with platform health and simulation disclosures.
- [ ] **`https://YOUR-NALAM-DOMAIN/api/health`**: Returns HTTP 200 with database connection status.
- [ ] **`https://YOUR-NALAM-DOMAIN/api/ai/chat`**: AI chat queries successfully reach FastAPI and return Indic responses.
- [ ] **`https://YOUR-NALAM-DOMAIN/docs`**: Swagger UI renders with all interactive endpoints.
- [ ] **`https://YOUR-NALAM-DOMAIN/openapi.json`**: Returns valid OpenAPI 3.1 JSON schema.
- [ ] **Network Tab Inspection**: All `/api/...` calls show same-origin requests with 0 CORS issues.
