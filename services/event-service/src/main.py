"""
Event Service - Main FastAPI Application

This service acts as a smart proxy/gateway between Soorma agents and the
underlying message bus (NATS, Kafka, Google Pub/Sub).

Key Features:
- REST API for publishing events
- Server-Sent Events (SSE) for real-time event streaming
- Adapter pattern for backend flexibility
- CloudEvents-compliant event format
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .services.event_manager import event_manager
from .api.routes import events, health, admin

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup (connect to message bus) and shutdown (cleanup).
    """
    # Startup
    await event_manager.initialize()
    
    yield
    
    # Shutdown
    await event_manager.shutdown()


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Soorma Event Service",
    description="Event proxy/gateway for the Soorma DisCo platform",
    version="0.6.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(events.router, prefix="/v1/events")
app.include_router(admin.router, prefix="/v1/admin")


@app.get("/", tags=["Info"])
async def root() -> Dict[str, str]:
    """Root endpoint with service info."""
    return {
        "service": "soorma-event-service",
        "version": "0.6.0",
        "docs": "/docs",
    }


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An unexpected error occurred",
    }
