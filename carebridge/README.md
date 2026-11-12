# CareBridge – Patient and Village Management Module

This module implements the **Patient Management** and **Village Directory** services for the CareBridge rural healthcare accessibility platform.

It is seamlessly integrated with the main developer's shared Phase 1 foundation.

---

## 1. Module Overview & Features

### A. Village Directory
- **SQLAlchemy 2.0 Model:** `Village` (`app.models.village.Village`) inheriting from `Base, UUIDPrimaryKeyMixin, TimestampMixin`.
- **Synthetic Seed Support:** 10 pre-configured rural Uttar Pradesh villages (Sitapur & Lakhimpur Kheri) in `seed_data/villages.json`, marked with `is_synthetic = True`.
- **Endpoint:** `GET /api/villages` returning paginated format `{"items": [...], "total": n}` adhering to `app.schemas.shared.Page`.

### B. Patient Management
- **SQLAlchemy 2.0 Model:** `Patient` (`app.models.patient.Patient`) inheriting from `Base, UUIDPrimaryKeyMixin, TimestampMixin`.
- **Relational Integrity:**
  - `user_id`: Mandatory & unique foreign key to `users.id` with `ondelete="RESTRICT"` (enforcing 1-to-1 patient-user binding; no anonymous profiles).
  - `village_id`: Foreign key to `villages.id` with `ondelete="RESTRICT"`.
- **Validation:** Pydantic v2 validation ensuring `date_of_birth` is not in the future, non-empty language, and optional 10-digit emergency contact phone.
- **Endpoints:**
  - `POST /api/patients`: Registers a profile for the authenticated caller.
  - `GET /api/patients/{id}`: Returns demographic details with nested `Village` object and user identity.

### C. Authentication Integration
- Reuses the main developer's shared JWT authentication dependency `get_current_user` from `app.core.dependencies`.
- Enforces Role-Based Access Control:
  - Role `PATIENT` can only view their own profile.
  - Roles `ASHA`, `DOCTOR`, `STAFF`, `ADMIN` can view patient profiles.
  - Unauthenticated requests are rejected with `401 Unauthorized`.

---

## 2. Running Automated Tests

Run pytest from the repository root:
```bash
pytest -v
```

All 24 test cases (13 foundation + 11 patient & village) pass with 100% success.
