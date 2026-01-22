"""API v1 router."""

from fastapi import APIRouter
from memory_service.api.v1 import (
    semantic,
    episodic,
    procedural,
    working,
    task_context,
    plan_context,
    plans,
    sessions,
)

# Create main v1 router
router = APIRouter(prefix="/v1/memory")

# Include sub-routers
router.include_router(semantic.router)
router.include_router(episodic.router)
router.include_router(procedural.router)
router.include_router(working.router)
router.include_router(task_context.router)
router.include_router(plan_context.router)
router.include_router(plans.router)
router.include_router(sessions.router)
