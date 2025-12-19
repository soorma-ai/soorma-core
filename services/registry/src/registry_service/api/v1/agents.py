"""
API endpoints for agent registry.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentQueryResponse,
    AgentDefinition,
    AgentCapability
)
from ...services import AgentRegistryService
from ...core.database import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


class SDKAgentRegistrationRequest(BaseModel):
    """
    Request model matching the SDK's flat structure.
    """
    agent_id: str
    name: str
    agent_type: str
    capabilities: List[str]
    events_consumed: List[str]
    events_produced: List[str]
    metadata: Optional[Dict[str, Any]] = None


@router.post("", response_model=AgentRegistrationResponse)
async def register_agent(
    request: SDKAgentRegistrationRequest,
    db: AsyncSession = Depends(get_db)
) -> AgentRegistrationResponse:
    """
    Register or update an agent in the agent registry (upsert operation).
    
    Args:
        request: Agent registration request (SDK format)
        db: Database session (injected)
        
    Returns:
        AgentRegistrationResponse with registration status
        
    Raises:
        HTTPException: 400 if registration fails
    """
    # Convert SDK request to AgentDefinition
    capabilities = []
    for cap_name in request.capabilities:
        capabilities.append(AgentCapability(
            task_name=cap_name,
            description=f"Capability: {cap_name}",
            consumed_event="unknown",
            produced_events=[]
        ))
        
    agent_def = AgentDefinition(
        agent_id=request.agent_id,
        name=request.name,
        description=request.metadata.get("description", "") if request.metadata else "",
        capabilities=capabilities,
        consumed_events=request.events_consumed,
        produced_events=request.events_produced
    )

    response = await AgentRegistryService.register_agent(db, agent_def)
    
    # If registration failed, return 400 Bad Request
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("", response_model=AgentQueryResponse)
async def query_agents(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    name: Optional[str] = Query(None, description="Filter by agent name"),
    consumed_event: Optional[str] = Query(None, description="Filter by consumed event"),
    produced_event: Optional[str] = Query(None, description="Filter by produced event"),
    include_expired: bool = Query(False, description="Include expired agents in results"),
    db: AsyncSession = Depends(get_db)
) -> AgentQueryResponse:
    """
    Query agents based on filters. Returns all agents if no filters provided.
    By default, only active (non-expired) agents are returned.
    
    Args:
        agent_id: Optional agent ID filter
        name: Optional name filter
        consumed_event: Optional consumed event filter
        produced_event: Optional produced event filter
        include_expired: If True, include expired agents in results
        db: Database session (injected)
        
    Returns:
        AgentQueryResponse with matching agents
    """
    return await AgentRegistryService.query_agents(
        db=db,
        agent_id=agent_id,
        name=name,
        consumed_event=consumed_event,
        produced_event=produced_event,
        include_expired=include_expired
    )


@router.post("/{agent_id}/heartbeat", response_model=AgentRegistrationResponse)
@router.put("/{agent_id}/heartbeat", response_model=AgentRegistrationResponse)
async def refresh_agent_heartbeat(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentRegistrationResponse:
    """
    Refresh an agent's heartbeat to extend its TTL.
    This is a lightweight operation that only updates the last_heartbeat timestamp.
    
    Args:
        agent_id: ID of the agent to refresh
        db: Database session (injected)
        
    Returns:
        AgentRegistrationResponse with refresh status
    """
    return await AgentRegistryService.refresh_agent_heartbeat(db, agent_id)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an agent from the registry.
    
    Args:
        agent_id: ID of the agent to delete
        db: Database session (injected)
        
    Raises:
        HTTPException: 404 if agent not found
    """
    success = await AgentRegistryService.delete_agent(db, agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
