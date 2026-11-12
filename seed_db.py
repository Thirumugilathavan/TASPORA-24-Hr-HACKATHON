import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.doctor import Doctor, DoctorSchedule
from app.models.facility import Facility, FacilityService
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.stock import FacilityMedicineBelief, StockReport
from app.models.user import User
from app.models.village import Village


async def seed():
    async with AsyncSessionLocal() as db:
        # 1. Seed Villages from seed_data/villages.json
        villages_json_path = os.path.join(os.path.dirname(__file__), "seed_data", "villages.json")
        with open(villages_json_path, "r", encoding="utf-8") as f:
            villages_data = json.load(f)

        village_map = {}
        for v_data in villages_data:
            v_id = uuid.UUID(v_data["id"])
            stmt = select(Village).where(Village.id == v_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                village = Village(
                    id=v_id,
                    name=v_data["name"],
                    district=v_data["district"],
                    latitude=float(v_data["latitude"]),
                    longitude=float(v_data["longitude"]),
                    is_synthetic=v_data.get("is_synthetic", True),
                )
                db.add(village)
                village_map[v_data["name"]] = village
            else:
                village_map[v_data["name"]] = existing

        await db.flush()
        print(f"Seeded {len(villages_data)} villages.")

        # Rampur village is our default anchor
        rampur_village = village_map.get("Rampur")
        maholi_village = village_map.get("Maholi") or rampur_village

        # 2. Seed Facilities
        facilities_data = [
            {
                "id": uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afb1"),
                "name": "Primary Health Centre (PHC) Rampur",
                "facility_type": "PHC",
                "address": "Near Panchayat Bhawan, Main Road, Rampur",
                "village_id": rampur_village.id,
                "latitude": 27.5690,
                "longitude": 80.6800,
                "contact_details": {"phone": "9876543210", "email": "phc.rampur@gov.in"},
                "services": ["General Outpatient", "Maternal Care", "Immunization", "Essential Drug Dispensing"],
            },
            {
                "id": uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afb2"),
                "name": "Community Health Centre (CHC) Maholi",
                "facility_type": "CHC",
                "address": "Highway Crossing, Tehsil Road, Maholi",
                "village_id": maholi_village.id,
                "latitude": 27.6660,
                "longitude": 80.4730,
                "contact_details": {"phone": "9876543211", "email": "chc.maholi@gov.in"},
                "services": ["24/7 Emergency", "Inpatient Ward", "Pediatrics", "Obstetrics & Gynecology", "Diagnostic Lab"],
            },
            {
                "id": uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afb3"),
                "name": "Sitapur District Hospital",
                "facility_type": "HOSPITAL",
                "address": "Hospital Road, Civil Lines, Sitapur",
                "village_id": rampur_village.id,
                "latitude": 27.5700,
                "longitude": 80.6850,
                "contact_details": {"phone": "9876543212"},
                "services": ["Specialist OPD", "Surgery", "Cardiology", "ICU", "Blood Bank", "Advanced Diagnostics"],
            },
            {
                "id": uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afb4"),
                "name": "Jan Aushadhi Kendra (Pharmacy) Rampur",
                "facility_type": "PHARMACY",
                "address": "Bazaar Chowk, Rampur",
                "village_id": rampur_village.id,
                "latitude": 27.5680,
                "longitude": 80.6780,
                "contact_details": {"phone": "9876543213"},
                "services": ["Essential Drug Dispensing", "Generic Medicines"],
            },
        ]

        fac_map = {}
        for f_info in facilities_data:
            stmt = select(Facility).where(Facility.id == f_info["id"])
            existing_fac = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_fac:
                fac = Facility(
                    id=f_info["id"],
                    name=f_info["name"],
                    facility_type=f_info["facility_type"],
                    address=f_info["address"],
                    village_id=f_info["village_id"],
                    latitude=f_info["latitude"],
                    longitude=f_info["longitude"],
                    contact_details=f_info["contact_details"],
                )
                db.add(fac)
                await db.flush()
                for s_name in f_info["services"]:
                    service = FacilityService(
                        facility_id=fac.id,
                        service_name=s_name,
                        description=f"{s_name} provided at {fac.name}",
                    )
                    db.add(service)
                fac_map[f_info["name"]] = fac
            else:
                fac_map[f_info["name"]] = existing_fac

        await db.flush()
        print("Seeded facilities and facility services.")

        # 3. Seed Medicines
        meds_data = [
            ("Paracetamol", "Acetaminophen", "500 mg", "Tablet", "Analgesic & Antipyretic"),
            ("Amoxicillin", "Amoxicillin Trihydrate", "250 mg", "Capsule", "Broad-spectrum Antibiotic"),
            ("Metformin", "Metformin Hydrochloride", "500 mg", "Tablet", "Anti-diabetic"),
            ("ORS Sachet", "Oral Rehydration Salts", "21.8 g", "Powder", "Electrolyte Replacement"),
            ("Ciprofloxacin", "Ciprofloxacin", "500 mg", "Tablet", "Antibiotic"),
            ("Cetirizine", "Cetirizine Dihydrochloride", "10 mg", "Tablet", "Antihistamine"),
            ("Azithromycin", "Azithromycin", "500 mg", "Tablet", "Antibiotic"),
        ]

        med_map = {}
        for name, generic, strength, form, category in meds_data:
            stmt = select(Medicine).where(Medicine.name == name)
            existing_med = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_med:
                med = Medicine(
                    name=name,
                    generic_name=generic,
                    strength=strength,
                    dosage_form=form,
                )
                db.add(med)
                await db.flush()
                med_map[name] = med
            else:
                med_map[name] = existing_med

        await db.flush()
        print("Seeded medicines.")

        # 4. Seed Stock Reports and Beliefs
        phc_rampur = fac_map.get("Primary Health Centre (PHC) Rampur")
        if phc_rampur:
            for med_name, med in med_map.items():
                stmt = select(FacilityMedicineBelief).where(
                    FacilityMedicineBelief.facility_id == phc_rampur.id,
                    FacilityMedicineBelief.medicine_id == med.id,
                )
                existing_belief = (await db.execute(stmt)).scalar_one_or_none()
                if not existing_belief:
                    belief = FacilityMedicineBelief(
                        facility_id=phc_rampur.id,
                        medicine_id=med.id,
                        p_available=0.85 if "Paracetamol" in med_name or "ORS" in med_name else 0.50,
                        confidence=0.75,
                        label="LIKELY" if "Paracetamol" in med_name or "ORS" in med_name else "UNCERTAIN",
                        evidence_count=2,
                        last_report_at=datetime.now(timezone.utc),
                    )
                    db.add(belief)

        await db.flush()
        print("Seeded stock beliefs.")

        # 5. Seed Users & Patients
        demo_users = [
            ("9876543210", "Sunita Devi", "PATIENT", "PatientPass123"),
            ("9876543203", "Ramesh Kumar", "PATIENT", "PatientPass123"),
            ("9876543202", "Kavita Sharma", "ASHA", "AshaPass123"),
            ("9876543201", "Dr. Manoj Verma", "STAFF", "StaffPass123"),
            ("9876543200", "Admin User", "ADMIN", "AdminPass123"),
            ("9876543220", "Dr. Anita Sharma", "DOCTOR", "DoctorPass123"),
        ]

        for phone, name, role, plain_pass in demo_users:
            stmt = select(User).where(User.phone == phone)
            existing_user = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_user:
                u = User(
                    phone=phone,
                    name=name,
                    role=role,
                    password_hash=hash_password(plain_pass),
                    is_active=True,
                )
                db.add(u)
                await db.flush()

                if role == "PATIENT":
                    p = Patient(
                        user_id=u.id,
                        village_id=rampur_village.id,
                        date_of_birth=date(1992, 8, 15),
                        preferred_language="ta" if phone == "9876543203" else "en",
                        consent_given=True,
                        emergency_contact_phone="9876543219",
                    )
                    db.add(p)
                elif role == "DOCTOR" and phc_rampur:
                    d = Doctor(
                        facility_id=phc_rampur.id,
                        name=name,
                        specialization="General Medicine",
                        qualification="MBBS",
                        contact_phone=phone,
                        user_id=u.id,
                    )
                    db.add(d)
                    await db.flush()
                    sched = DoctorSchedule(
                        doctor_id=d.id,
                        facility_id=phc_rampur.id,
                        schedule_date=date.today(),
                        start_time="09:00",
                        end_time="17:00",
                        attendance_status="PRESENT",
                        last_verified_at=datetime.now(timezone.utc),
                        notes="On duty today",
                    )
                    db.add(sched)

        await db.commit()
        print("CareBridge database successfully seeded with villages, facilities, doctors, medicines, and demo users!")


if __name__ == "__main__":
    asyncio.run(seed())
