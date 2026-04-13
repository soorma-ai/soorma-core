"""Discovery and JWKS publication endpoints."""

from fastapi import APIRouter, Request

from identity_service.services.provider_facade import provider_facade


router = APIRouter(prefix="/.well-known", tags=["Discovery"])


@router.get("/openid-configuration")
async def openid_configuration(request: Request):
    """Return minimal discovery metadata for verifier clients."""
    service_base_url = str(request.base_url).rstrip("/")
    return provider_facade.get_openid_configuration(service_base_url)


@router.get("/jwks.json")
async def jwks_document():
    """Return JSON Web Key Set for identity-service verifier discovery."""
    return provider_facade.get_jwks()
