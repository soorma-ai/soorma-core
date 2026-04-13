"""v1 API routes."""

from fastapi import APIRouter

from identity_service.api.v1 import (
    delegated_issuers,
    discovery,
    mappings,
    onboarding,
    principals,
    tokens,
)

router = APIRouter(prefix="/v1/identity")
router.include_router(discovery.router)
router.include_router(onboarding.router)
router.include_router(principals.router)
router.include_router(tokens.router)
router.include_router(delegated_issuers.router)
router.include_router(mappings.router)
