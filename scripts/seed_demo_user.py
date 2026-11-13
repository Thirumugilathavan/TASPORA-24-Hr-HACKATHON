import os
import sys
import sqlite3
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.security import hash_password

DB_PATH = "carebridge.db"

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get first village
    cur.execute("SELECT id, name, district, state, latitude, longitude FROM villages LIMIT 1")
    v_row = cur.fetchone()
    if not v_row:
        print("Village not found!")
        return

    v_id = v_row[0]
    print(f"Target Village: {v_row[1]}, {v_row[2]}, {v_row[3]} ({v_row[4]}, {v_row[5]})")

    phone = "9876543210"
    name = "Demo Patient"
    pass_hash = hash_password("DemoPass123!")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check if user exists
    cur.execute("SELECT id FROM users WHERE phone = ?", (phone,))
    u_row = cur.fetchone()
    if u_row:
        user_id = u_row[0]
        cur.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE id = ?", (pass_hash, user_id))
    else:
        user_id = uuid.uuid4().hex
        cur.execute(
            "INSERT INTO users (id, name, phone, password_hash, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, phone, pass_hash, "PATIENT", 1, now_iso, now_iso),
        )

    # Check if patient exists
    cur.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,))
    p_row = cur.fetchone()
    if p_row:
        cur.execute("UPDATE patients SET village_id = ? WHERE id = ?", (v_id, p_row[0]))
    else:
        patient_id = uuid.uuid4().hex
        cur.execute(
            "INSERT INTO patients (id, user_id, village_id, date_of_birth, preferred_language, consent_given, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (patient_id, user_id, v_id, "1992-08-15", "ta", 1, now_iso, now_iso),
        )

    conn.commit()
    conn.close()
    print("Demo user seeded successfully with real village and credentials!")

if __name__ == "__main__":
    seed()
