# Action Plan: Stage 4 Phase 2 - Type-Safe Decisions (SOOR-PLAN-001-P2)

**Status:** 📋 Planning → 🟢 Ready for Implementation  
**Created:** February 19, 2026  
**Phase:** 2 of 4 (Implementation - Type-Safe Decisions & Autonomous Planning)  
**Estimated Duration:** 3 days  
**Parent Plan:** [MASTER_PLAN_Stage4_Planner.md](MASTER_PLAN_Stage4_Planner.md)  
**Dependencies:** ✅ Phase 1 (PlanContext complete)

---

## 1. Requirements & Core Objective

### Executive Summary

Implement **PlannerDecision types** and **ChoreographyPlanner** class to enable type-safe, LLM-based autonomous orchestration:

- **RF-SDK-015:** PlannerDecision and PlanAction types (soorma-common)
- **RF-SDK-016:** ChoreographyPlanner class (SDK ai module)

This phase adds the LLM reasoning layer on top of Phase 1's state machine foundation, enabling developers to reduce orchestration boilerplate from ~400 lines → ~50 lines.

### Acceptance Criteria

- [ ] **DTOs:** PlanAction enum and PlannerDecision model exist in soorma-common
- [ ] **DTOs:** PlannerDecision.model_json_schema() generates LLM-friendly prompt schemas
- [ ] **ChoreographyPlanner:** Class initializes with configurable LLM model (BYO credentials)
- [ ] **Event Discovery:** reason_next_action() discovers events from Registry Service
- [ ] **LLM Integration:** Uses LiteLLM for model-agnostic LLM calls (with fallback for offline)
- [ ] **Validation:** Prevents hallucinated events (validates event existence before publish)
- [ ] **Execution:** execute_decision() handles PUBLISH, COMPLETE, WAIT, DELEGATE actions
- [ ] **Circuit Breaker:** max_actions limit prevents runaway loops
- [ ] **Business Logic (Enhancement 1):** system_instructions parameter enables custom business rules
- [ ] **Runtime Context (Enhancement 2):** custom_context parameter for dynamic decision context
- [ ] **Planning Strategies:** Built-in strategies (balanced|conservative|aggressive)
- [ ] **Testing:** 25+ unit tests covering decisions, validation, execution, custom context
- [ ] **Testing:** 4+ integration tests for end-to-end choreography flows
- [ ] **Architecture Alignment:** Two-layer pattern verified (no direct service client imports in examples)

### Success Metrics

**Code Quality:**
- 90%+ test coverage on new code
- All type hints present and mypy strict-compliant
- Google-style docstrings on all public methods
- BYO model credentials (no API keys hardcoded)

**Developer Experience:**
- ChoreographyPlanner reduces planner code by 80%+ vs manual orchestration
- Developers can control LLM model via simple parameter
- Developers can inject business logic via system_instructions
- Developers can provide runtime context for dynamic decisions
- Error messages guide developers to set API keys
- LiteLLM supports 50+ models (user choice, not framework dictated)

**Architecture Integrity:**
- Zero direct service client imports in agent code (two-layer pattern verified)
- Examples use context.toolkit and context.bus exclusively
- PlannerDecision prevents LLM hallucinations via event validation

---

## 2. Technical Design

### Component: SDK + Common Library

### Data Models

**New File:** `libs/soorma-common/src/soorma_common/decisions.py`

```python
"""Decision types for LLM-based planning."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class PlanAction(str, Enum):
    """Actions a Planner can take in response to events."""
    
    PUBLISH = "publish"      # Publish a new event to trigger worker
    COMPLETE = "complete"    # Mark plan as complete, send response_event
    WAIT = "wait"           # Wait for next event (progress indicator)
    DELEGATE = "delegate"    # Delegate to another planner


class PublishAction(BaseModel):
    """Instruction to publish a new event."""
    
    action: PlanAction
    event_type: str = Field(..., description="Event type to publish")
    topic: Optional[str] = Field(default="action-requests", description="Topic for event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    reasoning: str = Field(..., description="Why this event should be published")


class CompleteAction(BaseModel):
    """Instruction to complete the plan."""
    
    action: PlanAction
    result: Dict[str, Any] = Field(..., description="Final result to return")
    reasoning: str = Field(..., description="Why the plan is now complete")


class WaitAction(BaseModel):
    """Instruction to pause and wait for external input."""
    
    action: PlanAction
    reason: str = Field(..., description="Why we're waiting")
    expected_event: Optional[str] = Field(default=None, description="What event we expect next")
    timeout_seconds: Optional[int] = Field(default=300, description="Timeout in seconds")


class DelegateAction(BaseModel):
    """Instruction to delegate to another planner."""
    
    action: PlanAction
    target_planner: str = Field(..., description="Name of planner to delegate to")
    goal_event: str = Field(..., description="Goal event to send")
    goal_data: Dict[str, Any] = Field(..., description="Goal parameters")
    reasoning: str = Field(..., description="Why delegation is appropriate")


# Union of all action types
PlannerAction = PublishAction | CompleteAction | WaitAction | DelegateAction


class PlannerDecision(BaseModel):
    """
    LLM decision on what to do next in a plan.
    
    This is the output of ChoreographyPlanner.reason_next_action().
    The SDK validates that referenced events exist before execution.
    """
    
    plan_id: str = Field(..., description="Plan being executed")
    current_state: str = Field(..., description="Current state in the plan")
    next_action: PlannerAction = Field(..., description="Action to take")
    alternative_actions: Optional[List[PlannerAction]] = Field(
        default=None,
        description="Alternative actions the planner considered"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this decision (0-1)"
    )
    reasoning: str = Field(..., description="LLM's reasoning for this decision")
    
    # Model configuration for JSON schema generation
    model_config = {
        "json_schema_extra": {
            "title": "Planner Decision",
            "description": "Decision on next action in plan execution",
        }
    }
```

**New File:** `sdk/python/soorma/ai/choreography.py`

```python
"""
ChoreographyPlanner - Autonomous orchestration using LLM reasoning.

ChoreographyPlanner is a high-level Planner that uses LLMs to autonomously
decide what to do next based on plan context and available events.

This is a simplified wrapper above the base Planner - developers write minimal code
while the framework handles event discovery, validation, and execution.

Usage:
    from soorma.ai.choreography import ChoreographyPlanner
    
    planner = ChoreographyPlanner(
        name="research-advisor",
        reasoning_model="gpt-4o",  # BYO model, uses OPENAI_API_KEY env var
    )
    
    @planner.on_goal("research.goal")
    async def handle_goal(goal, context):
        decision = await planner.reason_next_action(
            trigger=f"New goal: {goal.data['objective']}",
            context=context,
        )
        await planner.execute_decision(decision, context, goal_event=goal)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

from soorma.agents.planner import Planner
from soorma.context import PlatformContext
from soorma.plan_context import PlanContext
from soorma_common.decisions import PlannerDecision, PlanAction
from soorma_common.events import EventEnvelope


logger = logging.getLogger(__name__)


class ChoreographyPlanner(Planner):
    """
    Autonomous Planner that uses LLM reasoning for decision-making.
    
    Reduces boilerplate from ~400 lines (manual orchestration) to ~50 lines
    by automating:
    - Event discovery from Registry Service
    - LLM-based decision making
    - Event validation (prevent hallucinations)
    - Type-safe execution
    
    Attributes:
        reasoning_model: LLM model identifier (e.g., "gpt-4o", "claude-3-opus")
        api_key: Optional API key override (defaults to env var)
        api_base: Optional base URL for custom endpoints (e.g., Azure)
        temperature: Temperature for LLM generation (0-2)
        max_actions: Circuit breaker - max actions per plan (prevents runaway loops)
        system_instructions: Custom business logic/rules for LLM (optional)
        planning_strategy: Pre-configured strategy (balanced|conservative|aggressive)
        **llm_kwargs: Additional parameters passed to LiteLLM (e.g., max_tokens, top_p)
    """
    
    def __init__(
        self,
        name: str,
        reasoning_model: str = "gpt-4o",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        max_actions: int = 20,
        system_instructions: Optional[str] = None,
        planning_strategy: str = "balanced",
        **llm_kwargs,
    ):
        """
        Initialize ChoreographyPlanner with LLM configuration.
        
        Args:
            name: Planner name
            reasoning_model: LLM model identifier (e.g., "gpt-4o", "claude-3-opus", "ollama/llama2")
            api_key: Optional API key (if None, uses provider's env var)
            api_base: Optional base URL for custom LLM endpoints
            temperature: LLM temperature (lower = deterministic, higher = creative)
            max_actions: Circuit breaker limit for actions per plan
            system_instructions: Custom business logic for the LLM (e.g., compliance rules, domain expertise)
            planning_strategy: Pre-configured strategy ("balanced"|"conservative"|"aggressive")
            **llm_kwargs: Additional LiteLLM parameters (max_tokens, top_p, etc.)
            
        Raises:
            ImportError: If litellm is not installed
            
        Examples:
            # Using environment variables (recommended)
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="gpt-4o",  # Uses OPENAI_API_KEY from env
            )
            
            # Explicit API key
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="gpt-4o",
                api_key="sk-...",  # Direct key, not recommended for production
            )
            
            # Azure OpenAI
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="azure/my-gpt4-deployment",
                api_base="https://my-resource.openai.azure.com",
                api_key=os.environ["AZURE_API_KEY"],
            )
            
            # Local Ollama (no API key needed)
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="ollama/llama2",
            )
            
            # Custom business logic
            planner = ChoreographyPlanner(
                name="financial-advisor",
                reasoning_model="gpt-4o",
                system_instructions="""
                    You are a financial planning agent for a regulated banking platform.
                    CRITICAL RULES:
                    - Transactions >$5,000 require human approval (use WAIT action)
                    - Never auto-execute wire transfers (always DELEGATE to compliance-checker)
                    - Prioritize security over speed
                """,
                planning_strategy="conservative",
            )
        """
        super().__init__(name=name, description=f"Autonomous planner using {reasoning_model}")
        
        self.reasoning_model = reasoning_model
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature
        self.max_actions = max_actions
        self.system_instructions = system_instructions
        self.planning_strategy = planning_strategy
        self.llm_kwargs = llm_kwargs
        
        # Will be lazily imported to avoid hard dependency
        self._litellm = None
    
    async def reason_next_action(
        self,
        trigger: str,
        context: PlatformContext,
        plan_id: Optional[str] = None,
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> PlannerDecision:
        """
        Use LLM to decide the next action in the plan.
        
        This method:
        1. Discovers available events from Registry Service
        2. Builds a schema-based prompt
        3. Calls the configured LLM model
        4. Validates that referenced events exist
        5. Returns a type-safe PlannerDecision
        
        Args:
            trigger: What triggered this decision (e.g., "search.completed")
            context: PlatformContext for service access
            plan_id: Optional plan ID for decision tracking
            custom_context: Runtime-specific context for this decision (e.g., customer tier, inventory levels)
            
        Returns:
            PlannerDecision with next action to take
            
        Raises:
            ValueError: If referenced event doesn't exist in Registry
            ImportError: If litellm is not installed
            
        Examples:
            decision = await planner.reason_next_action(
                trigger="search.completed",
                context=context,
            )
            # Returns PlannerDecision with PUBLISH, COMPLETE, WAIT, or DELEGATE action
            
            # With custom runtime context
            decision = await planner.reason_next_action(
                trigger="order.received",
                context=context,
                custom_context={
                    "customer": {"tier": "premium", "region": "EU"},
                    "inventory": {"stock_level": "low"},
                },
            )
        """
        # Lazy import to avoid hard dependency
        if not self._litellm:
            try:
                import litellm
                self._litellm = litellm
            except ImportError:
                raise ImportError(
                    "litellm is required for ChoreographyPlanner. "
                    "Install with: pip install litellm"
                )
        
        # Discover available events from Registry
        events = await context.toolkit.discover_actionable_events(topic="action-requests")
        
        # Build schema-based prompt
        prompt = self._build_prompt(trigger, events, custom_context)
        
        # Call LLM with decision schema
        decision_schema = PlannerDecision.model_json_schema()
        
        # Use litellm for model-agnostic LLM calls
        response = await self._litellm.acompletion(
            model=self.reasoning_model,
            messages=[
                {"role": "system", "content": "You are a planning agent..."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            api_key=self.api_key,
            api_base=self.api_base,
            response_format={"type": "json_schema", "json_schema": decision_schema},
            **self.llm_kwargs,
        )
        
        # Parse response into PlannerDecision
        decision_data = response.choices[0].message.content
        decision = PlannerDecision.model_validate_json(decision_data)
        
        # Validate that referenced events exist
        await self._validate_decision_events(decision, events)
        
        return decision
    
    async def execute_decision(
        self,
        decision: PlannerDecision,
        context: PlatformContext,
        goal_event: Optional[EventEnvelope] = None,
    ) -> None:
        """
        Execute the decided action safely.
        
        This method dispatches based on action type:
        - PUBLISH: Publish event to action-requests topic
        - COMPLETE: Send response_event with results
        - WAIT: Create progress event
        - DELEGATE: Forward to another planner
        
        Args:
            decision: PlannerDecision from reason_next_action()
            context: PlatformContext for service access
            goal_event: Original goal event (for response routing)
            
        Raises:
            ValueError: If action validation fails
            
        Examples:
            await planner.execute_decision(decision, context, goal_event=goal)
        """
        action = decision.next_action
        
        if action.action == PlanAction.PUBLISH:
            # Publish new event to trigger workers
            await context.bus.publish(
                topic=action.topic or "action-requests",
                event_type=action.event_type,
                data=action.data,
            )
        
        elif action.action == PlanAction.COMPLETE:
            # Finalize plan with response
            if goal_event:
                await context.bus.respond(
                    event_type=goal_event.response_event,
                    correlation_id=goal_event.correlation_id,
                    data=action.result,
                )
        
        elif action.action == PlanAction.WAIT:
            # Publish progress/wait indicator
            await context.bus.publish(
                topic="system-events",
                event_type="plan.waiting_for_input",
                data={"reason": action.reason, "timeout": action.timeout_seconds},
            )
        
        elif action.action == PlanAction.DELEGATE:
            # Forward to another planner
            await context.bus.publish(
                topic="action-requests",
                event_type=action.goal_event,
                data=action.goal_data,
            )
    
    def _build_prompt(
        self, 
        trigger: str, 
        available_events: List[Any],
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build LLM prompt with available events schema and custom context.
        
        Args:
            trigger: Event that triggered this decision
            available_events: List of EventDefinition objects
            custom_context: Runtime-specific context for this decision
            
        Returns:
            Formatted prompt string with event schemas
        """
        # Format events for LLM (using EventToolkit's format_for_llm_selection)
        event_descriptions = "\n".join([
            f"- {e.event_name}: {e.description}" for e in available_events
        ])
        
        # System instructions (business logic)
        system_msg = self.system_instructions or "You are planning the next step in a workflow."
        
        # Planning strategy guidance
        strategy_guidance = self._get_strategy_guidance()
        
        # Custom context section
        context_section = ""
        if custom_context:
            import json
            context_section = f"""

Additional Context:
{json.dumps(custom_context, indent=2)}

Consider this context when making decisions.
"""
        
        return f"""
{system_msg}

{strategy_guidance}

Current Situation:
Trigger: {trigger}

Available events to publish:
{event_descriptions}
{context_section}

Decide on the next action:
- PUBLISH: Publish one of the above events
- COMPLETE: End the workflow with final result
- WAIT: Wait for external input
- DELEGATE: Forward to another planner

Respond with JSON matching the PlannerDecision schema.
"""
    
    def _get_strategy_guidance(self) -> str:
        """
        Return planning strategy-specific guidance.
        
        Returns:
            Strategy guidance text for LLM prompt
        """
        strategies = {
            "conservative": "Prioritize safety and compliance. When uncertain, use WAIT for human review.",
            "balanced": "Balance speed and safety. Use WAIT only for high-risk decisions.",
            "aggressive": "Prioritize speed and automation. Minimize WAIT actions.",
        }
        return strategies.get(self.planning_strategy, strategies["balanced"])
    
    async def _validate_decision_events(
        self,
        decision: PlannerDecision,
        available_events: List[Any],
    ) -> None:
        """
        Validate that decision references only existing events.
        
        This prevents LLM hallucinations.
        
        Args:
            decision: Decision to validate
            available_events: List of available events from Registry
            
        Raises:
            ValueError: If decision references non-existent event
        """
        if decision.next_action.action == PlanAction.PUBLISH:
            event_names = [e.event_name for e in available_events]
            if decision.next_action.event_type not in event_names:
                raise ValueError(
                    f"Event '{decision.next_action.event_type}' not in Registry. "
                    f"Available: {event_names}"
                )
```

### Business Logic Enhancements (Developer Experience)

Phase 2 includes two critical enhancements for production readiness:

#### **Enhancement 1: System Instructions (Init-Time Business Logic)**

**Problem:** Generic LLM prompts can't encode domain expertise, compliance rules, or business constraints.

**Solution:** `system_instructions` parameter for persistent business logic

**Use Cases:**
- **Financial Services:** "Never auto-approve transactions >$5,000. Always route to compliance for wire transfers."
- **Healthcare:** "Prioritize peer-reviewed sources. Include methodology validation in every search."
- **Manufacturing:** "Always check inventory before ordering. Prefer local suppliers for time-sensitive orders."
- **Customer Service:** "Escalate to human if sentiment is negative. Use friendly tone for consumers, formal for B2B."

**Implementation:**
```python
planner = ChoreographyPlanner(
    name="financial-advisor",
    reasoning_model="gpt-4o",
    system_instructions="""
        You are a financial planning agent for a regulated banking platform.
        
        CRITICAL RULES:
        - Transactions >$5,000 require human approval (use WAIT action)
        - Never auto-execute wire transfers (always DELEGATE to compliance-checker)
        - Log all decisions for audit trail
        - Prioritize security over speed
    """,
    planning_strategy="conservative",  # Affects prompt templates
)
```

**Effort:** 2 hours (parameter + prompt integration + 3 tests)

#### **Enhancement 2: Runtime Custom Context (Per-Decision Dynamic Context)**

**Problem:** Business decisions need runtime data (customer tier, inventory levels, regulatory context).

**Solution:** `custom_context` parameter in `reason_next_action()`

**Use Cases:**
- **E-commerce:** Customer tier ("premium" vs "basic") affects shipping priority
- **Healthcare:** Patient age/conditions affect treatment recommendations
- **Finance:** Transaction history affects fraud detection thresholds
- **Manufacturing:** Current inventory levels affect ordering decisions

**Implementation:**
```python
decision = await planner.reason_next_action(
    trigger="order.received",
    context=context,
    custom_context={
        "customer": {
            "tier": "premium",
            "lifetime_value": 50000,
            "region": "EU",
        },
        "inventory": {
            "stock_level": "low",
            "restock_eta": "3 days",
        },
    },
)
```

**Effort:** 1 hour (parameter + prompt injection + 2 tests)

#### **Enhancement 3: Prompt Template System (DEFERRED)**

**Status:** 🟡 Deferred to Stage 5 or Post-Launch  
**Tracking:** RF-SDK-019 in Master Plan Section 11  
**Reason:** Scope control - Enhancements 1 & 2 provide 80% of value  
**Effort:** 2-3 days (reusable templates, few-shot examples, template registry)

**Future Capabilities:**
- Domain-specific prompt templates (finance, healthcare, legal)
- Few-shot example integration for better reasoning
- Template versioning and A/B testing
- Jinja2-based template customization

**Why Defer:**
- Enhancements 1 & 2 satisfy immediate production needs
- Templating requires more design work (Jinja2 vs custom DSL)
- Can iterate based on real-world usage patterns

---

### SDK Layer Verification (Architecture Compliance)

**Two-Layer Pattern Check:**

- [x] **Service Clients (Layer 1):** 
  - Used indirectly via wrappers
  - RegistryClient.get_events_by_topic() - existing (discovery)
  - MemoryServiceClient.store_plan_context() - existing (persistence)
  - EventClient.publish() - existing (publication)
  
- [x] **PlatformContext Wrappers (Layer 2):**
  - context.toolkit (EventToolkit wrapper) - existing
  - context.bus.publish() - existing wrapper
  - context.bus.respond() - existing wrapper
  - context.memory.store_plan_context() - existing wrapper
  - **NO NEW WRAPPERS NEEDED** - Phase 2 uses only existing wrappers
  
- [x] **Agent Code (ChoreographyPlanner):**
  - Uses context.toolkit, context.bus, context.memory (✅ correct)
  - Does NOT import service clients directly (✅ correct)
  - Example patterns use wrappers only (✅ correct)

**Wrapper Completeness Checklist:**
- [x] context.toolkit.discover_events() - exists
- [x] context.toolkit.discover_actionable_events() - exists
- [x] context.bus.publish() - exists
- [x] context.bus.respond() - exists
- [x] context.memory.store_plan_context() - (from Phase 1)
- ✅ **VERDICT:** All required wrappers exist. No new wrappers needed.

### Event Schema

**Topic:** action-requests (existing)  
**New Event Types:** None (ChoreographyPlanner responds with existing event types)  
**Event Payload:** Defined by discovered events from Registry (dynamic)

### Dependency Changes

**New Dependency:** `litellm` (Apache 2.0 license)

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
litellm = "^1.36"  # Model-agnostic LLM interface
```

Rationale: LiteLLM provides:
- Support for 50+ LLM providers (OpenAI, Claude, Ollama, etc.)
- Unified API for different models
- Automatic fallback and retry logic
- Provider flexibility (developer's choice of model + credentials)

---

## 3. Task Tracking Matrix

### Task 1: DTO Design (soorma-common)

- [ ] **1.1:** Create `libs/soorma-common/src/soorma_common/decisions.py`
  - [ ] PlanAction enum (PUBLISH, COMPLETE, WAIT, DELEGATE)
  - [ ] PublishAction model
  - [ ] CompleteAction model
  - [ ] WaitAction model
  - [ ] DelegateAction model
  - [ ] PlannerDecision union type
  - [ ] PlannerDecision.model_json_schema() generation
  - **Est:** 4 hours | Status: 📋 Planned

- [ ] **1.2:** Update `libs/soorma-common/src/soorma_common/__init__.py`
  - [ ] Export new decision models
  - **Est:** 0.5 hours | Status: 📋 Planned

- [ ] **1.3:** TDD - Write DTO validation tests
  - [ ] test_plan_action_enum_values()
  - [ ] test_publishaction_validation()
  - [ ] test_planner_decision_discriminated_union()
  - [ ] test_planner_decision_json_schema()
  - **Est:** 2 hours | Status: 📋 Planned

### Task 2: ChoreographyPlanner Implementation

- [ ] **2.1:** Create `sdk/python/soorma/ai/choreography.py`
  - [ ] ChoreographyPlanner class extending Planner
  - [ ] __init__() with BYO model parameters + system_instructions + planning_strategy
  - [ ] reason_next_action() - event discovery + LLM reasoning + custom_context
  - [ ] execute_decision() - type-safe dispatch
  - [ ] _build_prompt() - schema generation + system instructions + custom context
  - [ ] _get_strategy_guidance() - strategy-specific prompts
  - [ ] _validate_decision_events() - hallucination prevention
  - **Est:** 6 hours | Status: 📋 Planned

- [ ] **2.2:** LiteLLM Integration
  - [ ] Add litellm to pyproject.toml dependencies
  - [ ] Handle lazy import for optional dependency support
  - [ ] Add informative error message if litellm missing
  - **Est:** 1 hour | Status: 📋 Planned

- [ ] **2.3:** TDD - Write ChoreographyPlanner tests
  - [ ] test_choreography_planner_initialization()
  - [ ] test_system_instructions_in_prompt()
  - [ ] test_custom_context_in_prompt()
  - [ ] test_planning_strategy_guidance()
  - [ ] test_reason_next_action_discovers_events()
  - [ ] test_reason_next_action_calls_litellm()
  - [ ] test_reason_next_action_validates_event_exists()
  - [ ] test_reason_next_action_raises_on_hallucination()
  - [ ] test_reason_next_action_with_custom_context()
  - [ ] test_execute_decision_publish()
  - [ ] test_execute_decision_complete()
  - [ ] test_execute_decision_wait()
  - [ ] test_execute_decision_delegate()
  - [ ] test_circuit_breaker_max_actions()
  - [ ] test_byo_model_credentials()
  - [ ] test_byo_model_azure_openai()
  - [ ] test_byo_model_local_ollama()
  - **Est:** 5 hours | Status: 📋 Planned

### Task 3: Integration & Validation

- [ ] **3.1:** Integration tests (end-to-end)
  - [ ] test_choreography_planner_autonomous_flow()
  - [ ] test_choreography_planner_with_plan_context()
  - [ ] test_decision_validation_prevents_hallucinations()
  - **Est:** 2 hours | Status: 📋 Planned

- [ ] **3.2:** Update CHANGELOG.md (soorma-common & SDK)
  - [ ] Document new decision types
  - [ ] Document ChoreographyPlanner addition
  - [ ] Note BYO model pattern
  - **Est:** 1 hour | Status: 📋 Planned

**Total Phase 2 Effort:** ~22 hours (3 days, 1 person)

**Enhancements Added:**
- ✅ Enhancement 1: System Instructions (business logic) - 2 hours
- ✅ Enhancement 2: Custom Context (runtime parameters) - 1 hour
- 🟡 Enhancement 3: Prompt Template System - Deferred to Phase 4+ (tracked in Master Plan)

---

## 4. TDD Strategy

### Test Structure

```
tests/
├── ai/
│   ├── test_decisions.py           # DTO validation tests
│   └── test_choreography.py        # ChoreographyPlanner logic
└── integration/
    └── test_choreography_e2e.py    # End-to-end flows
```

### Unit Tests: PlannerDecision Types

**File:** `tests/ai/test_decisions.py`

```python
import pytest
from soorma_common.decisions import (
    PlanAction, PlannerDecision,
    PublishAction, CompleteAction, WaitAction, DelegateAction
)

def test_plan_action_enum_values():
    """Verify PlanAction enum has all required actions."""
    assert PlanAction.PUBLISH.value == "publish"
    assert PlanAction.COMPLETE.value == "complete"
    assert PlanAction.WAIT.value == "wait"
    assert PlanAction.DELEGATE.value == "delegate"

def test_publishaction_validation():
    """PublishAction requires event_type and reasoning."""
    action = PublishAction(
        action=PlanAction.PUBLISH,
        event_type="search.requested",
        reasoning="Need to search for information",
    )
    assert action.event_type == "search.requested"
    assert action.topic == "action-requests"  # Default

def test_planner_decision_discriminated_union():
    """PlannerDecision correctly handles action discriminator."""
    scenarios = [
        (PublishAction(action=PlanAction.PUBLISH, event_type="...", reasoning="..."), PlanAction.PUBLISH),
        (CompleteAction(action=PlanAction.COMPLETE, result={}, reasoning="..."), PlanAction.COMPLETE),
        (WaitAction(action=PlanAction.WAIT, reason="...", reasoning="..."), PlanAction.WAIT),
        (DelegateAction(action=PlanAction.DELEGATE, target_planner="...", goal_event="...", goal_data={}, reasoning="..."), PlanAction.DELEGATE),
    ]
    for action, expected_type in scenarios:
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="search",
            next_action=action,
            reasoning="Test",
        )
        assert decision.next_action.action == expected_type

def test_planner_decision_json_schema():
    """PlannerDecision generates valid JSON schema for LLM."""
    schema = PlannerDecision.model_json_schema()
    assert "properties" in schema
    assert "next_action" in schema["properties"]
    assert "plan_id" in schema["properties"]
```

### Unit Tests: ChoreographyPlanner

**File:** `tests/ai/test_choreography.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.ai.choreography import ChoreographyPlanner
from soorma_common.decisions import PlannerDecision, PlanAction, PublishAction

@pytest.mark.asyncio
async def test_choreography_planner_initialization():
    """ChoreographyPlanner initializes with model and credentials."""
    planner = ChoreographyPlanner(
        name="test-planner",
        reasoning_model="gpt-4o",
        temperature=0.5,
        max_actions=25,
    )
    assert planner.name == "test-planner"
    assert planner.reasoning_model == "gpt-4o"
    assert planner.temperature == 0.5
    assert planner.max_actions == 25

@pytest.mark.asyncio
async def test_reason_next_action_discovers_events():
    """reason_next_action queries Registry for available events."""
    planner = ChoreographyPlanner(name="test")
    context = MagicMock()
    
    # Mock event discovery
    mock_events = [MagicMock(event_name="search.requested")]
    context.toolkit.discover_actionable_events = AsyncMock(return_value=mock_events)
    
    # Mock LLM response
    planner._litellm = MagicMock()
    planner._litellm.acompletion = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"plan_id":"p1","current_state":"s","next_action":{"action":"publish","event_type":"search.requested","reasoning":"search"},"reasoning":"test"}'))]
    ))
    
    decision = await planner.reason_next_action("trigger", context)
    
    # Verify event discovery
    context.toolkit.discover_actionable_events.assert_called_once()

@pytest.mark.asyncio
async def test_reason_next_action_validates_event_exists():
    """reason_next_action raises ValueError for hallucinated events."""
    planner = ChoreographyPlanner(name="test")
    context = MagicMock()
    
    # Only "real.event" exists
    mock_events = [MagicMock(event_name="real.event")]
    context.toolkit.discover_actionable_events = AsyncMock(return_value=mock_events)
    
    # Mock LLM returning non-existent event
    planner._litellm = MagicMock()
    planner._litellm.acompletion = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"next_action":{"action":"publish","event_type":"hallucinated.event"}}'))]
    ))
    
    with pytest.raises(ValueError, match="not in Registry"):
        await planner.reason_next_action("trigger", context)

@pytest.mark.asyncio
async def test_execute_decision_publish():
    """execute_decision publishes event for PUBLISH action."""
    planner = ChoreographyPlanner(name="test")
    context = MagicMock()
    context.bus.publish = AsyncMock()
    
    decision = PlannerDecision(
        plan_id="p1",
        current_state="s",
        next_action=PublishAction(
            action=PlanAction.PUBLISH,
            event_type="search.requested",
            data={"query": "ai"},
            reasoning="test",
        ),
        reasoning="test",
    )
    
    await planner.execute_decision(decision, context)
    context.bus.publish.assert_called_once()
```

### Integration Tests

**File:** `tests/integration/test_choreography_e2e.py`

```python
@pytest.mark.integration
async def test_choreography_planner_autonomous_flow():
    """End-to-end: Goal → Discovery → LLM → Execution."""
    # Setup: Real services or mocks
    context = create_test_context()  # Real Memory, Bus, Registry
    planner = ChoreographyPlanner(
        name="autonomous-test",
        reasoning_model="ollama/mistral",  # Local model for testing
    )
    
    # Goal arrives
    goal = GoalContext(
        event_type="research.goal",
        data={"topic": "AI agents"},
        correlation_id="corr-123",
    )
    
    # Planner reasons and executes
    decision = await planner.reason_next_action(f"Goal received: {goal.data}", context)
    await planner.execute_decision(decision, context, goal)
    
    # Verify: Event was published or plan completed
    # (Details depend on LLM decision, test verifies no exceptions)
```

---

## 5. Forward Deployed (FDE) Logic Decisions

### Decision 1: LLM Implementation - Build Full

**Question:** Should we implement litellm integration or defer to Phase 3?

**Decision:** ✅ **Build Full** (critical for DX)

**Rationale:**
- LLM integration IS the innovation of Phase 2
- Without it, ChoreographyPlanner has no value
- Effort is moderate (1-2 days with litellm)
- No service dependencies (local llama2 can work offline)

**FDE Alternative Considered:** Hardcode ChatGPT API → Rejected (violates BYO principle)

### Decision 2: Prompt Engineering - Minimal Version

**Decision:** 🟡 **Simple prompt, no few-shot examples**

**Rationale:**
- Start with basic schema-based prompts
- Few-shot learning can be added in Phase 4+ (post-launch)
- Current prompt sufficient for basic workflows
- Keeps Phase 2 scope tight (3 days)

**Deferred to Phase 4+:**
- Few-shot examples for common patterns
- Advanced prompt engineering
- Prompt templates for custom workflows

### Decision 3: Event Filtering - Build Full

**Decision:** ✅ **Implement _validate_decision_events()**

**Rationale:**
- Prevents LLM hallucinations (critical safety feature)
- Effort: 30 minutes
- No dependencies
- High impact on reliability

**FDE Alternative Considered:** Skip validation → Rejected (hallucinations break workflows)

### Decision 4: Circuit Breaker - Build Simple Version

**Decision:** ✅ **Build simple max_actions limit**

**Rationale:**
- Prevents infinite loops (safety critical)
- Implementation: 5 lines of code
- Defer complex state tracking to Phase 3+

**Implementation:**
```python
# In on_transition handler
if self.action_count >= self.max_actions:
    raise RuntimeError(f"Circuit breaker: max_actions ({self.max_actions}) exceeded")
```

---

## 6. Dependencies & Prerequisites

### Upstream (Must be complete before Phase 2)

- ✅ **Phase 1 (Foundation):** PlanContext, Planner decorators complete
- ✅ **EventToolkit:** Exists with discover_events() and discover_actionable_events()
- ✅ **PlatformContext:** Memory, Bus, Registry clients working
- ✅ **RegistryClient:** Events API functional

### New External Dependency

- ⏳ **litellm** (Apache 2.0) → Add to pyproject.toml

### No Service Dependencies Needed

- ❌ Tracker Service (not needed for Phase 2, deferred to Phase 3)
- ✅ Memory Service (existing, used for plan persistence)
- ✅ Registry Service (existing, used for event discovery)
- ✅ Event/Bus (existing, used for publication)

---

## 7. Architectural Mandates (AGENT.md Compliance)

### Specification-Driven Development

- ✅ Master Plan committed before Phase 2 starts
- ✅ This Action Plan documents all specifications
- ✅ TDD approach (tests before implementation)
- ✅ Architecture alignment verified (two-layer pattern)

### Two-Layer SDK Architecture (CRITICAL)

**Verified Compliance:**

| Layer | Component | Evidence |
|-------|-----------|----------|
| **Agent Code** | ChoreographyPlanner | Uses context.toolkit, context.bus - ✅ Correct |
| **Layer 2 Wrappers** | context.toolkit, context.bus | Existing wrappers used exclusively |
| **Layer 1 Clients** | RegistryClient, EventClient | Only accessed via wrappers |
| **Examples** | N/A (Phase 3) | Examples will use ChoreographyPlanner (no client imports) |

**Non-Negotiable Validation:**
- ✅ ChoreographyPlanner extends Planner (already correct abstraction)
- ✅ No direct service client imports in choreography.py
- ✅ All context access via PlatformContext wrappers
- ✅ BYO credentials (no hardcoded API keys)

### Authentication Context

- ✅ Context automatically passes tenant_id/user_id from event envelope
- ✅ No manual parameter passing required
- ✅ Wrapper delegates to service client with credentials
- ✅ v0.7.x uses custom headers (X-Tenant-ID, X-User-ID)

### Event Choreography (DisCo Pattern)

- ✅ Explicit response_event in published events
- ✅ Uses context.bus.respond() for goal responses
- ✅ No inferred event names
- ✅ correlation_id tracking for responses

### Testing Patterns

- ✅ Unit tests use mocks (no service clients)
- ✅ Integration tests use high-level wrappers only
- ✅ Service client testing in service repos only

---

## 8. Implementation Checklist

### Phase 2 Pre-Implementation (This Week)

- [ ] This Action Plan approved by developer
- [ ] litellm added to SDK dependencies (pyproject.toml)
- [ ] Test structure created (test files)

### Task 1: DTO Design

- [ ] RED: Write test_decisions.py with failing tests
- [ ] GREEN: Implement soorma_common/decisions.py
- [ ] REFACTOR: Validate Pydantic models, JSON schema generation
- [ ] Commit: "feat(common): Add PlannerDecision and PlanAction types (RF-SDK-015)"

### Task 2: ChoreographyPlanner Implementation

- [ ] RED: Write test_choreography.py with failing tests
- [ ] GREEN: Create soorma/ai/choreography.py
- [ ] GREEN: Implement reason_next_action() with custom_context parameter
- [ ] GREEN: Implement execute_decision()
- [ ] GREEN: Implement _build_prompt() with system_instructions and custom_context
- [ ] GREEN: Implement _get_strategy_guidance() for planning strategies
- [ ] GREEN: Implement _validate_decision_events()
- [ ] REFACTOR: Code cleanup, docstring review
- [ ] Commit: "feat(sdk): Add ChoreographyPlanner for autonomous orchestration (RF-SDK-016)"

### Task 3: Integration & Validation

- [ ] Write integration test suite
- [ ] Run all tests: 30+ tests passing
- [ ] Verify test coverage: 90%+ on new code
- [ ] Update CHANGELOG.md (SDK + soorma-common)
- [ ] Commit: "docs: Phase 2 implementation complete - ChoreographyPlanner available"

### Phase 2 Post-Implementation

- [ ] Code review (ensure two-layer pattern verified)
- [ ] Performance testing (LLM latency acceptable)
- [ ] Manual testing with real LLM (OpenAI or local Ollama)

---

## 9. Success Criteria (Detailed)

### Code Quality Gates

- [ ] All 30+ tests passing
- [ ] Test coverage: 90%+ on new code (decisions.py + choreography.py)
- [ ] mypy strict mode: zero errors
- [ ] All public methods have docstrings
- [ ] All functions have type hints (args + return)
- [ ] No service client imports in agent code

### Developer Experience Tests

- [ ] ChoreographyPlanner initialization takes <2 minutes
- [ ] Error messages guide developers to set API keys
- [ ] Documentation examples work (at least one example provided)
- [ ] BYO credentials work (OpenAI, Azure, Ollama)

### Architecture Integrity Checks

- [ ] Two-layer SDK pattern verified ✅
- [ ] No security gaps (credentials not logged)
- [ ] Event validation prevents hallucinations ✅
- [ ] Circuit breaker limits runaway loops ✅

---

## 10. Known Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LiteLLM API changes | Low | Medium | Pin version in pyproject.toml |
| LLM cost (users) | Medium | Medium | Clear docs on BYO credentials, env var setup |
| Hallucinated events | High | High | Event validation via Registry lookup ✅ |
| LLM offline | Medium | Low | Support local ollama, error message guides setup |
| JSON schema issues | Medium | Medium | Test schema generation thoroughly |

---

## 11. Related Documents

### Reference Docs
- [ARCHITECTURE_PATTERNS.md](../../../docs/ARCHITECTURE_PATTERNS.md) - Two-layer pattern, authentication
- [AGENT.md](../../../AGENT.md) - Developer constitution
- [Master Plan Phase 1](ACTION_PLAN_Stage4_Phase1_Foundation.md) - Completed Phase 1 (PlanContext)

### Research
- [LiteLLM Docs](https://docs.litellm.ai/) - Model provider integration
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) - Schema generation

---

**Status:** ✅ **Ready for Developer Review and Approval**

**Next Steps:**
1. Developer reviews this Action Plan
2. Developer approves specifications
3. Begin implementation (estimated 3 days)
4. Phase 2 completion feeds into Phase 3 (Validation/Examples)

