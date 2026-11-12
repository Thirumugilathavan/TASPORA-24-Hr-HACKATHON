# NALAM AI — Demonstration & Evaluation Test Data

This document catalogues all fictional accounts, test facilities, villages, and medicine data prepared for the NALAM AI hackathon demonstration.

> **Data Disclosure:** All personal names, phone numbers, facility inventories, and GPS coordinates listed below are synthetic placeholders generated exclusively for demonstration and software testing.

---

## 1. Demo User Accounts

All test accounts share standard evaluation passwords for rapid judge testing:

| Role | Name | Phone Number | Password | Default Language | Consent Given |
|---|---|---|---|---|---|
| **PATIENT** | Patient Community (Demo) | `9876543203` | `PatientPass123` | `ta` (Tamil) | `true` |
| **PATIENT (New)** | Selvi Murugan | `9876500010` | `PatientPass123` | `ta` (Tamil) | `false` (Unconsented) |
| **ASHA Worker** | Vasanthi ASHA | `9876543202` | `AshaPass123` | `ta` (Tamil) | N/A |
| **DOCTOR** | Dr. Anita Sharma | `9876543220` | `DoctorPass123` | `ta` (Tamil) | N/A |
| **STAFF** | Ramesh PHC Staff | `9876543201` | `StaffPass123` | `en` (English) | N/A |
| **ADMIN** | System Administrator | `9876543204` | `AdminPass123` | `en` (English) | N/A |

---

## 2. Seeded Villages Directory

| Village Name | District | State | Latitude | Longitude | Synthetic Tag |
|---|---|---|---|---|---|
| **Rampur** | Vellore | Tamil Nadu | `12.9165` | `79.1325` | `is_synthetic: true` |
| **Mohanpur** | Vellore | Tamil Nadu | `12.9240` | `79.1450` | `is_synthetic: true` |
| **Anandpur** | Tiruvannamalai | Tamil Nadu | `12.2253` | `79.0747` | `is_synthetic: true` |

---

## 3. Healthcare Facilities & Doctor Schedules

### Facility 1: Primary Health Centre (PHC) Rampur
- **Facility Type:** `PHC`
- **Location:** Near Rampur Bus Stand, Rampur (`12.9170`, `79.1330`)
- **Offered Services:** Maternal Care, Immunization, General Outpatient, Essential Medicines
- **Assigned Doctor:** Dr. Anita Sharma (MBBS, DGO)
  - Today's Schedule: `09:00:00` – `13:00:00`
  - Attendance Status: `PRESENT` (Physically verified by doctor check-in)

### Facility 2: Community Health Centre (CHC) Mohanpur
- **Facility Type:** `CHC`
- **Location:** Main Road, Mohanpur (`12.9250`, `79.1460`)
- **Offered Services:** Emergency First Aid, Inpatient Ward, Diagnostics, Pediatric Care
- **Assigned Doctor:** Dr. Rajesh Kumar (MD, General Medicine)
  - Today's Schedule: `10:00:00` – `16:00:00`
  - Attendance Status: `EXPECTED` (Planned roster; physical check-in pending)

### Facility 3: Sub-Centre Anandpur
- **Facility Type:** `PHC` (Sub-centre)
- **Location:** Village Square, Anandpur (`12.2260`, `79.0750`)
- **Offered Services:** First Aid, Blood Pressure Screening, Antenatal Checkup
- **Staffing:** Auxiliary Nurse Midwife (ANM) / ASHA Worker on duty

---

## 4. Medicine Catalogue & Stock Availability Beliefs

| Medicine Name | Generic Name | Strength | Dosage Form | PHC Rampur Stock | CHC Mohanpur Stock |
|---|---|---|---|---|---|
| **Paracetamol** | Paracetamol IP | `500 mg` | Tablet | `LIKELY` ($P=0.92$, $c=0.88$) | `LIKELY` ($P=0.85$, $c=0.75$) |
| **Amoxicillin** | Amoxicillin Trihydrate | `500 mg` | Capsule | `UNCERTAIN` ($P=0.55$, $c=0.40$) | `LIKELY` ($P=0.78$, $c=0.80$) |
| **Metformin** | Metformin HCl | `500 mg` | Tablet | `UNLIKELY` ($P=0.20$, $c=0.70$) | `LIKELY` ($P=0.88$, $c=0.82$) |
| **ORS Sachet** | Oral Rehydration Salts | `21.8 g` | Powder | `LIKELY` ($P=0.95$, $c=0.90$) | `LIKELY` ($P=0.95$, $c=0.90$) |

---

## 5. Sample Healthcare Requests & Expected Recommendations

### Sample Request A: Child Fever Consultation
- **Patient:** Patient Community (`9876543203`), Village: Rampur
- **Request Type:** `CONSULTATION`
- **Urgency:** `NORMAL`
- **Top Recommended Facility:** **PHC Rampur**
  - *Distance:* $\approx 0.12\text{ km}$
  - *Doctor Status:* `PRESENT` (Dr. Anita Sharma)
  - *Medicine (Paracetamol):* `LIKELY` ($P=0.92$)
  - *Expected Loss:* Lowest trip failure risk ($0.08 \times \text{Cost}$)

### Sample Request B: Chronic Diabetic Medicine Refill
- **Patient:** Patient Community (`9876543203`), Village: Rampur
- **Request Type:** `REFILL` (Metformin 500mg)
- **Urgency:** `PRIORITY`
- **Top Recommended Facility:** **CHC Mohanpur**
  - *Why not PHC Rampur?* PHC Rampur is closer, but Metformin stock is `UNLIKELY` ($P=0.20$). Visiting PHC Rampur has an $80\%$ risk of a wasted trip.
  - *Recommendation:* CHC Mohanpur ($\approx 2.1\text{ km}$, Metformin `LIKELY`) is recommended to prevent a wasted journey.
