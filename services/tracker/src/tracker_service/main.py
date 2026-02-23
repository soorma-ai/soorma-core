"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tracker_service import __version__
from tracker_service.core.config import settings
from tracker_service.core.db import init_db, close_db
from tracker_service.api.v1 import query
from tracker_service.subscribers.event_handlers import (
    start_event_subscribers,
    stop_event_subscribers,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    print(f"Starting Tracker Service v{__version__}")
    print(f"Local testing mode: {settings.is_local_testing}")
    print(f"Database URL: {settings.database_url}")

    # Initialize database connection
    await init_db()

    # Start event subscribers to receive plan/action events
    await start_event_subscribers(settings.event_service_url)

    yield

    # Shutdown
    print("Shutting down Tracker Service")
    await stop_event_subscribers()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Soorma Tracker Service",
    description="Event-driven observability for autonomous agents (DisCo framework)",
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

# Include API routers
app.include_router(query.router)


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
        "tracker_service.main:app",
        host="0.0.0.0",
        port=8084,
        reload=not settings.is_prod,
    )
