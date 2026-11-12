from app.schemas.shared import *
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
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
    DoctorScheduleBase,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleDetailResponse,
)
from app.schemas.medicine import MedicineBase, MedicineCreate, MedicineResponse
