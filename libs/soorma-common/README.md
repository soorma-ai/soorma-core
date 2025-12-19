# Soorma Common

Common models and DTOs shared across Soorma platform services.

## Installation

```bash
pip install -e .
```

## Usage

```python
from soorma_common.models import (
    AgentDefinition,
    AgentCapability,
    EventDefinition,
)

# Create an agent definition
agent = AgentDefinition(
    agent_id="my-agent",
    name="My Agent",
    description="A sample agent",
    capabilities=[
        AgentCapability(
            task_name="process_data",
            description="Process incoming data",
            consumed_event="data.received",
            produced_events=["data.processed", "data.error"]
        )
    ]
)
```

## Models

### Agent Registry

- `AgentCapability` - Describes a single capability or task an agent can perform
- `AgentDefinition` - Defines a single agent in the system
- `AgentRegistrationRequest` - Request to register a new agent
- `AgentRegistrationResponse` - Response after registering an agent
- `AgentQueryRequest` - Request to query agents
- `AgentQueryResponse` - Response containing agent definitions

### Event Registry

- `EventDefinition` - Defines a single event in the system
- `EventRegistrationRequest` - Request to register a new event
- `EventRegistrationResponse` - Response after registering an event
- `EventQueryRequest` - Request to query events
- `EventQueryResponse` - Response containing event definitions
