# Generic Agent System Architecture

This document describes the architecture of the "Generic Research & Advice" example, focusing on how it leverages the Soorma SDK, Event Registry, and LLMs to create a dynamic, event-driven system.

## Overview

The system is designed as a **Choreography of Autonomous Agents**. Unlike a traditional monolithic application or a rigid pipeline, these agents operate independently, reacting to events on a shared bus.

### The "Trinity" of Agents

The architecture uses three primary types of agents defined in the Soorma SDK:

1.  **Planner (`AgentOrchestrator`)**: The "brain". It maintains the high-level goal and decides the next step. It does *not* know how to do the work; it only knows how to ask for it.
2.  **Worker (`WebResearcher`, `ContentDrafter`, `FactChecker`)**: The "doers". They listen for specific requests (events), perform a task (often using an LLM), and publish a result. They are stateless and unaware of the larger workflow.
3.  **Tool (Implicit)**: The `EventToolkit` acts as a bridge, allowing the Planner to treat the Event Registry as a dynamic tool menu.

## Dynamic Discovery & LLM Integration

One of the key features of this architecture is that the Planner is not hardcoded with a specific workflow. Instead, it uses **Dynamic Discovery**.

### 1. Event Registry as the "Source of Truth"
All agents register their capabilities (as Events) with the **Registry Service** on startup.
- `Researcher` registers `agent.research.requested` (Input) and `agent.research.completed` (Output).
- `Drafter` registers `agent.draft.requested` (Input) and `agent.draft.completed` (Output).

### 2. The `EventToolkit`
The Planner uses the `EventToolkit` from the SDK to query the Registry.
```python
async with EventToolkit() as toolkit:
    # "What actions are available to me?"
    events = await toolkit.discover_events(topic="action-requests")
```

The toolkit returns **Structured Metadata** for each event, optimized for LLM consumption:
- **Event Name**: e.g., `agent.research.requested`
- **Description**: "Performs web research on a topic."
- **Schema**: JSON Schema defining required fields (`query`, `context`).

### 3. LLM Decision Making
The Planner constructs a prompt for the LLM that includes:
- **Current Context**: What has happened so far (e.g., "Goal received", "Research completed").
- **Available Tools**: The list of discovered events and their descriptions.

**Prompt Structure:**
```text
You are an autonomous agent orchestrator.
Current Context: {context}

Available Events to Publish:
[
  {"name": "agent.research.requested", "description": "Performs web research..."},
  {"name": "agent.draft.requested", "description": "Drafts response..."}
]

Decide the next logical step.
```

The LLM reasons about the state and selects the most appropriate event to publish. This allows the workflow to adapt. For example, if the `Validator` rejects a draft, the Planner (via LLM) naturally decides to send it back to the `Drafter` because that's the logical next step given the available tools.

## Data Flow & Structured Payloads

Communication between agents is strictly typed using **Pydantic Models**.

1.  **Definition**: Events are defined as Pydantic models in `events.py`.
    ```python
    class ResearchRequestPayload(BaseModel):
        query: str = Field(..., description="The topic to research")
        context: Optional[str] = Field(None, description="Context")
    ```
2.  **Registration**: These models are converted to JSON Schemas and stored in the Registry.
3.  **Validation**: When an agent receives an event, the SDK (and Pydantic) validates the payload against the schema. This ensures that the LLM-generated data is structurally correct before it reaches the business logic.

## Agent Design Pattern

Each agent follows a "Listen-Think-Act" loop:

1.  **Listen**: Subscribe to a specific event topic (e.g., `agent.research.requested`).
2.  **Think (LLM)**:
    -   Extract data from the event payload.
    -   Construct a prompt for the LLM using the payload data.
    -   (Optional) Use `litellm` to call OpenAI/Anthropic.
3.  **Act**:
    -   Parse the LLM response.
    -   Construct a result Event (e.g., `agent.research.completed`).
    -   Publish the event back to the bus.

## Summary

This architecture decouples the "What" (Planner) from the "How" (Workers). By using the Registry and LLMs together, the system becomes self-describing and flexible. The Planner doesn't need to know *how* research is done, only that there is an event it can trigger to get it done.
