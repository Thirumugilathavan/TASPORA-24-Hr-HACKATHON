from fastapi import APIRouter
from app.api.v1.appointments import router as appointments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.facilities import router as facilities_router, healthcare_router
from app.api.v1.health import router as health_router
from app.api.v1.medicines import router as medicines_router
from app.api.v1.patients import router as patients_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.requests import router as requests_router
from app.api.v1.stock import router as stock_router
from app.api.v1.villages import router as villages_router
from app.api.v1.ivr import router as ivr_router
from app.api.v1.ai import router as ai_router

api_router = APIRouter()

# Phase 1 Foundation Routers
api_router.include_router(health_router)
api_router.include_router(auth_router)

# Member 1: Patient and Village Routers
api_router.include_router(villages_router)
api_router.include_router(patients_router)

# Member 2: Facility, Doctor, Medicine, and Stock Routers
api_router.include_router(facilities_router)
api_router.include_router(healthcare_router)
api_router.include_router(doctors_router)
api_router.include_router(medicines_router)
api_router.include_router(stock_router)

# Core Healthcare Workflow Routers
api_router.include_router(requests_router)
api_router.include_router(recommendations_router)
api_router.include_router(appointments_router)

# CareBridge Voice Access: IVR & Feature Phone Router
api_router.include_router(ivr_router)

# CareBridge AI Assistant & Multimodal Voice Router
api_router.include_router(ai_router)
