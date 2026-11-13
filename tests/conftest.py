from datetime import date, datetime, timezone
from typing import AsyncGenerator, Dict, Any
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.village import Village
from app.models.facility import Facility, FacilityService
from app.models.doctor import Doctor, DoctorSchedule
from app.models.medicine import Medicine
from app.models.stock import FacilityMedicineBelief

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean in-memory database session for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with get_db overridden to use isolated test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session: AsyncSession) -> Dict[str, Any]:
    """Seed synthetic evaluation data for facilities, villages, doctors, and medicines."""
    # Seed Users for different roles
    staff_user = User(
        id=uuid.uuid4(),
        name="Staff Member",
        phone="9876543201",
        password_hash=hash_password("StaffPass123"),
        role="STAFF",
        is_active=True,
    )
    asha_user = User(
        id=uuid.uuid4(),
        name="ASHA Worker",
        phone="9876543202",
        password_hash=hash_password("AshaPass123"),
        role="ASHA",
        is_active=True,
    )
    patient_user = User(
        id=uuid.uuid4(),
        name="Patient Community",
        phone="9876543203",
        password_hash=hash_password("PatientPass123"),
        role="PATIENT",
        is_active=True,
    )
    admin_user = User(
        id=uuid.uuid4(),
        name="System Admin",
        phone="9876543204",
        password_hash=hash_password("AdminPass123"),
        role="ADMIN",
        is_active=True,
    )
    db_session.add_all([staff_user, asha_user, patient_user, admin_user])
    await db_session.flush()

    staff_token = create_access_token({"sub": str(staff_user.id), "role": "STAFF"})
    asha_token = create_access_token({"sub": str(asha_user.id), "role": "ASHA"})
    patient_token = create_access_token({"sub": str(patient_user.id), "role": "PATIENT"})
    admin_token = create_access_token({"sub": str(admin_user.id), "role": "ADMIN"})

    # Seed Villages
    village_1 = Village(
        name="Rampur",
        latitude=12.9716,
        longitude=77.5946,
        district="Rural District",
        state="Karnataka",
    )
    village_2 = Village(
        name="Sitapur",
        latitude=13.0827,
        longitude=77.5877,
        district="Rural District",
        state="Karnataka",
    )
    village_tiruchengode = Village(
        name="Tiruchengode",
        latitude=11.3800,
        longitude=77.8900,
        district="Namakkal",
        state="Tamil Nadu",
    )
    village_coimbatore = Village(
        name="Coimbatore",
        latitude=11.0168,
        longitude=76.9558,
        district="Coimbatore",
        state="Tamil Nadu",
    )
    village_salem = Village(
        name="Salem",
        latitude=11.6643,
        longitude=78.1460,
        district="Salem",
        state="Tamil Nadu",
    )
    db_session.add_all([village_1, village_2, village_tiruchengode, village_coimbatore, village_salem])
    await db_session.flush()

    # Seed Facilities
    fac_1 = Facility(
        name="PHC Rampur",
        facility_type="PHC",
        address="Main Road, Rampur",
        village_id=village_1.id,
        latitude=12.9720,
        longitude=77.5950,
        contact_details={"phone": "9876543210", "email": "phc.rampur@gov.in"},
    )
    fac_2 = Facility(
        name="CHC Sitapur",
        facility_type="CHC",
        address="Hospital Circle, Sitapur",
        village_id=village_2.id,
        latitude=13.0800,
        longitude=77.5850,
        contact_details={"phone": "9876543211", "email": "chc.sitapur@gov.in"},
    )
    fac_3 = Facility(
        name="City General Hospital",
        facility_type="HOSPITAL",
        address="Central Ring Road",
        village_id=village_1.id,
        latitude=12.9800,
        longitude=77.6000,
        contact_details={"phone": "9876543212"},
    )
    fac_tiruchengode = Facility(
        name="UPHC Tiruchengode",
        facility_type="PHC",
        address="Near Old Bus Stand, Tiruchengode, Namakkal District, Tamil Nadu",
        village_id=village_tiruchengode.id,
        latitude=11.3812,
        longitude=77.8934,
        contact_details={"phone": "04288-252100", "emergency": "108"},
    )
    fac_coimbatore = Facility(
        name="UPHC Singanallur, Coimbatore",
        facility_type="PHC",
        address="Trichy Road, Singanallur, Coimbatore, Tamil Nadu - 641005",
        village_id=village_coimbatore.id,
        latitude=11.0020,
        longitude=77.0260,
        contact_details={"phone": "0422-2578100", "emergency": "108"},
    )
    fac_salem = Facility(
        name="UPHC Shevapet, Salem",
        facility_type="PHC",
        address="Main Road, Shevapet, Salem, Tamil Nadu - 636002",
        village_id=village_salem.id,
        latitude=11.6580,
        longitude=78.1420,
        contact_details={"phone": "0427-2211200", "emergency": "108"},
    )
    db_session.add_all([fac_1, fac_2, fac_3, fac_tiruchengode, fac_coimbatore, fac_salem])
    await db_session.flush()

    # Seed Facility Services
    s1 = FacilityService(facility_id=fac_1.id, service_name="Maternal Care", description="Basic maternal care")
    s2 = FacilityService(facility_id=fac_1.id, service_name="Immunization", description="Routine child vaccination")
    s3 = FacilityService(facility_id=fac_2.id, service_name="Emergency", description="24/7 trauma & emergency")
    s4 = FacilityService(facility_id=fac_2.id, service_name="Immunization", description="Routine vaccination")
    s5 = FacilityService(facility_id=fac_3.id, service_name="Surgery", description="General surgery")
    db_session.add_all([s1, s2, s3, s4, s5])
    await db_session.flush()

    # Seed Doctors
    doc_1 = Doctor(
        facility_id=fac_1.id,
        name="Dr. Anita Sharma",
        specialization="General Medicine",
        qualification="MBBS",
        contact_phone="9876543220",
    )
    doc_2 = Doctor(
        facility_id=fac_2.id,
        name="Dr. Rajesh Kumar",
        specialization="Pediatrics",
        qualification="MD",
        contact_phone="9876543221",
    )
    doc_tiru = Doctor(
        facility_id=fac_tiruchengode.id,
        name="Dr. K. Senthil Nathan",
        specialization="General Medicine",
        qualification="MBBS",
        contact_phone="9876543250",
    )
    doc_cbe = Doctor(
        facility_id=fac_coimbatore.id,
        name="Dr. S. Venkatesh",
        specialization="General Medicine",
        qualification="MBBS, MD",
        contact_phone="9876543260",
    )
    doc_salem = Doctor(
        facility_id=fac_salem.id,
        name="Dr. N. Gayathri",
        specialization="General Medicine & Family Health",
        qualification="MBBS",
        contact_phone="9876543261",
    )
    db_session.add_all([doc_1, doc_2, doc_tiru, doc_cbe, doc_salem])
    await db_session.flush()

    # Seed Schedules
    today = date.today()
    sched_1 = DoctorSchedule(
        doctor_id=doc_1.id,
        facility_id=fac_1.id,
        schedule_date=today,
        start_time="09:00",
        end_time="17:00",
        attendance_status="EXPECTED",
        notes="Regular shift",
    )
    sched_2 = DoctorSchedule(
        doctor_id=doc_2.id,
        facility_id=fac_2.id,
        schedule_date=today,
        start_time="10:00",
        end_time="16:00",
        attendance_status="PRESENT",
        last_verified_at=datetime.now(timezone.utc),
        notes="Verified present at 10:05",
    )
    sched_tiru = DoctorSchedule(
        doctor_id=doc_tiru.id,
        facility_id=fac_tiruchengode.id,
        schedule_date=today,
        start_time="08:30",
        end_time="14:00",
        attendance_status="PRESENT",
        last_verified_at=datetime.now(timezone.utc),
        notes="Verified present in Tiruchengode",
    )
    sched_cbe = DoctorSchedule(
        doctor_id=doc_cbe.id,
        facility_id=fac_coimbatore.id,
        schedule_date=today,
        start_time="08:30",
        end_time="14:30",
        attendance_status="PRESENT",
        last_verified_at=datetime.now(timezone.utc),
        notes="Verified present in Coimbatore",
    )
    sched_salem = DoctorSchedule(
        doctor_id=doc_salem.id,
        facility_id=fac_salem.id,
        schedule_date=today,
        start_time="09:00",
        end_time="15:00",
        attendance_status="PRESENT",
        last_verified_at=datetime.now(timezone.utc),
        notes="Verified present in Salem",
    )
    db_session.add_all([sched_1, sched_2, sched_tiru, sched_cbe, sched_salem])
    await db_session.flush()

    # Seed Medicines
    med_1 = Medicine(
        name="Paracetamol",
        generic_name="Acetaminophen",
        strength="500 mg",
        dosage_form="Tablet",
    )
    med_2 = Medicine(
        name="Amoxicillin",
        generic_name="Amoxicillin Trihydrate",
        strength="250 mg",
        dosage_form="Capsule",
    )
    med_3 = Medicine(
        name="ORS Sachet",
        generic_name="Oral Rehydration Salts",
        strength="21.8 g",
        dosage_form="Powder",
    )
    db_session.add_all([med_1, med_2, med_3])
    await db_session.flush()

    # Seed beliefs for testing
    b1 = FacilityMedicineBelief(
        facility_id=fac_tiruchengode.id,
        medicine_id=med_1.id,
        p_available=0.95,
        confidence=0.92,
        label="LIKELY",
    )
    b2 = FacilityMedicineBelief(
        facility_id=fac_coimbatore.id,
        medicine_id=med_1.id,
        p_available=0.95,
        confidence=0.90,
        label="LIKELY",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    return {
        "users": {
            "staff": staff_user,
            "asha": asha_user,
            "patient": patient_user,
            "admin": admin_user,
        },
        "tokens": {
            "staff": staff_token,
            "asha": asha_token,
            "patient": patient_token,
            "admin": admin_token,
        },
        "headers": {
            "staff": {"Authorization": f"Bearer {staff_token}"},
            "asha": {"Authorization": f"Bearer {asha_token}"},
            "patient": {"Authorization": f"Bearer {patient_token}"},
            "admin": {"Authorization": f"Bearer {admin_token}"},
        },
        "villages": [village_1, village_2],
        "facilities": [fac_1, fac_2, fac_3],
        "doctors": [doc_1, doc_2],
        "schedules": [sched_1, sched_2],
        "medicines": [med_1, med_2, med_3],
    }
