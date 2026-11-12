# CareBridge – Frontend UI

CareBridge is an AI-powered rural healthcare accessibility and coordination platform connecting patients with primary healthcare centers (PHCs), community health centers (CHCs), pharmacies, ASHA workers, and medical staff.

**Tagline**: *No Wasted Trips. Better Access. Continuous Care.*

This frontend application is built with **React 18**, **Vite**, **TypeScript**, and **Tailwind CSS**, featuring comprehensive bilingual support (Tamil & English default with Hindi, Telugu, Bengali), real backend API integration (`http://localhost:8000`), and smooth fallback demo mock mode.

---

## Features Built

- **Bilingual & Multi-Language Support (Tamil Default)**:
  - Defaulting to Tamil (`ta`) for rural Tamil Nadu healthcare contexts with one-click toggling to English (`en`), Hindi (`hi`), Telugu (`te`), and Bengali (`bn`).
  - Centralized `LanguageContext` and `i18n.ts` dictionary translating headers, sidebars, dashboard metrics, status badges, emergency advisories, and forms.
- **Backend API Integration & Hybrid Mock Mode**:
  - Automatically targets live FastAPI backend at `http://localhost:8000`.
  - Graceful fallback with localStorage-based runtime toggle in `/profile` for offline jury evaluations and demonstrations.
- **Identity Decoupling & Patient Profile Flow**:
  - Full support for decoupled authentication (`User`) and clinical records (`Patient`).
  - Seamless two-step registration (`POST /api/auth/register` + `POST /api/patients`) with automatic session token capture.
- **Emergency Helpline & Medical Safety Disclaimer**:
  - Prominent notices highlighting the non-diagnostic coordination nature of CareBridge (no prescription/dosage issuance).
  - Instant one-tap dials for `108` (Ambulance) & `102` (Janani Shishu Maternal Helpline).
- **Interactive Dashboard**:
  - Real-time summary statistics (nearby facilities, active requests, upcoming visits, ASHA status).
  - Quick action buttons (Create Request, Book Visit).
  - Upcoming appointments list with instant cancellation dialog.
  - Recent healthcare requests overview.
  - Nearest facilities shortcut and emergency hotlines.
- **Healthcare Facilities Directory (`/facilities`)**:
  - Filter by facility type (`PHC`, `CHC`, `HOSPITAL`, `PHARMACY`).
  - Search by center name, district, or offered medical services.
  - Facility modal showing doctor roster, attendance status, operating hours, and direct booking trigger.
- **Medicine Stock & Bayesian Availability (`/medicines`)**:
  - Search essential drug formulary and filter by category (Antibiotics, Analgesics, Chronic Care, Maternal).
  - Probabilistic Bayesian stock badges: **Likely ($p \ge 0.65$)**, **Uncertain ($0.35 < p < 0.65$)**, or **Unlikely ($p \le 0.35$)**.
  - One-click "Request Refill" modal prefilled with selected medicine.
- **Care Requests & AI Optimization (`/requests`)**:
  - Submit consultation, refill, checkup, or diagnostic requests with urgency levels (`NORMAL`, `PRIORITY`, `URGENT`).
  - AI Routing Panel showing facility recommendations ranked by proximity, stock confidence, and expected travel loss ($E[\text{loss}] = P(\text{fail}) \times \text{cost}$).
  - Direct appointment booking from recommendation cards.
- **Appointments Management (`/appointments`)**:
  - Filter between "Upcoming Visits" and "Completed & Cancelled".
  - Appointment booking modal with facility selection, doctor selection, date picker, and ISO-compliant time slot selector.
  - Transactional double-booking prevention support.
  - Safe appointment cancellation with destructive confirmation modal.
- **Profile & Preferences (`/profile`)**:
  - Patient health identity card (UID, phone, village coordinates, DOB, consent status).
  - Multi-language communication selector (English, தமிழ், हिंदी, తెలుగు, বাংলা).
  - Runtime toggle for Demo Mock Mode vs Live Backend API.

---

## Getting Started

### 1. Prerequisites
- Node.js (v18+) & npm

### 2. Environment Configuration
Inspect or edit `.env`:
```bash
# Set to 'false' (default) to connect to live FastAPI backend on port 8000
VITE_MOCK_MODE=false
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Install Dependencies
```bash
npm install
```

### 4. Run Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:5173`.

### 5. Build for Production
```bash
npm run build
```
Creates an optimized static bundle in `dist/`.
