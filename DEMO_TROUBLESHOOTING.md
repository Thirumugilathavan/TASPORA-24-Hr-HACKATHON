# NALAM AI — Demonstration Troubleshooting & Recovery Guide

This guide provides rapid diagnostic steps and recovery procedures for common issues that may arise during live hackathon demonstrations or evaluator setup.

---

## 1. Port Conflicts

### Symptom: `ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`
- **Cause:** Another process or previous Uvicorn instance is already listening on port 8000.
- **Resolution (Windows PowerShell):**
  ```powershell
  # Find PID using port 8000
  netstat -ano | findstr :8000
  # Terminate process by PID (replace <PID>)
  taskkill /PID <PID> /F
  ```
- **Resolution (Alternative Port):**
  Start backend on port 8001:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
  ```
  *(Update `VITE_API_BASE_URL=http://localhost:8001` in `frontend/.env` if changing ports).*

---

## 2. Frontend Connectivity / CORS Errors

### Symptom: `ApiConnectionError: Unable to connect to NALAM AI API at http://localhost:8000`
- **Cause 1:** Backend Uvicorn server is not running.
  - *Fix:* Verify Terminal 1 shows `Uvicorn running on http://0.0.0.0:8000`. Test `http://localhost:8000/api/health` in browser.
- **Cause 2:** Browser blocked cross-origin request.
  - *Fix:* Backend `CORS_ORIGINS` includes `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`. Ensure frontend is accessed via `http://localhost:5173`.

---

## 3. IVR PIN Lockout Recovery

### Symptom: IVR simulator announces *"Your account is temporarily locked due to 3 incorrect attempts. Please try again in 15 minutes."*
- **Cause:** 3 consecutive incorrect PIN inputs triggered brute-force security lockout.
- **Fast Reset for Live Demo:**
  Run Python snippet to clear lockout in the demo database:
  ```powershell
  .\.venv\Scripts\python.exe -c "import asyncio, aiosqlite; async def reset(): db = await aiosqlite.connect('carebridge.db'); await db.execute('UPDATE ivr_auth_attempts SET is_locked=0, attempts_count=0, locked_until=NULL WHERE phone=\"9876543203\"'); await db.commit(); await db.close(); print('Lockout reset successfully!'); asyncio.run(reset())"
  ```

---

## 4. Database Reset & Clean Seed

### Symptom: Demo database has test records from previous test runs, or appointments double-booking occurs on same demo slot.
- **Resolution:** Re-run migrations or wipe local SQLite instance:
  ```bash
  # 1. Rollback or delete local carebridge.db
  del carebridge.db

  # 2. Re-apply Alembic migrations to fresh head
  alembic upgrade head

  # 3. Re-seed clean demo data
  python -m tests.seed_demo_helper   # or restart backend
  ```

---

## 5. Mock Mode vs Live API in Frontend

### Symptom: Frontend displays mock data instead of live backend responses.
- **Cause:** Demo toggle in header or `carebridge_mock_mode` localStorage key is enabled.
- **Fix:** 
  1. Look at the top banner: If `Demo Mode (Offline Mocks)` banner is visible, click the toggle switch to disable it.
  2. Or run in browser DevTools console:
     ```javascript
     localStorage.removeItem('carebridge_mock_mode');
     window.location.reload();
     ```

---

## 6. Doctor Attendance Self-Verification Failure (HTTP 403)

### Symptom: `HTTP 403 FORBIDDEN: Doctor profile not linked to user account`
- **Cause:** A doctor user logged in with a user account whose `users.id` is not linked to `Doctor.user_id`.
- **Fix:** Link the doctor profile using an administrative account:
  ```bash
  curl -X POST "http://localhost:8000/api/doctors/<DOCTOR_ID>/link-user" \
    -H "Authorization: Bearer <STAFF_JWT>" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"<DOCTOR_USER_ID>\"}"
  ```
  *(In seed data, Dr. Anita Sharma `9876543220` is already pre-linked).*
