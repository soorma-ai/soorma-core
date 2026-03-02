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
      Registry Service is scoped to the **developer's own tenant** — not to any
      end-user session. The developer tenant UUID is read from the environment at
      construction time and sent as X-Tenant-ID on every request.

      Conceptual model (see ARCHITECTURE_PATTERNS.md Section 1):
        - SOORMA_DEVELOPER_TENANT_ID  → X-Tenant-ID  (this client)
        - User Tenant / User ID       → from event envelope (Memory, Tracker, Bus)

    TODO: Replace env-var placeholder with API key / machine token once that
    auth flow is implemented (v0.8.0+).
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the registry client.

        The developer tenant UUID is read from SOORMA_DEVELOPER_TENANT_ID at
        construction time. This represents the developer's own identity for
        startup registration — not the identity of any end-user or session.

        Falls back to the sentinel UUID 00000000-... for local development when
        the env var is not set.

        Args:
            base_url: Base URL of the registry service (e.g., "http://localhost:8081")
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Developer deployment identity — placeholder until API key auth is available.
        # SOORMA_DEVELOPER_TENANT_ID identifies whose agents/events are being registered.
        _developer_tenant_id = os.getenv(
            "SOORMA_DEVELOPER_TENANT_ID",
            "00000000-0000-0000-0000-000000000000"
        )
        self._auth_headers = {"X-Tenant-ID": _developer_tenant_id}
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
            headers=self._auth_headers
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
            headers=self._auth_headers
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
        request = PayloadSchemaRegistrationRequest(schema=schema)
        response = await self._client.post(
            f"{self.base_url}/v1/schemas",
            json=request.model_dump(by_alias=True),
            headers=self._auth_headers,
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
        response = await self._client.get(url, headers=self._auth_headers)
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
            headers=self._auth_headers,
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
            headers=self._auth_headers,
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

        High-level discovery API that accepts a list of capability keywords and
        returns fully-enriched DiscoveredAgent objects, optionally with schema
        references. Uses ``GET /v1/agents/discover`` with ``requirements`` query
        params.

        Args:
            requirements: List of capability keywords, e.g. ``["web_search"]``.
            include_schemas: Whether to include schema references in results
                             (default True).

        Returns:
            List of DiscoveredAgent DTOs matching at least one requirement.
        """
        params: dict = {
            "requirements": requirements,
            "include_schemas": include_schemas,
        }
        response = await self._client.get(
            f"{self.base_url}/v1/agents/discover",
            params=params,
            headers=self._auth_headers,
        )
        response.raise_for_status()
        result = AgentQueryResponse.model_validate(response.json())
        return [self._map_agent_to_discovered(agent) for agent in result.agents]
