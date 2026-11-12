from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.patients import router as patients_router
from app.api.v1.villages import router as villages_router

api_router = APIRouter()

# Mount Phase 1 routers
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(villages_router)
api_router.include_router(patients_router)
