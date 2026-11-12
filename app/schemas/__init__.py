from app.schemas.shared import *
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
from app.schemas.workflow import (
    RequestDetailOut,
    RecommendationCreateIn,
    AppointmentDetailOut,
    AppointmentCancelOut,
)
from app.schemas.patient_village import (
    VillageOut,
    VillageListOut,
    PatientIn,
    PatientOut,
    PatientDetailOut,
)
from app.schemas.facility import (
    FacilityBase,
    FacilityCreate,
    FacilityResponse,
    FacilityDetailResponse,
    FacilityServiceResponse,
    DoctorSummary,
)
from app.schemas.doctor import (
    DoctorBase,
    DoctorCreate,
    DoctorResponse,
    DoctorLinkUserRequest,
    DoctorScheduleBase,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleDetailResponse,
)
from app.schemas.medicine import MedicineBase, MedicineCreate, MedicineResponse
