"""
Client library for interacting with the Registry Service.
"""
import logging
import os
from typing import List, Optional
import httpx
from soorma_common import (
    EventDefinition,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryResponse,
    AgentDefinition,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentQueryResponse,
)

logger = logging.getLogger(__name__)


class RegistryClient:
    """
    Client for interacting with the Registry Service API.

    Authentication context (tenant_id, user_id) is set at construction time
    from environment variables SOORMA_TENANT_ID / SOORMA_USER_ID. These
    represent the agent developer's deployment identity and are used for
    startup registration calls only.

    TODO: Replace env-var placeholder with API key / machine token once that
    auth flow is implemented (v0.8.0+).
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the registry client.

        tenant_id and user_id are read from the environment at construction
        time so that the running agent process gets a stable identity for its
        lifetime without leaking credentials into agent config or AgentDefinition.

        Args:
            base_url: Base URL of the registry service (e.g., "http://localhost:8081")
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Deployment identity — placeholder until API key auth is available
        self._tenant_id = os.getenv("SOORMA_TENANT_ID", "00000000-0000-0000-0000-000000000000")
        self._user_id = os.getenv("SOORMA_USER_ID", "00000000-0000-0000-0000-000000000000")
        self._auth_headers = {"X-Tenant-ID": self._tenant_id, "X-User-ID": self._user_id}
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Event Registry Methods
    
    async def register_event(self, event: EventDefinition) -> EventRegistrationResponse:
        """
        Register a new event in the event registry.
        
        Args:
            event: Event definition to register
            
        Returns:
            EventRegistrationResponse with registration status
        """
        logger.info(f"[RegistryClient] Registering event: {event.event_name} on topic: {event.topic}")
        
        request = EventRegistrationRequest(event=event)
        request_json = request.model_dump(by_alias=True)
        logger.debug(f"[RegistryClient] Request payload: {request_json}")
        
        response = await self._client.post(
            f"{self.base_url}/v1/events",
            json=request_json,
            headers=self._auth_headers
        )
        response.raise_for_status()
        logger.info(f"[RegistryClient] Event {event.event_name} registered successfully")
        
        return EventRegistrationResponse.model_validate(response.json())
    
    async def get_event(self, event_name: str) -> Optional[EventDefinition]:
        """
        Get a specific event by name.
        
        Args:
            event_name: Name of the event to retrieve
            
        Returns:
            EventDefinition if found, None otherwise
        """
        response = await self._client.get(
            f"{self.base_url}/v1/events",
            params={"event_name": event_name},
            headers=self._auth_headers
        )
        response.raise_for_status()
        result = EventQueryResponse.model_validate(response.json())
        return result.events[0] if result.events else None
    
    async def get_events_by_topic(self, topic: str) -> List[EventDefinition]:
        """
        Get all events for a specific topic.
        
        Args:
            topic: Topic to filter by
            
        Returns:
            List of EventDefinitions for the topic
        """
        logger.info(f"[RegistryClient] Querying events with topic={topic}")
        
        response = await self._client.get(
            f"{self.base_url}/v1/events",
            params={"topic": topic},
            headers=self._auth_headers
        )
        response.raise_for_status()
        result = EventQueryResponse.model_validate(response.json())
        logger.info(f"[RegistryClient] Parsed {len(result.events)} events")
        return result.events
        
    async def get_all_events(self) -> List[EventDefinition]:
        """
        Get all registered events.
        
        Returns:
            List of all EventDefinitions
        """
        response = await self._client.get(
            f"{self.base_url}/v1/events",
            headers=self._auth_headers
        )
        response.raise_for_status()
        result = EventQueryResponse.model_validate(response.json())
        return result.events

    # Agent Registry Methods

    async def register_agent(self, agent: AgentDefinition) -> AgentRegistrationResponse:
        """
        Register a new agent in the agent registry.
        
        Args:
            agent: Agent definition to register
            
        Returns:
            AgentRegistrationResponse with registration status
        """
        request = AgentRegistrationRequest(agent=agent)
        response = await self._client.post(
            f"{self.base_url}/v1/agents",
            json=request.model_dump(by_alias=True),
            headers=self._auth_headers
        )
        response.raise_for_status()
        return AgentRegistrationResponse.model_validate(response.json())

    async def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        """
        Get a specific agent by ID.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            AgentDefinition if found, None otherwise
        """
        response = await self._client.get(
            f"{self.base_url}/v1/agents",
            params={"agent_id": agent_id},
            headers=self._auth_headers
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return result.agents[0] if result.agents else None

    async def query_agents(
        self,
        name: Optional[str] = None,
        consumed_event: Optional[str] = None,
        produced_event: Optional[str] = None
    ) -> List[AgentDefinition]:
        """
        Query agents with filters.
        
        Args:
            name: Filter by agent name
            consumed_event: Filter by consumed event
            produced_event: Filter by produced event
            
        Returns:
            List of matching AgentDefinitions
        """
        params = {}
        if name:
            params["name"] = name
        if consumed_event:
            params["consumed_event"] = consumed_event
        if produced_event:
            params["produced_event"] = produced_event
            
        response = await self._client.get(
            f"{self.base_url}/v1/agents",
            params=params,
            headers=self._auth_headers
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return result.agents