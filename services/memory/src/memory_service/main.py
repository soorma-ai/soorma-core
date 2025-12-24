"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from memory_service import __version__
from memory_service.core.config import settings
from memory_service.core.middleware import TenancyMiddleware
from memory_service.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    print(f"Starting Memory Service v{__version__}")
    print(f"Local testing mode: {settings.is_local_testing}")
    print(f"Database URL: {settings.database_url}")

    yield

    # Shutdown
    print("Shutting down Memory Service")


# Create FastAPI app
app = FastAPI(
    title="Soorma Memory Service",
    description="Persistent memory layer for autonomous agents (CoALA framework)",
    version=__version__,
    docs_url="/docs" if not settings.is_prod else None,
    redoc_url="/redoc" if not settings.is_prod else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenancy middleware
app.add_middleware(TenancyMiddleware)

# Include API routes
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": __version__,
        "local_testing": settings.is_local_testing,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "memory_service.main:app",
        host="0.0.0.0",
        port=8002,
        reload=not settings.is_prod,
    )
