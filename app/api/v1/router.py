from fastapi import APIRouter
from app.api.v1.appointments import router as appointments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.requests import router as requests_router

api_router = APIRouter()

# Phase 1 Foundation Routers
api_router.include_router(health_router)
api_router.include_router(auth_router)

# Core Healthcare Workflow Routers
api_router.include_router(requests_router)
api_router.include_router(recommendations_router)
api_router.include_router(appointments_router)
