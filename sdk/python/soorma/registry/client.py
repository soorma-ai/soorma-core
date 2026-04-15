"""
Client library for interacting with the Registry Service.
"""
import logging
import os
from typing import List, Optional

import httpx

from soorma.auth import AuthTokenProvider, resolve_auth_token
from soorma_common import (
    EventDefinition,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryResponse,
    AgentDefinition,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentQueryResponse,
    DiscoveredAgent,
    PayloadSchema,
    PayloadSchemaRegistrationRequest,
    PayloadSchemaResponse,
    PayloadSchemaListResponse,
)

logger = logging.getLogger(__name__)


class RegistryClient:
    """
    Client for interacting with the Registry Service API.

    Authentication Model:
        Registry uses bearer-token transport during JWT cutover. Server-side
        platform tenant resolution comes from validated JWT claims rather than
        legacy tenant headers projected by the SDK.
    """

    def __init__(
            self,
            base_url: str,
            timeout: float = 30.0,
            auth_token: Optional[str] = None,
            auth_token_provider: Optional[AuthTokenProvider] = None,
    ):
        """
        Initialize the registry client.

        Args:
            base_url: Base URL of the registry service (e.g., "http://localhost:8081")
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._auth_token = auth_token or os.getenv("SOORMA_AUTH_TOKEN")
        self._auth_token_provider = auth_token_provider
        self._client = httpx.AsyncClient(timeout=timeout)

    def set_auth_token(self, auth_token: Optional[str]) -> None:
        """Inject or replace bearer token for registry-service requests."""
        self._auth_token = auth_token

    def set_auth_token_provider(self, auth_token_provider: Optional[AuthTokenProvider]) -> None:
        """Inject or replace bearer token provider for registry-service requests."""
        self._auth_token_provider = auth_token_provider

    async def _build_auth_headers(self) -> dict[str, str]:
        """Build auth headers for registry-service calls."""
        token = await resolve_auth_token(self._auth_token, self._auth_token_provider)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}
    
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
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
            headers=await self._build_auth_headers()
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return result.agents

    async def deregister_agent(self, agent_id: str) -> bool:
        """
        Deregister (delete) an agent from the registry.

        Must include auth headers (X-Tenant-ID) — the agent belongs to the
        developer tenant and can only be removed within that tenant scope.

        Args:
            agent_id: ID of the agent to deregister

        Returns:
            True if deregistered successfully, False if agent not found
        """
        response = await self._client.delete(
            f"{self.base_url}/v1/agents/{agent_id}",
            headers=await self._build_auth_headers()
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    async def refresh_heartbeat(self, agent_id: str) -> bool:
        """
        Refresh an agent's heartbeat to extend its TTL.

        Must include auth headers so the registry can verify the request is
        within the correct developer tenant scope.

        Args:
            agent_id: ID of the agent to refresh

        Returns:
            True if heartbeat refreshed successfully, False otherwise
        """
        response = await self._client.put(
            f"{self.base_url}/v1/agents/{agent_id}/heartbeat",
            headers=await self._build_auth_headers()
        )
        return response.status_code == 200

    # Schema Registry Methods (v0.8.1+)

    async def register_schema(self, schema: PayloadSchema) -> PayloadSchemaResponse:
        """
        Register a payload schema with the Registry Service.

        Args:
            schema: Payload schema definition to register

        Returns:
            PayloadSchemaResponse with success flag
        """
        request = PayloadSchemaRegistrationRequest(payload_schema=schema)
        response = await self._client.post(
            f"{self.base_url}/v1/schemas",
            json=request.model_dump(by_alias=True),
            headers=await self._build_auth_headers(),
        )
        response.raise_for_status()
        return PayloadSchemaResponse.model_validate(response.json())

    async def get_schema(
        self,
        schema_name: str,
        version: Optional[str] = None,
    ) -> Optional[PayloadSchema]:
        """
        Retrieve a schema by name (latest version) or by name + version.

        Args:
            schema_name: Schema name to look up
            version: Optional version string; latest version returned if omitted

        Returns:
            PayloadSchema DTO if found, None otherwise
        """
        if version is not None:
            url = f"{self.base_url}/v1/schemas/{schema_name}/versions/{version}"
        else:
            url = f"{self.base_url}/v1/schemas/{schema_name}"
        response = await self._client.get(url, headers=await self._build_auth_headers())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return PayloadSchema.model_validate(response.json())

    async def list_schemas(
        self,
        owner_agent_id: Optional[str] = None,
    ) -> List[PayloadSchema]:
        """
        List schemas for this developer tenant, optionally filtered by owner agent.

        Args:
            owner_agent_id: Optional agent ID filter

        Returns:
            List of PayloadSchema DTOs
        """
        params = {}
        if owner_agent_id is not None:
            params["owner_agent_id"] = owner_agent_id
        response = await self._client.get(
            f"{self.base_url}/v1/schemas",
            params=params,
            headers=await self._build_auth_headers(),
        )
        response.raise_for_status()
        result = PayloadSchemaListResponse.model_validate(response.json())
        return result.schemas

    def _map_agent_to_discovered(self, agent: AgentDefinition) -> DiscoveredAgent:
        """Map AgentDefinition to DiscoveredAgent, parsing version from name.

        Name format is ``"AgentName:version"`` (e.g. ``"SearchWorker:1.0.0"``).
        When no version suffix is present, defaults to ``"1.0.0"``.

        Args:
            agent: Raw AgentDefinition from the service response.

        Returns:
            DiscoveredAgent with separate name and version fields.
        """
        # Parse version from name using the established Name:version convention
        # (service does not yet return version as a separate field — see FDE-2)
        name_parts = agent.name.split(":")
        name = name_parts[0]
        version = name_parts[1] if len(name_parts) > 1 else "1.0.0"
        return DiscoveredAgent(
            agent_id=agent.agent_id,
            name=name,
            description=agent.description,
            version=version,
            capabilities=agent.capabilities,
        )

    async def discover_agents(
        self,
        consumed_event: Optional[str] = None,
    ) -> List[DiscoveredAgent]:
        """Discover active agents by capability (consumed event).

        Backward-compatible discovery entry point. Retained for callers that
        specify a consumed event directly rather than using requirements-based
        discovery (see ``discover()``). Both methods return ``DiscoveredAgent``
        since Phase 3.

        Args:
            consumed_event: Optional event name to filter agents by their
                            consumed event.

        Returns:
            List of DiscoveredAgent DTOs for matching active agents.
        """
        params: dict = {}
        if consumed_event is not None:
            params["consumed_event"] = consumed_event
        response = await self._client.get(
            f"{self.base_url}/v1/agents/discover",
            params=params,
            headers=await self._build_auth_headers(),
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return [self._map_agent_to_discovered(agent) for agent in result.agents]

    async def discover(
        self,
        requirements: List[str],
        include_schemas: bool = True,
    ) -> List[DiscoveredAgent]:
        """Discover agents by capability requirements.

        High-level discovery API that accepts a list of capability task_name
        keywords and returns DiscoveredAgent objects whose capabilities match
        at least one requirement.

        The service's ``GET /v1/agents/discover`` endpoint filters by
        ``consumed_event`` (event name), not by ``task_name``.  This method
        fetches all agents and applies the task_name filter client-side so
        callers can use human-readable capability names (e.g. ``"web_research"``)
        rather than internal event names (e.g. ``"research.requested"``).

        Args:
            requirements: List of capability task_name keywords to match,
                          e.g. ``["web_research"]``.  An agent is included if
                          ANY of its capabilities' task_name matches ANY entry
                          in this list (case-insensitive substring match).
            include_schemas: Unused at this layer (reserved for future schema
                             enrichment pass).  Kept for API compatibility.

        Returns:
            List of DiscoveredAgent DTOs whose capabilities match at least one
            requirement.
        """
        # Fetch all active agents for this tenant — the service has no task_name
        # filter, so we apply it client-side below.
        response = await self._client.get(
            f"{self.base_url}/v1/agents/discover",
            headers=await self._build_auth_headers(),
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())

        lower_reqs = [r.lower() for r in requirements]

        def _matches(agent: AgentDefinition) -> bool:
            """Return True if any capability task_name matches any requirement."""
            for cap in agent.capabilities:
                task = (cap.task_name or "").lower()
                if any(req in task or task in req for req in lower_reqs):
                    return True
            return False

        matching = [a for a in result.agents if _matches(a)]
        return [self._map_agent_to_discovered(a) for a in matching]
