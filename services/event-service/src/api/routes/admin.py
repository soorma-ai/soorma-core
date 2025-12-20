from typing import Any, Dict
from fastapi import APIRouter
from ...services.event_manager import event_manager

router = APIRouter(tags=["Admin"])

@router.get("/connections")
async def list_connections() -> Dict[str, Any]:
    """
    List all active SSE connections.
    
    Note: This endpoint should be protected in production.
    """
    return {
        "count": len(event_manager.active_connections),
        "connections": [
            {
                "connection_id": conn_id,
                "agent_id": data.get("agent_id"),
                "topics": data.get("topics"),
            }
            for conn_id, data in event_manager.active_connections.items()
        ],
    }
