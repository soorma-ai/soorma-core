"""Main FastAPI application for Identity Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from soorma_service_common import TenancyMiddleware, configure_platform_tenant_openapi

from identity_service import __version__
from identity_service.core.config import settings
from identity_service.core.db import close_db, init_db
from identity_service.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    print(f"Starting Identity Service v{__version__}")
    await init_db()
    try:
        yield
    finally:
        await close_db()
        print("Shutting down Identity Service")


app = FastAPI(
    title="Soorma Identity Service",
    description="Identity domain service for platform-tenant onboarding and trust policies",
    version=__version__,
    docs_url="/docs" if not settings.is_prod else None,
    redoc_url="/redoc" if not settings.is_prod else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenancyMiddleware)
configure_platform_tenant_openapi(
    app,
    include_paths={
        "/v1/identity/tenant-admin-credentials/rotate",
        "/v1/identity/principals",
        "/v1/identity/principals/{principal_id}",
        "/v1/identity/principals/{principal_id}/revoke",
        "/v1/identity/tokens/issue",
        "/v1/identity/delegated-issuers",
        "/v1/identity/delegated-issuers/{delegated_issuer_id}",
        "/v1/identity/mappings/evaluate",
    },
    add_global_security=False,
)
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": __version__,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "identity_service.main:app",
        host="0.0.0.0",
        port=8085,
        reload=not settings.is_prod,
    )
