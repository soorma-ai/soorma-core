"""
AI-friendly toolkit for dynamic event discovery and generation.

This module provides utilities specifically designed for AI agents to:
1. Discover available events from the registry
2. Generate example payloads from schemas
3. Validate and publish events dynamically
4. Handle responses without hardcoded DTOs

The toolkit abstracts away the complexity of working with JSON schemas
and provides a simple, intuitive interface that AI agents can understand.
"""
from typing import Any, Dict, List, Optional
from pydantic import ValidationError as PydanticValidationError

from soorma.registry.client import RegistryClient
from soorma_common import EventDefinition
from soorma_common.events import EventTopic
from soorma.utils.schema_utils import (
    create_event_models,
    get_schema_field_names,
    get_required_fields,
)


class EventToolkit:
    """
    AI-friendly toolkit for working with events dynamically.
    
    This class provides a simple interface for AI agents to discover
    and work with events without needing to know schemas in advance.
    
    Example:
        >>> async with EventToolkit() as toolkit:
        ...     # Discover available events
        ...     events = await toolkit.discover_events(topic="action-requests")
        ...     
        ...     # Create validated payload
        ...     payload = await toolkit.create_payload(
        ...         "web.search.request",
        ...         {"query": "AI trends"}
        ...     )
    """
    
    def __init__(self, registry_url: str = "http://localhost:8000", registry_client: Optional[RegistryClient] = None):
        """
        Initialize the toolkit.
        
        Args:
            registry_url: Registry service URL (default: http://localhost:8000)
            registry_client: Optional RegistryClient to reuse (shares HTTP session with context)
        """
        self.registry_url = registry_url
        self._client: Optional[RegistryClient] = registry_client
        self._owns_client = registry_client is None  # Track if we own the client lifecycle
    
    async def __aenter__(self):
        """Async context manager entry - only creates client if not shared."""
        if self._owns_client and not self._client:
            self._client = RegistryClient(base_url=self.registry_url)
            await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - only closes client if we created it."""
        if self._owns_client and self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _format_event_descriptor(self, event: EventDefinition) -> Dict[str, Any]:
        """Format event definition for AI consumption."""
        required_fields = get_required_fields(event.payload_schema)
        payload_fields = {}
        
        for name, prop in event.payload_schema.get("properties", {}).items():
            field_info = prop.copy()
            field_info["required"] = name in required_fields
            if "enum" in field_info:
                field_info["allowed_values"] = field_info.pop("enum")
            payload_fields[name] = field_info

        descriptor = {
            "name": event.event_name,
            "description": event.description,
            "topic": event.topic,
            "required_fields": required_fields,
            "payload_fields": payload_fields,
            "example_payload": self._generate_example(event.payload_schema),
            "has_response": event.response_schema is not None
        }
        
        if event.response_schema:
            descriptor["response_fields"] = event.response_schema.get("properties", {})
            
        return descriptor

    async def discover_events(
        self,
        topic: Optional[EventTopic] = None,
        event_name_pattern: Optional[str] = None,
    ) -> List[EventDefinition]:
        """
        Discover available events with their schemas.
        
        Returns strongly-typed EventDefinition objects for type safety.
        Use format_for_llm() to convert to LLM-friendly format.
        
        Args:
            topic: Optional topic filter (e.g., "action-requests", "business-facts")
            event_name_pattern: Optional pattern to match in event names
        
        Returns:
            List of EventDefinition objects
        """
        if not self._client:
            raise RuntimeError(
                "Toolkit must be used as async context manager or initialized with registry_client. "
                "When using context.toolkit, no async with is needed."
            )
        
        # Get events from registry
        if topic:
            all_events = await self._client.get_events_by_topic(topic.value)
        else:
            all_events = await self._client.get_all_events()
        
        # Filter by name pattern if provided
        if event_name_pattern:
            all_events = [
                e for e in all_events 
                if event_name_pattern.lower() in e.event_name.lower()
            ]
            
        return all_events

    async def discover_actionable_events(self, topic: Optional[EventTopic] = None) -> List[EventDefinition]:
        """
        Discover events that are currently consumed by active agents.
        
        This filters the universe of events down to only those that will actually
        trigger an action by a live agent.
        
        Args:
            topic: Optional topic filter
            
        Returns:
            List of EventDefinition objects for actionable events
        """
        if not self._client:
            raise RuntimeError("Toolkit must be used as async context manager")
            
        # 1. Get all active agents
        agents = await self._client.query_agents()
        
        # 2. Collect all consumed events
        consumed_event_names = set()
        for agent in agents:
            if agent.consumed_events:
                consumed_event_names.update(agent.consumed_events)
                
        if not consumed_event_names:
            return []
            
        # 3. Get details for these events
        if topic:
            all_events = await self._client.get_events_by_topic(topic.value)
        else:
            all_events = await self._client.get_all_events()
            
        # 4. Filter to actionable events
        actionable_events = [
            e for e in all_events 
            if e.event_name in consumed_event_names
        ]
        
        return actionable_events

    async def get_event_info(self, event_name: str) -> Optional[EventDefinition]:
        """
        Get detailed information about a specific event.
        
        Args:
            event_name: Name of the event
            
        Returns:
            EventDefinition object, or None if not found
        """
        if not self._client:
            raise RuntimeError("Toolkit must be used as async context manager")
            
        return await self._client.get_event(event_name)
    
    def format_for_llm(self, events: List[EventDefinition]) -> List[Dict[str, Any]]:
        """
        Format EventDefinition objects for LLM consumption.
        
        Converts strongly-typed EventDefinition objects into simplified
        dictionaries with computed fields that LLMs can easily reason about.
        
        Args:
            events: List of EventDefinition objects
            
        Returns:
            List of LLM-friendly event descriptor dictionaries
        """
        return [self._format_event_descriptor(e) for e in events]
    
    def format_as_prompt_text(
        self,
        events: List[Dict[str, Any]],
        include_metadata: bool = True,
        numbered: bool = True
    ) -> str:
        """
        Format event dictionaries as human-readable text for LLM prompts.
        
        This method takes event dictionaries (from format_for_llm) and creates
        nicely formatted text suitable for injecting into LLM prompts.
        
        Args:
            events: Event dictionaries (from format_for_llm)
            include_metadata: Include metadata like when_to_use guidance
            numbered: Add numbering (1., 2., etc.)
            
        Returns:
            Formatted string ready for prompt injection
            
        Example:
            >>> definitions = await toolkit.discover_events(topic="action-requests")
            >>> dicts = toolkit.format_for_llm(definitions)
            >>> prompt_text = toolkit.format_as_prompt_text(dicts)
            >>> # Use in prompt: f"Available actions:\n{prompt_text}"
        """
        formatted = []
        for i, event in enumerate(events, 1):
            prefix = f"{i}. " if numbered else ""
            lines = [
                f"{prefix}**{event['name']}**",
                f"   Description: {event['description']}"
            ]
            
            # Include metadata guidance if available
            if include_metadata:
                metadata = event.get("metadata", {})
                when_to_use = metadata.get("when_to_use")
                if when_to_use:
                    lines.append(f"   When to use: {when_to_use}")
            
            formatted.append("\n".join(lines))
        
        return "\n".join(formatted)

    async def create_payload(
        self, 
        event_name: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and validate an event payload.
        
        Args:
            event_name: Name of the event
            data: Raw data dictionary (can be snake_case)
            
        Returns:
            Validated payload dictionary (camelCase)
            
        Raises:
            ValueError: If event not found or validation fails
        """
        if not self._client:
            raise RuntimeError("Toolkit must be used as async context manager")
            
        event = await self._client.get_event(event_name)
        if not event:
            raise ValueError(f"Event '{event_name}' not found in registry")
            
        # Create dynamic Pydantic model
        PayloadModel, _ = create_event_models(event)
        
        # Validate and convert
        try:
            model_instance = PayloadModel.model_validate(data)
            return model_instance.model_dump(by_alias=True)
        except PydanticValidationError as e:
            # Re-raise as ValueError with clear message for AI
            raise ValueError(f"Payload validation failed: {str(e)}")

    async def validate_response(
        self,
        event_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate an event response.
        
        Args:
            event_name: Name of the event
            data: Response data dictionary
            
        Returns:
            Validated response dictionary
            
        Raises:
            ValueError: If event not found, has no response schema, or validation fails
        """
        if not self._client:
            raise RuntimeError("Toolkit must be used as async context manager")
            
        event = await self._client.get_event(event_name)
        if not event:
            raise ValueError(f"Event '{event_name}' not found in registry")
            
        if not event.response_schema:
            raise ValueError(f"Event '{event_name}' has no response schema")
            
        # Create dynamic Pydantic model
        _, ResponseModel = create_event_models(event)
        
        if not ResponseModel:
             raise ValueError(f"Event '{event_name}' has no response schema")

        # Validate and convert
        try:
            model_instance = ResponseModel.model_validate(data)
            return model_instance.model_dump(by_alias=True)
        except PydanticValidationError as e:
            raise ValueError(f"Response validation failed: {str(e)}")

    def _generate_example(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simple example from schema."""
        example = {}
        properties = schema.get("properties", {})
        
        for name, prop in properties.items():
            prop_type = prop.get("type")
            if prop_type == "string":
                example[name] = prop.get("example", "string_value")
            elif prop_type == "integer":
                example[name] = prop.get("minimum", 0)
            elif prop_type == "boolean":
                example[name] = True
            elif prop_type == "object":
                example[name] = {}
            elif prop_type == "array":
                example[name] = []
                
        return example

# Helper functions for non-async usage (if needed)
async def discover_events_simple(
    topic: Optional[str] = None,
    registry_url: str = "http://localhost:8000"
) -> List[EventDefinition]:
    """One-shot event discovery."""
    async with EventToolkit(registry_url) as toolkit:
        return await toolkit.discover_events(topic)

async def create_event_payload_simple(
    event_name: str,
    data: Dict[str, Any],
    registry_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """One-shot payload creation."""
    try:
        async with EventToolkit(registry_url) as toolkit:
            payload = await toolkit.create_payload(event_name, data)
            return {
                "success": True,
                "payload": payload,
                "errors": []
            }
    except Exception as e:
        return {
            "success": False,
            "errors": [str(e)]
        }


async def get_event_info_simple(
    event_name: str,
    registry_url: str = "http://localhost:8000"
) -> Optional[EventDefinition]:
    """One-shot event info retrieval."""
    async with EventToolkit(registry_url) as toolkit:
        return await toolkit.get_event_info(event_name)
