from fastapi import APIRouter
from ...models.schemas import HealthResponse
from ...services.event_manager import event_manager

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status, adapter connection state, and active streams count.
    """
    adapter = event_manager.adapter
    return HealthResponse(
        status="healthy" if adapter and adapter.is_connected else "degraded",
        adapter=adapter.name if adapter else "none",
        connected=adapter.is_connected if adapter else False,
        active_streams=len(event_manager.active_connections),
    )
