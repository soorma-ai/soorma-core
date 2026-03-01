"""
API endpoints for agent registry.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
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
from ..dependencies import get_auth_context

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRegistrationResponse)
async def register_agent(
    request: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
) -> AgentRegistrationResponse:
    """
    Register or update an agent in the agent registry (upsert operation).
    
    Args:
        request: Agent registration request (Full structured format)
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Returns:
        AgentRegistrationResponse with registration status
        
    Raises:
        HTTPException: 400 if registration fails
    """
    tenant_id, user_id = auth_context
    response = await AgentRegistryService.register_agent(
        db, request.agent, tenant_id, user_id
    )
    
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
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
) -> AgentQueryResponse:
    """
    Query agents based on filters. Returns all agents if no filters provided.
    By default, only active (non-expired) agents are returned.
    Automatically filters by tenant_id from auth context.
    
    Args:
        agent_id: Optional agent ID filter
        name: Optional name filter
        consumed_event: Optional consumed event filter
        produced_event: Optional produced event filter
        include_expired: If True, include expired agents in results
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Returns:
        AgentQueryResponse with matching agents
    """
    tenant_id, user_id = auth_context
    return await AgentRegistryService.query_agents(
        db=db,
        tenant_id=tenant_id,
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
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
) -> AgentRegistrationResponse:
    """
    Refresh an agent's heartbeat to extend its TTL.
    This is a lightweight operation that only updates the last_heartbeat timestamp.
    
    Args:
        agent_id: ID of the agent to refresh
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Returns:
        AgentRegistrationResponse with refresh status
        
    Raises:
        HTTPException: 404 if agent not found
    """
    tenant_id, user_id = auth_context
    response = await AgentRegistryService.refresh_agent_heartbeat(
        db, agent_id, tenant_id
    )
    
    # Return 404 if agent not found
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message
        )
    
    return response


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
):
    """
    Delete an agent from the registry.
    
    Args:
        agent_id: ID of the agent to delete
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Raises:
        HTTPException: 404 if agent not found
    """
    tenant_id, user_id = auth_context
    success = await AgentRegistryService.delete_agent(db, agent_id, tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
