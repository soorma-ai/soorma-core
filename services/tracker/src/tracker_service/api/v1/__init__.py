"""API v1 routes package."""

from fastapi import APIRouter

from tracker_service.api.v1 import admin, query

router = APIRouter(prefix="/v1")
router.include_router(query.router)
router.include_router(admin.router)

__all__ = ["router"]
