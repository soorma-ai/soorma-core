"""API v1 router."""

from fastapi import APIRouter
from memory_service.api.v1 import semantic, episodic, procedural, working

# Create main v1 router
router = APIRouter(prefix="/v1/memory")

# Include sub-routers
router.include_router(semantic.router)
router.include_router(episodic.router)
router.include_router(procedural.router)
router.include_router(working.router)
