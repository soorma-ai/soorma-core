"""
Client library for interacting with the Registry Service.
"""
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


class RegistryClient:
    """
    Client for interacting with the Registry Service API.
    
    This client allows other services to register and query events and agents.
    """
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the registry client.
        
        Args:
            base_url: Base URL of the registry service (e.g., "http://localhost:8000")
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
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
        request = EventRegistrationRequest(event=event)
        response = await self._client.post(
            f"{self.base_url}/api/v1/events",
            json=request.model_dump(by_alias=True)
        )
        response.raise_for_status()
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
            f"{self.base_url}/api/v1/events",
            params={"event_name": event_name}
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
        response = await self._client.get(
            f"{self.base_url}/api/v1/events",
            params={"topic": topic}
        )
        response.raise_for_status()
        result = EventQueryResponse.model_validate(response.json())
        return result.events
        
    async def get_all_events(self) -> List[EventDefinition]:
        """
        Get all registered events.
        
        Returns:
            List of all EventDefinitions
        """
        response = await self._client.get(f"{self.base_url}/api/v1/events")
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
            f"{self.base_url}/api/v1/agents",
            json=request.model_dump(by_alias=True)
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
            f"{self.base_url}/api/v1/agents",
            params={"agent_id": agent_id}
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
            f"{self.base_url}/api/v1/agents",
            params=params
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return result.agents
