"""CareBridge Synthetic Evaluation Data Seeder.

Seeds comprehensive demonstration data for Tamil Nadu and rural health centres:
- Villages (Tiruchengode, Molasi, Rampur, Mohanpur, Anandpur, Sitapur)
- Facilities (UPHC Tiruchengode, CHC Tiruchengode, PHC Molasi, PHC Rampur, CHC Mohanpur, Sub-Centre Anandpur)
- Services (General OPD, Emergency, Maternal Care, Immunization, Pharmacy, Diagnostics)
- Doctors & Verified Schedules (Dr. Anita Sharma, Dr. Rajesh Kumar, Dr. K. Senthil Nathan, Dr. R. Priya, Dr. M. Ganesan)
- Medicines & Availability Belief States (Paracetamol, Amoxicillin, Metformin, ORS Sachet, Cetirizine)
- Demo Users and Patients conforming to DEMO_TEST_DATA.md
"""
import asyncio
from datetime import date, datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.doctor import Doctor, DoctorSchedule
from app.models.facility import Facility, FacilityService
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.stock import FacilityMedicineBelief, StockReport
from app.models.user import User
from app.models.village import Village


async def seed_all_demo_data(db: Optional[AsyncSession] = None) -> bool:
    """Seeds the demonstration database if facilities are empty.
    
    Returns True if seeding occurred, False if data already existed.
    """
    owns_session = False
    if db is None:
        db = AsyncSessionLocal()
        owns_session = True

    try:
        # Check if already seeded
        fac_count = (await db.execute(select(func.count(Facility.id)))).scalar_one()
        if fac_count > 0:
            return False

        # 1. Seed Demo Users
        users_data = [
            ("Patient Community", "9876543203", "PatientPass123", "PATIENT"),
            ("Selvi Murugan", "9876500010", "PatientPass123", "PATIENT"),
            ("Vasanthi ASHA", "9876543202", "AshaPass123", "ASHA"),
            ("Dr. Anita Sharma", "9876543220", "DoctorPass123", "DOCTOR"),
            ("Ramesh PHC Staff", "9876543201", "StaffPass123", "STAFF"),
            ("System Administrator", "9876543204", "AdminPass123", "ADMIN"),
        ]

        users_by_phone = {}
        for name, phone, pwd, role in users_data:
            stmt = select(User).where(User.phone == phone)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                u = User(
                    id=uuid.uuid4(),
                    name=name,
                    phone=phone,
                    password_hash=hash_password(pwd),
                    role=role,
                    is_active=True,
                )
                db.add(u)
                users_by_phone[phone] = u
            else:
                users_by_phone[phone] = existing

        await db.flush()

        # 2. Seed Villages
        villages_raw = [
            {
                "id": uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
                "name": "Tiruchengode",
                "district": "Namakkal",
                "state": "Tamil Nadu",
                "latitude": 11.3800,
                "longitude": 77.8900,
                "is_synthetic": True,
            },
            {
                "id": uuid.UUID("7ca65e12-4211-4899-b1ba-1d892e54fca1"),
                "name": "Molasi",
                "district": "Namakkal",
                "state": "Tamil Nadu",
                "latitude": 11.3420,
                "longitude": 77.8450,
                "is_synthetic": True,
            },
            {
                "id": uuid.UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"),
                "name": "Rampur",
                "district": "Vellore",
                "state": "Tamil Nadu",
                "latitude": 12.9165,
                "longitude": 79.1325,
                "is_synthetic": True,
            },
            {
                "id": uuid.UUID("b2c3d4e5-f6a7-4b6c-9d0e-1f2a3b4c5d6e"),
                "name": "Mohanpur",
                "district": "Vellore",
                "state": "Tamil Nadu",
                "latitude": 12.9240,
                "longitude": 79.1450,
                "is_synthetic": True,
            },
            {
                "id": uuid.UUID("c3d4e5f6-a7b8-4c7d-0e1f-2a3b4c5d6e7f"),
                "name": "Anandpur",
                "district": "Tiruvannamalai",
                "state": "Tamil Nadu",
                "latitude": 12.2253,
                "longitude": 79.0747,
                "is_synthetic": True,
            },
            {
                "id": uuid.UUID("d4e5f6a7-b8c9-4d8e-1f2a-3b4c5d6e7f8a"),
                "name": "Sitapur",
                "district": "Sitapur",
                "state": "Uttar Pradesh",
                "latitude": 27.5684,
                "longitude": 80.6791,
                "is_synthetic": True,
            },
        ]

        villages_by_name = {}
        for vdata in villages_raw:
            stmt = select(Village).where(Village.name == vdata["name"])
            existing_v = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_v:
                v = Village(**vdata)
                db.add(v)
                villages_by_name[vdata["name"]] = v
            else:
                villages_by_name[vdata["name"]] = existing_v

        await db.flush()

        # 3. Seed Patients linked to Villages
        p1_user = users_by_phone.get("9876543203")
        p2_user = users_by_phone.get("9876500010")
        tiruchengode_v = villages_by_name.get("Tiruchengode") or villages_by_name.get("Rampur")

        if p1_user and tiruchengode_v:
            stmt = select(Patient).where(Patient.user_id == p1_user.id)
            if not (await db.execute(stmt)).scalar_one_or_none():
                p1 = Patient(
                    id=uuid.uuid4(),
                    user_id=p1_user.id,
                    village_id=tiruchengode_v.id,
                    date_of_birth=date(1990, 5, 15),
                    preferred_language="ta",
                    consent_given=True,
                    emergency_contact_phone="9876543202",
                )
                db.add(p1)

        if p2_user and tiruchengode_v:
            stmt = select(Patient).where(Patient.user_id == p2_user.id)
            if not (await db.execute(stmt)).scalar_one_or_none():
                p2 = Patient(
                    id=uuid.uuid4(),
                    user_id=p2_user.id,
                    village_id=tiruchengode_v.id,
                    date_of_birth=date(1998, 8, 22),
                    preferred_language="ta",
                    consent_given=False,
                    emergency_contact_phone="9876500011",
                )
                db.add(p2)

        await db.flush()

        # 4. Seed Medicines
        medicines_data = [
            ("Paracetamol", "Paracetamol IP", "500 mg", "Tablet"),
            ("Amoxicillin", "Amoxicillin Trihydrate", "500 mg", "Capsule"),
            ("Metformin", "Metformin HCl", "500 mg", "Tablet"),
            ("ORS Sachet", "Oral Rehydration Salts", "21.8 g", "Powder"),
            ("Cetirizine", "Cetirizine HCl", "10 mg", "Tablet"),
            ("Amlodipine", "Amlodipine Besylate", "5 mg", "Tablet"),
        ]

        medicines_by_name = {}
        for mname, gname, strength, form in medicines_data:
            stmt = select(Medicine).where(Medicine.name == mname)
            existing_m = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_m:
                m = Medicine(
                    id=uuid.uuid4(),
                    name=mname,
                    generic_name=gname,
                    strength=strength,
                    dosage_form=form,
                )
                db.add(m)
                medicines_by_name[mname] = m
            else:
                medicines_by_name[mname] = existing_m

        await db.flush()

        # 5. Seed Facilities
        facilities_raw = [
            {
                "name": "UPHC Tiruchengode",
                "facility_type": "PHC",
                "address": "Near Old Bus Stand, Tiruchengode, Namakkal District, Tamil Nadu - 637211",
                "village_id": villages_by_name["Tiruchengode"].id,
                "latitude": 11.3812,
                "longitude": 77.8934,
                "contact_details": {"phone": "04288-252100", "emergency": "108"},
                "services": ["General OPD", "Maternal Care", "Immunization", "Diagnostic Lab", "Essential Medicines"],
            },
            {
                "name": "CHC Tiruchengode",
                "facility_type": "CHC",
                "address": "Sankari Main Road, Tiruchengode, Namakkal District, Tamil Nadu - 637211",
                "village_id": villages_by_name["Tiruchengode"].id,
                "latitude": 11.3785,
                "longitude": 77.8960,
                "contact_details": {"phone": "04288-252200", "emergency": "108"},
                "services": ["Emergency 24x7", "Inpatient Ward", "Surgery", "General Medicine", "Pediatrics", "Diagnostic Lab"],
            },
            {
                "name": "PHC Molasi",
                "facility_type": "PHC",
                "address": "Main Road, Molasi, Tiruchengode Taluk, Namakkal District, Tamil Nadu - 637212",
                "village_id": villages_by_name["Molasi"].id,
                "latitude": 11.3420,
                "longitude": 77.8450,
                "contact_details": {"phone": "04288-261300"},
                "services": ["General OPD", "Maternal Care", "Immunization", "Pharmacy Refill"],
            },
            {
                "name": "PHC Rampur",
                "facility_type": "PHC",
                "address": "Near Rampur Bus Stand, Rampur, Vellore District, Tamil Nadu - 632001",
                "village_id": villages_by_name["Rampur"].id,
                "latitude": 12.9170,
                "longitude": 79.1330,
                "contact_details": {"phone": "0416-2244111"},
                "services": ["Maternal Care", "Immunization", "General Outpatient", "Essential Medicines"],
            },
            {
                "name": "CHC Mohanpur",
                "facility_type": "CHC",
                "address": "Main Road, Mohanpur, Vellore District, Tamil Nadu - 632002",
                "village_id": villages_by_name["Mohanpur"].id,
                "latitude": 12.9250,
                "longitude": 79.1460,
                "contact_details": {"phone": "0416-2244222"},
                "services": ["Emergency First Aid", "Inpatient Ward", "Diagnostics", "Pediatric Care"],
            },
            {
                "name": "Sub-Centre Anandpur",
                "facility_type": "PHC",
                "address": "Village Square, Anandpur, Tiruvannamalai District, Tamil Nadu - 606601",
                "village_id": villages_by_name["Anandpur"].id,
                "latitude": 12.2260,
                "longitude": 79.0750,
                "contact_details": {"phone": "04175-223300"},
                "services": ["First Aid", "Blood Pressure Screening", "Antenatal Checkup"],
            },
        ]

        facilities_by_name = {}
        for fraw in facilities_raw:
            services_list = fraw.pop("services")
            fac = Facility(id=uuid.uuid4(), **fraw)
            db.add(fac)
            facilities_by_name[fac.name] = fac
            for sname in services_list:
                db.add(FacilityService(
                    id=uuid.uuid4(),
                    facility_id=fac.id,
                    service_name=sname,
                    description=f"{sname} facility service",
                ))

        await db.flush()

        # 6. Seed Doctors and Verified Today's Schedules
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        doctors_data = [
            {
                "facility_name": "UPHC Tiruchengode",
                "name": "Dr. K. Senthil Nathan",
                "specialization": "General Medicine",
                "qualification": "MBBS",
                "contact_phone": "9876543250",
                "attendance_status": "PRESENT",
                "start_time": "08:30",
                "end_time": "14:00",
                "notes": "Verified present via biometrics check-in at 08:35",
            },
            {
                "facility_name": "CHC Tiruchengode",
                "name": "Dr. R. Priya",
                "specialization": "Pediatrics & General Medicine",
                "qualification": "MD (Pediatrics)",
                "contact_phone": "9876543251",
                "attendance_status": "PRESENT",
                "start_time": "09:00",
                "end_time": "16:00",
                "notes": "Verified present on duty in OPD",
            },
            {
                "facility_name": "PHC Molasi",
                "name": "Dr. M. Ganesan",
                "specialization": "General Physician",
                "qualification": "MBBS",
                "contact_phone": "9876543252",
                "attendance_status": "EXPECTED",
                "start_time": "10:00",
                "end_time": "15:00",
                "notes": "Scheduled roster shift; physical check-in pending",
            },
            {
                "facility_name": "PHC Rampur",
                "name": "Dr. Anita Sharma",
                "specialization": "General Medicine & Maternal Care",
                "qualification": "MBBS, DGO",
                "contact_phone": "9876543220",
                "attendance_status": "PRESENT",
                "start_time": "09:00",
                "end_time": "13:00",
                "notes": "Physically verified by doctor check-in",
            },
            {
                "facility_name": "CHC Mohanpur",
                "name": "Dr. Rajesh Kumar",
                "specialization": "Pediatrics & General Medicine",
                "qualification": "MD",
                "contact_phone": "9876543221",
                "attendance_status": "EXPECTED",
                "start_time": "10:00",
                "end_time": "16:00",
                "notes": "Planned roster; physical check-in pending",
            },
        ]

        for ddata in doctors_data:
            fac = facilities_by_name.get(ddata["facility_name"])
            if fac:
                doc = Doctor(
                    id=uuid.uuid4(),
                    facility_id=fac.id,
                    name=ddata["name"],
                    specialization=ddata["specialization"],
                    qualification=ddata["qualification"],
                    contact_phone=ddata["contact_phone"],
                )
                db.add(doc)
                await db.flush()

                sched = DoctorSchedule(
                    id=uuid.uuid4(),
                    doctor_id=doc.id,
                    facility_id=fac.id,
                    schedule_date=today,
                    start_time=ddata["start_time"],
                    end_time=ddata["end_time"],
                    attendance_status=ddata["attendance_status"],
                    last_verified_at=now_utc if ddata["attendance_status"] == "PRESENT" else None,
                    notes=ddata["notes"],
                )
                db.add(sched)

        await db.flush()

        # 7. Seed Medicine Belief States & Probabilities
        beliefs_data = [
            # Tiruchengode facilities
            ("UPHC Tiruchengode", "Paracetamol", 0.95, 0.92, "LIKELY"),
            ("UPHC Tiruchengode", "Amoxicillin", 0.88, 0.85, "LIKELY"),
            ("UPHC Tiruchengode", "Metformin", 0.82, 0.80, "LIKELY"),
            ("UPHC Tiruchengode", "ORS Sachet", 0.95, 0.95, "LIKELY"),
            ("UPHC Tiruchengode", "Cetirizine", 0.90, 0.88, "LIKELY"),
            ("CHC Tiruchengode", "Paracetamol", 0.92, 0.90, "LIKELY"),
            ("CHC Tiruchengode", "Amoxicillin", 0.85, 0.82, "LIKELY"),
            ("CHC Tiruchengode", "Metformin", 0.90, 0.88, "LIKELY"),
            ("CHC Tiruchengode", "ORS Sachet", 0.98, 0.95, "LIKELY"),
            ("PHC Molasi", "Paracetamol", 0.85, 0.80, "LIKELY"),
            ("PHC Molasi", "Amoxicillin", 0.55, 0.40, "UNCERTAIN"),
            ("PHC Molasi", "ORS Sachet", 0.90, 0.85, "LIKELY"),
            # Rampur / Mohanpur demo data from DEMO_TEST_DATA.md
            ("PHC Rampur", "Paracetamol", 0.92, 0.88, "LIKELY"),
            ("PHC Rampur", "Amoxicillin", 0.55, 0.40, "UNCERTAIN"),
            ("PHC Rampur", "Metformin", 0.20, 0.70, "UNLIKELY"),
            ("PHC Rampur", "ORS Sachet", 0.95, 0.90, "LIKELY"),
            ("CHC Mohanpur", "Paracetamol", 0.85, 0.75, "LIKELY"),
            ("CHC Mohanpur", "Amoxicillin", 0.78, 0.80, "LIKELY"),
            ("CHC Mohanpur", "Metformin", 0.88, 0.82, "LIKELY"),
            ("CHC Mohanpur", "ORS Sachet", 0.95, 0.90, "LIKELY"),
            ("Sub-Centre Anandpur", "Paracetamol", 0.80, 0.70, "LIKELY"),
            ("Sub-Centre Anandpur", "ORS Sachet", 0.90, 0.85, "LIKELY"),
        ]

        staff_user_id = users_by_phone["9876543201"].id

        for fname, mname, p_avail, conf, label in beliefs_data:
            fac = facilities_by_name.get(fname)
            med = medicines_by_name.get(mname)
            if fac and med:
                belief = FacilityMedicineBelief(
                    id=uuid.uuid4(),
                    facility_id=fac.id,
                    medicine_id=med.id,
                    p_available=p_avail,
                    confidence=conf,
                    label=label,
                    evidence_count=3,
                    last_report_at=now_utc,
                )
                db.add(belief)

                # Append-only report ledger entry
                rep = StockReport(
                    id=uuid.uuid4(),
                    facility_id=fac.id,
                    medicine_id=med.id,
                    reporter_id=staff_user_id,
                    source_type="STAFF",
                    availability_status="IN_STOCK" if p_avail >= 0.75 else ("LOW" if p_avail >= 0.4 else "OUT"),
                    verification_status="VERIFIED",
                    reported_at=now_utc,
                    notes=f"Stock inventory check - {label}",
                )
                db.add(rep)

        await db.commit()
        return True

    except Exception:
        await db.rollback()
        raise
    finally:
        if owns_session:
            await db.close()


async def main():
    try:
        did_seed = await seed_all_demo_data()
        print(f"CareBridge demo evaluation data seeded: {did_seed}")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

