# CareBridge AI Assistant — Architecture, Tool Calling, RAG & Voice Integration

**Project:** CareBridge – AI-Powered Rural Healthcare Accessibility and Coordination Platform  
**Tagline:** *No Wasted Trips. Better Access. Continuous Care.*  
**Module:** CareBridge AI Healthcare Assistant (`app/ai`)

---

## 1. Executive Summary & Core Philosophy

In rural healthcare accessibility across India, patient journeys are fraught with uncertainty: clinics may lack doctors on duty, pharmacies may be out of essential medicines, and patients often spend hours on buses only to arrive at locked doors or unstocked dispensaries.

The **CareBridge AI Assistant** is designed to address this reality. Its defining architectural principle is:

$$\mathbf{UNDERSTAND} \longrightarrow \mathbf{EXECUTE} \longrightarrow \mathbf{RETRIEVE} \longrightarrow \mathbf{VERIFY} \longrightarrow \mathbf{EXPLAIN} \longrightarrow \mathbf{DISPLAY}$$

### The Strict Anti-Pattern Elimination
The assistant enforces a strict, non-negotiable operational directive:
> **The AI must NEVER merely announce an intention to search, check, find, or update records. It must execute the backend tools, retrieve verified ground-truth data, calculate geographic distances and expected trip loss, and return the factual records in the very same response.**

For example, when a user asks:
```
"Find a PHC near Tiruchengode"
```
The AI **does not** reply with:
> *"I'll search the available PHC records for Tiruchengode and show matching facilities with their recorded services and locations."* ❌

Instead, the AI executes `search_facilities_tool`, calculates straight-line haversine distances, inspects today's doctor schedules, and immediately delivers:
```markdown
Primary Healthcare Facilities near Tiruchengode (ranked by geographic proximity):

- UPHC Tiruchengode (PHC) — 0.4 km
  - Address: Near Old Bus Stand, Tiruchengode, Namakkal District
  - Doctor on duty: Dr. K. Senthil Nathan (Status: PRESENT — Physically verified present)
  - Core Services: General OPD, Maternal Care, Immunization, Diagnostic Lab
  [Action: Book Consultation Slot]

- CHC Tiruchengode (CHC) — 0.7 km
  - Address: Sankari Main Road, Tiruchengode
  - Doctor on duty: Dr. R. Priya (Status: PRESENT — Inpatient & OPD)
  - Core Services: 24/7 Emergency, Inpatient Ward, Surgery, Pediatrics

- PHC Molasi (PHC) — 6.5 km
  - Address: Main Road, Molasi, Tiruchengode Taluk
  - Doctor: Dr. M. Ganesan (Status: EXPECTED — Shift scheduled, check-in pending)
```
Accompanying each facility is an interactive UI card with live booking triggers and attendance badges.

---

## 2. System Architecture Overview

```
                                  +------------------------------------+
                                  |     User / Patient / ASHA / Staff   |
                                  +-----------------+------------------+
                                                    |
                         +--------------------------+--------------------------+
                         | (Web UI / Speech Mic)                               | (Feature Phone / DTMF)
                         v                                                     v
          +-------------------------------+                     +-------------------------------+
          |  React + TypeScript Frontend  |                     |  Button-Phone IVR Simulator   |
          |  - AIAssistantModal           |                     |  - DTMF Keypad (1=ta, 2=en)   |
          |  - Floating Action Button     |                     |  - Emergency 108 Shortcut '7' |
          +---------------+---------------+                     +---------------+---------------+
                          |                                                     |
                          +--------------------------+--------------------------+
                                                     | HTTP REST API
                                                     v
                                  +------------------------------------+
                                  |        FastAPI AI Subsystem        |
                                  |         (/api/ai/chat)             |
                                  +------------------+-----------------+
                                                     |
                                                     v
                                  +------------------------------------+
                                  |       CareBridge Agent Loop        |
                                  |      (Intent & Language Triage)    |
                                  +---------+----------------+---------+
                                            |                |
                       +--------------------+                +--------------------+
                       | (Data / Tool Query)                                      | (Doc / Architecture)
                       v                                                          v
        +-------------------------------+                          +-------------------------------+
        |       Live Backend Tools      |                          |      BM25 RAG Knowledge Engine |
        |  - search_facilities_tool     |                          |  - STOCK_ALGORITHM.md         |
        |  - check_doctor_availability  |                          |  - README.md & API.md         |
        |  - check_medicine_stock_tool  |                          |  - IVR_ARCHITECTURE.md        |
        |  - get_recommendations_tool   |                          |  - DEMO_TEST_DATA.md          |
        |  - emergency_guidance_tool    |                          +---------------+---------------+
        +---------------+---------------+                                          |
                        |                                                          |
                        v                                                          v
        +-------------------------------+                          +-------------------------------+
        |  SQLite / PostgreSQL Database |                          |  Indexed Document Chunks      |
        |  - facilities & services      |                          |  - Math formulations          |
        |  - doctor_schedules           |                          |  - Loss calculation formulas  |
        |  - facility_medicine_beliefs  |                          |  - PIN lockout policies       |
        +-------------------------------+                          +-------------------------------+
```

---

## 3. The 3 Architectural Pillars

### Pillar 1: Medical Scope, Safety Boundaries & System Prompting
The agent operates under strict clinical and legal safety guardrails:
1. **Non-Diagnostic Policy:** CareBridge is an access and logistical coordination engine. It strictly refuses to generate medical diagnoses, clinical evaluations, prescription generation, or drug dosage recommendations.
2. **Safe Redirection:** If a patient asks *"What dose of paracetamol should I take for fever?"*, the agent politely explains that only a licensed medical doctor can prescribe dosages, queries the database for the nearest operating PHC, and displays doctor shifts so the patient can be seen by a physician.
3. **Emergency Triaging:** If symptoms indicate a critical emergency (severe chest pain, stroke, breathlessness, major trauma, heavy bleeding), the agent immediately halts standard Q&A and triggers the **Emergency Protocol**: displays the 108 ambulance call button and lists nearest 24/7 trauma hospitals.
4. **Attendance Truth:** Explicitly distinguishes `PRESENT` (physically verified on site) from `EXPECTED` (rostered planned shift).
5. **Probabilistic Stock:** Explains medicine availability as `LIKELY` ($P \ge 0.75$), `UNCERTAIN` ($0.40 \le P < 0.75$), and `UNLIKELY` ($P < 0.40$) without inventing phantom unit counts.

### Pillar 2: RAG (Retrieval-Augmented Generation) Engine
The local RAG engine (`app/ai/rag.py`):
- Indexes 10 repository markdown documents (`STOCK_ALGORITHM.md`, `README.md`, `API.md`, `IVR_ARCHITECTURE.md`, `IVR_API.md`, `IVR_CALL_FLOWS.md`, `DEMO_GUIDE.md`, `DEMO_TEST_DATA.md`, `FINAL_SECURITY_AUDIT.md`, `FINAL_SMOKE_TEST_REPORT.md`).
- Parses markdown into semantic sections with tokenization and stopword removal.
- Uses BM25 probabilistic relevance scoring with document length normalization and header matching boosts.
- Formulates answers citing exact equations and source documents.

#### The Recommendation Loss Formula (Retrieved via RAG):
$$\text{Expected Loss} = \text{RoundHalfUp}(\text{Failure Probability} \times \text{Travel Cost})$$

Where:
- $\text{Travel Cost} = \text{Base Cost} + (\text{Cost per km} \times \text{Distance in km})$
- $\text{Failure Probability} = f(\text{Doctor Attendance}, 1.0 - P_{\text{available}})$

### Pillar 3: Tool / Function Calling Handlers
The agent executes typed Python backend handlers with direct database sessions:

| Tool Name | Parameters | Ground Truth Operation |
|---|---|---|
| `search_facilities_tool` | `location_name`, `facility_type`, `service`, `limit` | Haversine distance calculation from target coordinates; eagerly loads services, doctors, and today's schedule. |
| `check_doctor_availability_tool` | `facility_name`, `doctor_name`, `specialization`, `location` | Queries `doctors` and `doctor_schedules`; checks verified attendance (`PRESENT` vs `EXPECTED`). |
| `check_medicine_stock_tool` | `medicine_name`, `facility_name`, `location` | Queries `facility_medicine_beliefs` for Bayesian probability, confidence, and triage label. |
| `get_recommendations_tool` | `village_name`, `request_type`, `urgency`, `medicine_name` | Computes Expected Trip Loss for each facility and ranks in ascending order. |
| `query_rag_knowledge_tool` | `query`, `top_k` | BM25 retrieval over project technical specifications and algorithm whitepapers. |
| `emergency_guidance_tool` | `symptom_or_query` | Official 108 emergency ambulance protocols and 24x7 trauma facilities. |

---

## 4. Multimodal Voice Architecture (Gnani.ai Indic Voice Adapter)

CareBridge is built for rural Tamil Nadu citizens who may prefer voice interactions over typing:
- **Speech-to-Text (STT):** Endpoint `/api/ai/voice/transcribe` accepts Base64 audio and transcribes into Tamil (`ta-IN`) or English (`en-IN`).
- **Text-to-Speech (TTS):** Endpoint `/api/ai/voice/synthesize` synthesizes response text into natural audio.
- **Resilient Fallback Design:** When external `GNANI_API_KEY` credentials are not present in `.env`, the adapter operates in local evaluation mode, providing instant mock transcripts and valid PCM/WAV headers, while the frontend leverages the browser's native `SpeechRecognition` and `SpeechSynthesis` APIs for a fully functional voice experience out-of-the-box.

---

## 5. API Endpoints Reference

### `POST /api/ai/chat`
**Request Body:**
```json
{
  "message": "Find a PHC near Tiruchengode",
  "language": "en",
  "location_context": "Tiruchengode"
}
```

**Response Body:**
```json
{
  "conversation_id": "0df006d6-fcfd-4876-b6d8-04f86d63d08f",
  "response_text": "Primary Healthcare Facilities near Tiruchengode...",
  "language": "en",
  "intent": "FACILITY_PROXIMITY_SEARCH",
  "tools_called": ["search_facilities_tool"],
  "cards": [
    {
      "type": "FACILITY",
      "title": "UPHC Tiruchengode",
      "subtitle": "PHC • 0.4 km away",
      "badge": "Doctor: PRESENT",
      "badge_color": "green",
      "details": {
        "distance_km": 0.4,
        "address": "Near Old Bus Stand, Tiruchengode...",
        "doctor_name": "Dr. K. Senthil Nathan",
        "doctor_status": "PRESENT",
        "services": ["General OPD", "Maternal Care", "Immunization"]
      },
      "action": {
        "label": "Book Appointment Slot",
        "type": "BOOK",
        "facility_id": "2a654d65-fa58-4a6f-ab45-013de8a40963"
      }
    }
  ],
  "rag_sources": [],
  "action_taken": "RETRIEVE_AND_DISPLAY_FACILITIES",
  "disclaimer": "CareBridge provides accessibility and coordination information only..."
}
```

### Other AI Endpoints:
- `POST /api/ai/voice/transcribe`: Audio STT transcription.
- `POST /api/ai/voice/synthesize`: Text-to-speech audio synthesis.
- `GET /api/ai/health`: Reports subsystem readiness, indexed RAG document count, and tool registry count.
- `GET /api/ai/tools`: Catalogues tool schemas with parameter descriptions.
- `POST /api/ai/feedback`: Collects user satisfaction ratings (1 to 5 stars).

---

## 6. Verification and Test Results

The CareBridge AI Assistant is backed by a dedicated test suite (`tests/test_ai_agent.py`) and passes all 144 backend tests:

```bash
$ pytest tests/test_ai_agent.py -v
tests/test_ai_agent.py::test_find_phc_near_tiruchengode_executes_and_returns_records PASSED
tests/test_ai_agent.py::test_doctor_availability_lookup PASSED
tests/test_ai_agent.py::test_medicine_stock_probabilistic_lookup PASSED
tests/test_ai_agent.py::test_rag_query_expected_loss_formula PASSED
tests/test_ai_agent.py::test_emergency_triage_triggers_108_protocol PASSED
tests/test_ai_agent.py::test_clinical_safety_guard_enforces_non_diagnostic_posture PASSED
tests/test_ai_agent.py::test_tamil_multilingual_query_returns_tamil_guidance PASSED
tests/test_ai_agent.py::test_ai_health_and_tools_catalog PASSED
tests/test_ai_agent.py::test_voice_transcribe_and_synthesize_endpoints PASSED
tests/test_ai_agent.py::test_ai_feedback_submission PASSED
============================= 10 passed in 6.09s ==============================

$ pytest -q
144 passed in 101.01s (0:01:41)
```

Frontend production build verification:
```bash
$ npm run build
> carebridge-frontend@0.1.0 build
> tsc -b && vite build
✓ 1629 modules transformed.
dist/index.html                   0.83 kB
dist/assets/index-BVOo9UDD.css   40.29 kB
dist/assets/index-CFMx7Gel.js   350.20 kB
✓ built in 6.10s
```
