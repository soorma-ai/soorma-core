"""
Main FastAPI application for Registry Service.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.background_tasks import background_task_manager
from .api import router

# Configure logging with timestamps
logging.basicConfig(
    level=logging.DEBUG if settings.IS_LOCAL_TESTING else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    await background_task_manager.start()
    yield
    # Shutdown
    await background_task_manager.stop()


# Create FastAPI application
# Disable docs in production for security
app = FastAPI(
    title="Registry Service",
    description="Event and Agent Registry Service for distributed autonomous agents",
    version=settings.SERVICE_VERSION,
    docs_url="/docs" if not settings.IS_PROD else None,
    redoc_url="/redoc" if not settings.IS_PROD else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    response = {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "operational"
    }
    # Only include docs URL in non-production environments
    if not settings.IS_PROD:
        response["docs"] = "/docs"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
