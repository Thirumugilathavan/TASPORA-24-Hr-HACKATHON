from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.facilities import router as facilities_router
from app.api.v1.health import router as health_router
from app.api.v1.medicines import router as medicines_router
from app.api.v1.stock import router as stock_router

api_router = APIRouter()

# Phase 1 & Module routers
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(facilities_router)
api_router.include_router(doctors_router)
api_router.include_router(medicines_router)
api_router.include_router(stock_router)
