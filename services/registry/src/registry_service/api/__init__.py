"""
API router configuration.
"""
from fastapi import APIRouter
from .v1 import router as v1_router

# Create main API router
router = APIRouter()

# Include version routers
router.include_router(v1_router)
