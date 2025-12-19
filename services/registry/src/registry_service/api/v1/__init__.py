"""
API v1 router configuration.
"""
from fastapi import APIRouter
from .events import router as events_router
from .agents import router as agents_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(events_router)
router.include_router(agents_router)
