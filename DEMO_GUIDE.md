# CareBridge — Live Hackathon Demonstration Guide

**Project:** CareBridge – AI-Powered Rural Healthcare Accessibility & Coordination Platform  
**Tagline:** *No Wasted Trips. Better Access. Continuous Care.*  
**Primary Evaluator Channel:** Web Application (React + TypeScript) + Voice Keypad (CLI IVR Simulator)

---

## 1. Prerequisites & Environment Setup

### Required Software
- **Python 3.11+** (Tested on Python 3.14)
- **Node.js 18+ & npm** (Tested on Node v20+)
- **Git**

### Step-by-Step System Startup

#### Terminal 1 — Backend API Service
```bash
# 1. Activate virtual environment
.\.venv\Scripts\activate       # Windows PowerShell
# source .venv/bin/activate    # Linux / macOS

# 2. Run Database Migrations to latest single head
alembic upgrade head

# 3. Start FastAPI server on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Health verification:* Open `http://localhost:8000/api/health` $\to$ Returns `{"status":"healthy","service":"carebridge-backend"}`.  
*Interactive Swagger docs:* `http://localhost:8000/docs`

---

#### Terminal 2 — Frontend Web Application
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start Vite development server on port 5173
npm run dev
```
*Web App URL:* Open `http://localhost:5173` in your browser.

---

#### Terminal 3 — Voice Access / Button-Phone Simulator
```bash
# In repository root with virtual environment activated:
python -m app.tools.ivr_simulator --phone 9876543203 --lang ta
```

---

## 2. Recommended 14-Step Live Hackathon Walkthrough

### Part A: Multilingual Web Experience (Steps 1–12)

| Step | Action | What to Point Out to Judges |
|---|---|---|
| **1. Open Web UI** | Navigate to `http://localhost:5173` | Modern, clean blue/teal responsive healthcare layout designed for mobile and desktop. |
| **2. Tamil-First Language** | Click the Tamil / English switch in top-right header | Demonstrates accessibility for rural Tamil Nadu patients. All labels, buttons, and alerts switch instantly between தமிழ் and English. |
| **3. Registration or Login** | Log in with demo patient: Phone: `9876543203`, Password: `PatientPass123` (or click "Register" for a new fictional patient) | Role-based authentication: public registration strictly provisions `PATIENT` role; client-supplied administrative roles are ignored. |
| **4. Explicit Consent** | View Patient Profile modal | **Privacy Guard:** Notice `Consent Given` checkbox. Consent defaults to `False`. Frontline workers cannot inspect personal records without explicit opt-in. |
| **5. Facility Discovery** | Click "Facilities" in navigation | Lists primary health centres (PHC), community health centres (CHC), and sub-centres with synthetic geography labels (`is_synthetic: true`). |
| **6. Doctor Attendance** | Open facility details for *PHC Rampur* | Notice Dr. Anita Sharma's schedule: Attendance is marked `PRESENT` (physically verified by doctor login) vs `EXPECTED` (planned shift). **Zero false promises.** |
| **7. Medicine Stock Intelligence** | Click "Medicines" in navigation | Search for *Paracetamol* or *Amoxicillin*. Shows probabilistic availability labels (`LIKELY`, `UNCERTAIN`, `UNLIKELY`) based on weighted staff/ASHA reports. |
| **8. Create Healthcare Request** | Click "+ New Request" button | Select Request Type: `CONSULTATION` or `REFILL`, Urgency: `NORMAL` or `PRIORITY`, and select home village. |
| **9. Recommendation Engine** | View generated recommendations | **Core Innovation:** System ranks facilities in ascending order of **Expected Trip Loss**! |
| **10. Explain the Loss Formula** | Hover/inspect recommendation card | Shows formula: $\text{Expected Loss} = \text{RoundHalfUp}(\text{Failure Probability} \times \text{Travel Cost})$. Factors in straight-line distance, doctor presence, and stock confidence. |
| **11. Book Confirmed Slot** | Click "Book Appointment" on recommended facility | Slot booking succeeds with instantaneous confirmation. Partial database unique index prevents double booking of the same slot. |
| **12. Cancellation & Slot Freeing** | View "My Appointments" $\to$ Click "Cancel" | Cancelling releases the slot immediately, making it available for other rural patients without orphan locks. |

---

### Part B: Button-Phone Voice Access (Steps 13–14)

| Step | Action | What to Point Out to Judges |
|---|---|---|
| **13. Dial IVR Simulator** | In Terminal 3, run `python -m app.tools.ivr_simulator --phone 9876543203` | Welcomes caller in spoken Tamil (`1`) or English (`2`). Zero smartphone / internet requirement. |
| **14. Authenticate & Lookup** | Press `1` (Facility Info), `2` (Doctor Shift), or `4` (Book Appointment $\to$ Enter PIN `3203#`) | Authenticates caller securely. If 3 wrong PINs entered $\to$ triggers 15-minute brute-force lockout. Pressing `7` triggers immediate 108 emergency advice without login. |

---

## 3. The Core Differentiator: Uncertainty-Aware Journey Routing

Unlike generic hospital appointment apps (which assume doctors are always present and pharmacies are fully stocked), **CareBridge solves the rural reality**:
1. **Belief States:** Medicines are tracked via probability $P(\text{available}) \in [0.0, 1.0]$ and confidence $c \in [0.0, 1.0]$.
2. **Attendance Truth:** Distinguishes planned roster (`EXPECTED`) from physical biometric/self check-in (`PRESENT`).
3. **Loss-Minimization:** Calculates the risk of a wasted 30 km journey before the patient boards a rural bus.

---

## 4. Medical Safety & Clinical Scope

> **Clinical Disclaimer:** CareBridge is an access and logistical coordination platform. It does **NOT** provide AI diagnosis, prescription generation, medicine dosage calculations, or drug substitutions. All clinical treatment decisions remain exclusively with licensed doctors.
