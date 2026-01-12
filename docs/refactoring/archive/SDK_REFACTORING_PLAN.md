# Soorma Python SDK Refactoring Plan

**Status:** 📋 Planning  
**Last Updated:** January 11, 2026  
**Authors:** Architecture Team  
**Review Status:** ✅ Comments Addressed (v4)

---

## 1. Executive Summary

This document outlines the refactoring plan for the Soorma Python SDK (`soorma-core`). The goal is to create a clean, progressive API that aligns with the DisCo (Distributed Cognition) architecture vision while providing an excellent developer experience.

**Key Principles:**
- Progressive complexity (simple → discoverable → autonomous)
- Explicit over implicit (no magic topic inference)
- Asynchronous-first design (event-driven, non-blocking)
- Industry standards where applicable (e.g., A2A Agent Card compatibility)
- TDD approach: tests define behavior before implementation
- Schema ownership: Result publisher owns result schema, requestor specifies event name
- **Common library (`soorma-common`) for shared DTOs** - State machine configs, A2A models, and service DTOs live in the common library; SDK provides convenience methods
- **Explicit event schemas over implicit inference** - While LLMs can generate/parse payloads through reasoning, explicit schemas provide consistency, predictability, and debuggability

---

## 2. Current State Analysis

### 2.1 SDK Structure (Current)
```
sdk/python/soorma/
├── agents/
│   ├── base.py      # Agent class - foundation
│   ├── planner.py   # Planner class - goal decomposition
│   ├── worker.py    # Worker class - task execution
│   └── tool.py      # Tool class - synchronous utilities
├── context.py       # PlatformContext (registry, memory, bus, tracker)
├── events.py        # EventClient (SSE streaming, publish)
├── models.py        # Re-exports from soorma-common
├── memory/          # Memory service client
├── registry/        # Registry service client  
└── ai/              # AI integration (EventToolkit)
```

### 2.2 Issues Identified

| Issue | Current Behavior | Impact | Priority |
|-------|-----------------|--------|----------|
| Topic inference | `BusClient._infer_topic()` guesses topic from event name | Implicit behavior, error-prone | 🔴 High |
| Synchronous task execution | `worker.on_task()` expects handler to return result (blocking) | Breaks async choreography pattern | 🔴 High |
| Event namespacing | Events are flat, not tied to agents | No ownership, hard to cleanup | 🟡 Medium |
| Tracker API calls | Workers call tracker service API directly | Should publish events instead | 🟡 Medium |
| Missing TaskContext persistence | Task context not saved to memory for async completion | Can't resume after delegation | 🔴 High |
| Response event specification | No way to specify which event to use for action results | Tight coupling, no dynamic routing | 🔴 High |

---

## 3. Agent Progression Model

### 3.1 Vision: Progressive Abstraction Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Autonomous Agents (Planner with LLM reasoning)        │
│  - planner.on_goal(), planner.on_transition()                   │
│  - Dynamic capability discovery, plan generation                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Async Task Agents (Worker)                            │
│  - worker.on_task(), worker.on_result()                         │
│  - Task decomposition, sub-agent delegation                     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Sync Tool Agents (Tool)                               │
│  - tool.on_invoke()                                             │
│  - Atomic, stateless operations                                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Base Agent (Primitive)                                │
│  - agent.on_event(topic, event_type)                            │
│  - Generic event handler, no assumptions                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Decorator Contracts

#### Layer 1: Base Agent
```python
from soorma.agents import Agent

agent = Agent(name="my-agent", capabilities=[...])

# Primitive: explicit topic + event_type, no magic
@agent.on_event(topic="business-facts", event_type="order.placed")
async def handle_order(event: Dict, context: PlatformContext):
    # Full control, raw event handling
    await context.bus.publish(
        topic="action-requests",  # ← EXPLICIT topic
        event_type="inventory.check",
        data={...}
    )
```

#### Layer 2: Tool (Synchronous)
```python
from soorma.agents import Tool

tool = Tool(name="calculator", capabilities=[...])

# Opinionated: listens on action-requests, publishes to action-results
# Response event NAME is specified by the caller in the request
# Response event SCHEMA is defined by the Tool (published in registry)
@tool.on_invoke(event_type="calculate.requested")
async def calculate(request: InvocationContext, context: PlatformContext) -> Dict:
    result = compute(request.data["expression"])
    return {"result": result}  # SDK publishes to request.response_event using Tool's schema
```

#### Layer 3: Worker (Asynchronous)
```python
from soorma.agents import Worker

worker = Worker(name="researcher", capabilities=[...])

# Opinionated: listens on action-requests
# Handler saves context and may delegate to sub-agents
@worker.on_task(event_type="research.requested")
async def handle_research(task: TaskContext, context: PlatformContext):
    # Save task context for async completion
    await task.save()  # Persists to working memory
    
    # IMPORTANT: Use task.delegate() instead of direct bus.publish()
    # delegate() manages memory state for async completion
    await task.delegate(
        event_type="web.search.requested",
        data={"query": task.data["topic"]},
        response_event="web.search.completed",
    )
    # Handler returns without result - async completion later

# Handler for sub-task results
@worker.on_result(event_type="web.search.completed")
async def handle_search_result(result: ResultContext, context: PlatformContext):
    # Restore task context
    task = await result.restore_task()
    
    # Check if ready to complete or need more sub-tasks
    if task.is_complete():
        await task.complete(result={"findings": result.data})
    else:
        # Chain to next sub-task
        await task.delegate(...)
```

> **⚠️ Important:** Always use `task.delegate()` instead of direct `context.bus.publish()` 
> for sub-task delegation. The `delegate()` method ensures task context is saved to memory
> before publishing, which is required for async completion in `on_result()` handlers.

#### Layer 4: Planner (Autonomous)
```python
from soorma.agents import Planner

planner = Planner(name="research-planner", capabilities=[...])

# Listens on action-requests for goal events
@planner.on_goal(event_type="research.goal")
async def plan_research(goal: GoalContext, context: PlatformContext):
    # Discover available agents/capabilities
    agents = await context.registry.discover(goal.requirements)
    
    # Generate plan using LLM reasoning
    plan = await planner.create_plan(goal, agents, context)
    
    # Save plan to working memory
    await plan.save()
    
    # Start first task
    await plan.execute_next()

# Listens to ALL events on action-requests AND action-results
@planner.on_transition()
async def handle_transition(event: EventContext, context: PlatformContext):
    # Restore plan context
    plan = await PlanContext.restore(event.correlation_id)
    
    # Update plan state based on event
    plan.update_state(event)
    
    # Determine next action
    if plan.is_complete():
        await plan.finalize()
    elif plan.has_next():
        await plan.execute_next()
    else:
        # LLM reasoning for dynamic plans
        await planner.reason_next_action(plan, event, context)
```

---

## 3.3 Design Rationale: Why Structured/Discoverable Patterns?

Our SDK supports three levels of event definition complexity:

| Level | Pattern | Event Definition | Payload Handling |
|-------|---------|------------------|------------------|
| **Simple** | String names | `"order.placed"` | Caller knows schema at compile time |
| **Structured** | EventDefinition | `EventDefinition(name=..., schema=...)` | Schema registered, validated |
| **Discoverable** | Capability-based | `AgentCapability(consumed_event=..., produced_events=...)` | LLM discovers and generates payloads |

**Why not just use Simple (string names)?**

In the request/response pattern, callers need to construct payloads. They have two options:

1. **Compile-time knowledge (tight coupling):**
   - Caller hardcodes the payload structure
   - Works for internal, well-known integrations
   - Breaks when producer changes schema

2. **LLM-based dynamic generation:**
   - LLM generates payloads based on registered EventDefinition schemas
   - LLM parses responses based on registered schemas
   - Enables loose coupling and runtime discovery

**Why explicit schemas even with LLMs?**

While LLMs can reason about payload structures, explicit schemas provide:

| Benefit | Without Schema | With Schema |
|---------|---------------|-------------|
| **Consistency** | LLM may vary structure | Guaranteed structure |
| **Predictability** | Output varies per invocation | Reproducible results |
| **Debuggability** | "LLM generated something wrong" | "Field X doesn't match type Y" |
| **Validation** | Hope it works | Fail fast on schema mismatch |
| **Documentation** | Read the agent's code | Browse registry for contracts |

**Example: LLM payload generation with schema**

```python
# Without schema - LLM guesses based on event name
prompt = "Generate payload for 'order.validate' event"
# LLM might return: {"order_id": "123"} or {"orderId": "123"} or {"id": "123"}

# With schema - LLM follows contract
schema = await registry.get_event_schema("order.validate")
prompt = f"Generate payload matching schema: {schema}"
# LLM returns: {"order_id": "123", "items": [...]} - matches schema exactly
```

**Recommendation:** Start simple, graduate to structured/discoverable as needs grow:

1. **Simple:** Prototyping, internal tools, known contracts
2. **Structured:** Production services, cross-team integration
3. **Discoverable:** Multi-agent orchestration, LLM-driven workflows

---

## 4. Refactoring Tasks

### 4.1 Phase 1: Foundation (Breaking Changes)

#### RF-SDK-001: Remove Topic Inference from BusClient
**Priority:** 🔴 High  
**Files:** [context.py](../sdk/python/soorma/context.py#L705-L718)

**Current:**
```python
# BusClient._infer_topic() - REMOVE THIS
def _infer_topic(self, event_type: str) -> str:
    if event_type.endswith(".requested"):
        return "action-requests"
    # ... magic inference
```

**Target:**
```python
async def publish(
    self,
    topic: str,          # ← REQUIRED, no default
    event_type: str,
    data: Dict[str, Any],
    correlation_id: Optional[str] = None,
    response_event: Optional[str] = None,  # ← NEW
) -> str:
```

#### Convenience Methods for Request/Response Pattern

To enforce contracts and reduce boilerplate, provide dedicated methods for action topics:

```python
class BusClient:
    async def request(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,  # ← REQUIRED for requests
        correlation_id: Optional[str] = None,
        response_topic: str = "action-results",  # Default
    ) -> str:
        """
        Publish to action-requests topic with mandatory response_event.
        Enforces the request/response contract.
        """
        return await self.publish(
            topic="action-requests",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            response_event=response_event,
            response_topic=response_topic,
        )
    
    async def respond(
        self,
        event_type: str,  # The response_event from original request
        data: Dict[str, Any],
        correlation_id: str,  # ← REQUIRED for responses
        topic: str = "action-results",  # Default
    ) -> str:
        """
        Publish to action-results topic with mandatory correlation_id.
        Enforces response correlation contract.
        """
        return await self.publish(
            topic=topic,
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
        )
    
    async def announce(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish to business-facts topic for domain events/observations.
        No response expected.
        """
        return await self.publish(
            topic="business-facts",
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
        )
```

**Usage Examples:**
```python
# Action request (requires response_event)
await context.bus.request(
    event_type="research.requested",
    data={"topic": "AI trends"},
    response_event="research.completed",
)

# Action response (requires correlation_id)
await context.bus.respond(
    event_type="research.completed",
    data={"findings": [...]},
    correlation_id=request.correlation_id,
)

# Business fact announcement (no response needed)
await context.bus.announce(
    event_type="order.placed",
    data={"order_id": "123"},
)
```

**Tests to Add:**
- `test_publish_requires_topic()` - raises if topic not provided
- `test_publish_with_response_event()` - includes response_event in envelope

---

#### RF-SDK-002: Add Response Event to Action Requests
**Priority:** 🔴 High  
**Files:** [context.py](../sdk/python/soorma/context.py), [events.py](../sdk/python/soorma/events.py)

**Rationale:** When publishing an action request, the caller must specify which event type the callee should use for the response. This enables dynamic routing and decouples request/response contracts.

**Current Event Envelope:**
```python
{
    "id": "evt_123",
    "type": "research.requested",
    "topic": "action-requests",
    "data": {...},
    "correlation_id": "corr_456"
}
```

**Target Event Envelope:**
```python
{
    "id": "evt_123",
    "type": "research.requested",
    "topic": "action-requests",
    "data": {...},
    "correlation_id": "corr_456",
    "response_event": "research.completed",  # ← NEW
    "response_topic": "action-results"       # ← NEW (optional, defaults to action-results)
}
```

**Tests to Add:**
- `test_action_request_includes_response_event()`
- `test_tool_publishes_to_specified_response_event()`
- `test_worker_publishes_to_specified_response_event()`

---

#### RF-SDK-003: Refactor on_event() Signature
**Priority:** 🔴 High  
**Files:** [base.py](../sdk/python/soorma/agents/base.py#L277-L306)

**Current:**
```python
@agent.on_event("data.requested")  # Only event_type
async def handler(event, context): ...
```

**Target:**
```python
@agent.on_event(topic="action-requests", event_type="data.requested")
async def handler(event, context): ...

# OR for convenience with defaults
@agent.on_event("data.requested", topic="business-facts")  # topic has default
```

**Discussion Point:**
- Option A: Always require topic (explicit)
- Option B: Require topic for base Agent, higher abstractions (Worker, Tool) have defaults
- **Recommendation:** Option B - progressive disclosure

---

### 4.2 Phase 2: Async Task Handling

#### RF-SDK-004: Worker Async Task Model
**Priority:** 🔴 High  
**Files:** [worker.py](../sdk/python/soorma/agents/worker.py)

**Current Issue:** `_handle_action_request()` expects handler to return result synchronously:
```python
# Current - BLOCKING
result = await handler(task, context)
await context.bus.publish("action.result", data={"result": result})
```

**Target Design:**

1. **TaskContext with persistence:**
```python
@dataclass
class TaskContext:
    task_id: str
    event_type: str
    plan_id: str
    data: Dict[str, Any]
    response_event: str      # ← NEW: from request envelope
    response_topic: str      # ← NEW: from request envelope
    sub_tasks: Dict[str, SubTaskInfo]  # ← NEW: track delegated sub-tasks
    state: Dict[str, Any]    # ← NEW: task-specific state
    
    # Authentication context (from platform context / token)
    tenant_id: str
    user_id: str
    agent_id: str
    
    async def save(self):
        """Persist task context to working memory for async completion."""
        await self._context.memory.store_task_context(
            task_id=self.task_id,
            plan_id=self.plan_id,
            context=self.to_dict(),
        )
    
    async def delegate(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
    ) -> str:
        """
        Delegate to sub-agent (sequential chaining).
        
        Uses string event_type and dict data for progressive complexity:
        - Simple agents use str + dict directly
        - Advanced agents convert EventDefinition to these arguments
        
        Returns sub_task_id for tracking.
        """
        sub_task_id = str(uuid4())
        self.sub_tasks[sub_task_id] = SubTaskInfo(
            sub_task_id=sub_task_id,
            event_type=event_type,
            response_event=response_event,
            status="pending",
        )
        await self.save()  # ← CRITICAL: Save before publish for async resume
        
        await self._context.bus.request(
            event_type=event_type,
            data=data,
            response_event=response_event,
            correlation_id=sub_task_id,
        )
        return sub_task_id
    
    async def delegate_parallel(
        self,
        sub_tasks: List[DelegationSpec],
    ) -> str:
        """
        Delegate multiple sub-tasks in parallel (fan-out).
        
        Args:
            sub_tasks: List of DelegationSpec(event_type, data, response_event)
        
        Returns:
            parallel_group_id for tracking this fan-out group
        """
        parallel_group_id = str(uuid4())
        
        for spec in sub_tasks:
            sub_task_id = str(uuid4())
            self.sub_tasks[sub_task_id] = SubTaskInfo(
                sub_task_id=sub_task_id,
                event_type=spec.event_type,
                response_event=spec.response_event,
                status="pending",
                parallel_group_id=parallel_group_id,
            )
        
        await self.save()  # ← Save all sub-tasks before publishing
        
        # Publish all in parallel
        for sub_task_id, info in self.sub_tasks.items():
            if info.parallel_group_id == parallel_group_id:
                spec = next(s for s in sub_tasks if s.event_type == info.event_type)
                await self._context.bus.request(
                    event_type=info.event_type,
                    data=spec.data,
                    response_event=info.response_event,
                    correlation_id=sub_task_id,
                )
        
        return parallel_group_id
    
    def aggregate_parallel_results(self, parallel_group_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if all sub-tasks in a parallel group completed and aggregate results.
        
        Returns:
            Aggregated results if all complete, None if still pending
        """
        group_tasks = [
            info for info in self.sub_tasks.values()
            if info.parallel_group_id == parallel_group_id
        ]
        
        if all(t.status == "completed" for t in group_tasks):
            return {t.sub_task_id: t.result for t in group_tasks}
        return None
    
    def update_sub_task_result(self, sub_task_id: str, result: Dict[str, Any]):
        """Update a sub-task with its result (called from on_result handler)."""
        if sub_task_id in self.sub_tasks:
            self.sub_tasks[sub_task_id].status = "completed"
            self.sub_tasks[sub_task_id].result = result
    
    def is_complete(self) -> bool:
        """Check if all sub-tasks have completed."""
        return all(info.status == "completed" for info in self.sub_tasks.values())
    
    async def complete(self, result: Dict[str, Any]):
        """
        Complete the task and publish result.
        
        The result schema should match what's registered in Registry for response_event.
        For Tools: Schema is predefined by the Tool at registration time.
        For Workers with LLM: Can use LLM to generate result matching registry schema.
        """
        await self._context.bus.respond(
            event_type=self.response_event,
            data={
                "task_id": self.task_id,
                "status": "completed",
                "result": result,
            },
            correlation_id=self.task_id,
            topic=self.response_topic,
        )
        # Cleanup task context
        await self._context.memory.delete_task_context(self.task_id)


@dataclass
class SubTaskInfo:
    """Tracking info for a delegated sub-task."""
    sub_task_id: str
    event_type: str
    response_event: str
    status: str  # pending, completed, failed
    parallel_group_id: Optional[str] = None  # For fan-out groups
    result: Optional[Dict[str, Any]] = None


@dataclass  
class DelegationSpec:
    """Specification for a parallel delegation."""
    event_type: str
    data: Dict[str, Any]
    response_event: str
```

2. **Parallel Fan-out / Fan-in Example:**
```python
@worker.on_task(event_type="analyze.requested")
async def handle_analyze(task: TaskContext, context: PlatformContext):
    # Fan-out: Delegate to multiple workers in parallel
    group_id = await task.delegate_parallel([
        DelegationSpec("sentiment.analyze", {"text": task.data["text"]}, "sentiment.completed"),
        DelegationSpec("entity.extract", {"text": task.data["text"]}, "entity.completed"),
        DelegationSpec("topic.classify", {"text": task.data["text"]}, "topic.completed"),
    ])
    
    # Store group_id in task state for aggregation
    task.state["pending_group"] = group_id
    await task.save()

@worker.on_result(event_type="sentiment.completed")
@worker.on_result(event_type="entity.completed")
@worker.on_result(event_type="topic.completed")
async def handle_analysis_result(result: ResultContext, context: PlatformContext):
    task = await result.restore_task()
    
    # Update sub-task result
    task.update_sub_task_result(result.correlation_id, result.data)
    
    # Check if all parallel tasks completed (fan-in)
    group_id = task.state.get("pending_group")
    aggregated = task.aggregate_parallel_results(group_id)
    
    if aggregated:
        # All done - complete the original task
        await task.complete(result={
            "sentiment": aggregated[...]["result"],
            "entities": aggregated[...]["result"],
            "topics": aggregated[...]["result"],
        })
    else:
        # Still waiting for other sub-tasks
        await task.save()
```

3. **Worker with on_result() decorator:**
```python
class Worker(Agent):
    def on_task(self, event_type: str):
        """Register handler for incoming tasks (action-requests)."""
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                task = TaskContext.from_event(event, context)
                await func(task, context)
                # NOTE: No automatic result publishing - handler manages completion
            return func
        return decorator
    
    def on_result(self, event_type: str):
        """Register handler for sub-task results (action-results)."""
        def decorator(func):
            @self.on_event(topic="action-results", event_type=event_type)
            async def wrapper(event, context):
                result = ResultContext.from_event(event, context)
                await func(result, context)
            return func
        return decorator
```

4. **ResultContext for restoring task:**
```python
@dataclass
class ResultContext:
    """Context for handling sub-task results."""
    event_type: str
    correlation_id: str  # sub_task_id
    data: Dict[str, Any]
    success: bool
    error: Optional[str]
    
    async def restore_task(self) -> TaskContext:
        """
        Restore the parent task context from memory.
        
        Uses correlation_id (sub_task_id) to find the parent task.
        """
        # Look up which task this sub-task belongs to
        task_data = await self._context.memory.get_task_by_subtask(
            self.correlation_id
        )
        return TaskContext.from_dict(task_data, self._context)
```

**Tests to Add:**
- `test_task_context_save_restore()`
- `test_worker_delegates_to_sub_agent()`
- `test_worker_completes_after_sub_task_result()`
- `test_worker_chains_multiple_sub_tasks()`

---

#### RF-SDK-005: Tool Synchronous Model (Simplify)
**Priority:** 🟡 Medium  
**Files:** [tool.py](../sdk/python/soorma/agents/tool.py)

**Current:** Uses `tool.request` / `tool.response` events (non-standard)

**Target:** Use same `action-requests` / `action-results` topics but with synchronous handler model.

**Key Design Decision: Schema Ownership Pattern**

For all request/response patterns:
- **Request event name:** Provided by the requestor (caller)
- **Response event name:** Provided by the requestor (caller) via `response_event` field
- **Request payload schema:** Defined by the responder (Tool/Worker) at registration
- **Response payload schema:** Defined by the responder (Tool/Worker) at registration

This pattern means:
1. Tools/Workers **must** define both `consumed_event` (request schema) AND `produced_events` (response schema) in their capabilities
2. Callers with LLM can dynamically generate/parse payloads matching the registry schemas
3. Callers without LLM work with predefined schemas they know at compile time

---
1. **Tool with on_invoke() decorator:**
```python
class Tool(Agent):
    def on_invoke(self, event_type: str):
        """Register handler for tool invocations."""
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                request = InvocationContext.from_event(event, context)
                
                try:
                    result = await func(request, context)
                    
                    # Auto-publish result using caller-specified event name
                    # but Tool's registered response schema
                    await context.bus.respond(
                        event_type=request.response_event,
                        data={
                            "request_id": request.request_id,
                            "success": True,
                            "result": result,
                        },
                        correlation_id=request.correlation_id,
                        topic=request.response_topic,
                    )
                except Exception as e:
                    await context.bus.respond(
                        event_type=request.response_event,
                        data={
                            "request_id": request.request_id,
                            "success": False,
                            "error": str(e),
                        },
                        correlation_id=request.correlation_id,
                        topic=request.response_topic,
                    )
            return func
        return decorator
```

2. **Tool declaration example:**
```python
# Tool registration with explicit schemas
CALCULATOR_CAPABILITY = AgentCapability(
    task_name="calculate",
    description="Performs mathematical calculations",
    consumed_event=EventDefinition(
        event_name="calculate.requested",  # Or any name caller provides
        topic="action-requests",
        description="Request a calculation",
        payload_schema={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression"},
            },
            "required": ["expression"]
        }
    ),
    produced_events=[
        EventDefinition(
            event_name="calculate.completed",  # Schema for any response_event
            topic="action-results", 
            description="Calculation result",
            payload_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "number"},
                    "expression": {"type": "string"},
                },
                "required": ["result"]
            }
        )
    ]
)

tool = Tool(
    name="calculator",
    capabilities=[CALCULATOR_CAPABILITY],
)
```

3. **Caller using Tool's schema dynamically:**
```python
@worker.on_task(event_type="math.problem")
async def handle_math(task: TaskContext, context: PlatformContext):
    # Discover calculator tool
    calc = await context.registry.find("calculate")
    
    # Get the schema for invoking this capability
    request_schema = calc.get_consumed_event_schema("calculate")
    response_schema = calc.get_produced_event_schema("calculate")
    
    # If Worker has LLM, can generate payload dynamically
    # If not, must know schema at compile time
    await task.delegate(
        event_type=request_schema.event_name,  # Or any name
        data={"expression": "2 + 2"},  # Must match request_schema (use LLM for dynamic schema)
        response_event="my.calc.done",  # Caller chooses name
    )

@worker.on_result(event_type="my.calc.done")
async def handle_calc_result(result: ResultContext, context: PlatformContext):
    # Result payload follows Tool's response_schema
    # Caller must handle according to that schema
    calc_result = result.data["result"]
```

---

### 4.3 Phase 3: Planner & State Machine

#### RF-SDK-006: Planner on_goal() and on_transition()
**Priority:** 🟡 Medium  
**Files:** [planner.py](../sdk/python/soorma/agents/planner.py)

**Current Issue:** Planner creates plan and publishes all tasks immediately. No support for:
- Dynamic plan generation with LLM
- Event-based state transition handling
- Result aggregation
- Re-entrant plans for long-running conversations

**Target Design:**

```python
@dataclass
class PlanContext:
    plan_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    response_event: str  # NEW: Explicit response event from goal request
    status: str  # pending, running, completed, failed, paused
    
    # State machine with event-based transitions
    state_machine: Dict[str, StateConfig]  # state_name -> StateConfig
    current_state: str
    results: Dict[str, Any]  # Aggregated results from steps
    
    # For re-entrant / long-running plans (see Q4)
    parent_plan_id: Optional[str] = None  # For nested sub-plans
    session_id: Optional[str] = None  # Conversation/session context
    
    # Authentication context
    user_id: str
    tenant_id: str
    
    async def save(self):
        """Persist plan to working memory."""
        await self._context.memory.store_plan_context(
            plan_id=self.plan_id,
            session_id=self.session_id,
            context=self.to_dict(),
        )
    
    @classmethod
    async def restore(cls, plan_id: str, context: PlatformContext):
        """Restore plan from working memory."""
        data = await context.memory.get_plan_context(plan_id)
        return cls.from_dict(data, context)
    
    @classmethod
    async def restore_by_correlation(cls, correlation_id: str, context: PlatformContext):
        """Restore plan that has a task with this correlation_id."""
        data = await context.memory.get_plan_by_correlation(correlation_id)
        return cls.from_dict(data, context) if data else None
    
    def get_next_state(self, event: EventContext) -> Optional[str]:
        """
        Determine next state based on current state AND received event.
        
        A state may have multiple outgoing transitions based on different events.
        This is the key insight: state transitions are event-driven.
        """
        current_config = self.state_machine.get(self.current_state)
        if not current_config:
            return None
        
        # Find transition matching the received event
        for transition in current_config.transitions:
            if transition.on_event == event.event_type:
                # Optionally evaluate condition
                if transition.condition:
                    if not self._evaluate_condition(transition.condition, event):
                        continue
                return transition.to_state
        
        return None
    
    async def execute_next(self, trigger_event: Optional[EventContext] = None):
        """
        Execute the next step based on current state and triggering event.
        
        Args:
            trigger_event: The event that triggered this transition (for conditional routing)
        """
        # Determine next state based on event
        if trigger_event:
            next_state = self.get_next_state(trigger_event)
        else:
            # Initial execution - get first state after 'start'
            start_config = self.state_machine.get("start")
            next_state = start_config.default_next if start_config else None
        
        if not next_state:
            return  # No valid transition
        
        state_config = self.state_machine.get(next_state)
        if not state_config:
            return
        
        # Execute the action for this state
        if state_config.action:
            await self._context.bus.request(
                event_type=state_config.action.event_type,
                data=self._interpolate_data(state_config.action.data or {}),
                response_event=state_config.action.response_event,
                correlation_id=self.plan_id,
            )
        
        self.current_state = next_state
        self.status = "running"
        await self.save()
    
    def is_complete(self) -> bool:
        """Check if plan reached a terminal state."""
        current_config = self.state_machine.get(self.current_state)
        return current_config and current_config.is_terminal
    
    async def finalize(self, result: Optional[Dict[str, Any]] = None):
        """Complete the plan and publish final result using the specified response_event."""
        self.status = "completed"
        self.results["final"] = result
        
        # Use the response_event specified in the original goal request
        # This follows our request/response pattern: requestor specifies event name
        await self._context.bus.respond(
            event_type=self.response_event,  # Use explicit response_event, not derived
            data={"plan_id": self.plan_id, "result": result},
            correlation_id=self.parent_plan_id or self.plan_id,
        )
        
        await self.save()  # Keep for history
    
    async def pause(self, reason: str = "user_input_required"):
        """Pause the plan (e.g., waiting for HITL)."""
        self.status = "paused"
        self.state["pause_reason"] = reason
        await self.save()
    
    async def resume(self, input_data: Dict[str, Any]):
        """Resume a paused plan with new input."""
        self.status = "running"
        self.results["user_input"] = input_data
        await self.save()
        await self.execute_next()


@dataclass
class StateConfig:
    """Configuration for a state in the plan state machine."""
    state_name: str
    description: str
    action: Optional[StateAction] = None  # Action to execute on entering state
    transitions: List[StateTransition] = field(default_factory=list)
    default_next: Optional[str] = None  # For unconditional transitions
    is_terminal: bool = False


@dataclass
class StateTransition:
    """A transition from one state to another based on an event."""
    on_event: str  # Event type that triggers this transition
    to_state: str  # Target state
    condition: Optional[str] = None  # Optional condition expression


@dataclass
class StateAction:
    """Action to execute when entering a state."""
    event_type: str
    response_event: str
    data: Optional[Dict[str, Any]] = None
```

> **📦 Common Library Note:** The `StateConfig`, `StateTransition`, and `StateAction` 
> dataclasses will live in `soorma-common` as Pydantic DTOs. This allows:
> - State Tracker service to reuse the same DTOs for API contracts
> - SDK to import and use them for plan configuration
> - Consistent serialization for plan registration and storage
>
> See [RF-SDK-012: Common Library DTOs](#rf-sdk-012-common-library-dtos) for details.

**Example: State Machine with Event-Based Transitions**
```python
# State machine where transitions depend on the received event
state_machine = {
    "start": StateConfig(
        state_name="start",
        description="Initial state",
        default_next="searching",
    ),
    "searching": StateConfig(
        state_name="searching",
        description="Searching for information",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
            data={"query": "{goal_data.topic}"},
        ),
        transitions=[
            # Different events lead to different states
            StateTransition(on_event="web.search.completed", to_state="analyzing"),
            StateTransition(on_event="web.search.failed", to_state="retry_search"),
            StateTransition(on_event="web.search.no_results", to_state="ask_user"),
        ]
    ),
    "retry_search": StateConfig(
        state_name="retry_search",
        description="Retry with broader query",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
            data={"query": "{goal_data.topic}", "broad": True},
        ),
        transitions=[
            StateTransition(on_event="web.search.completed", to_state="analyzing"),
            StateTransition(on_event="web.search.failed", to_state="failed"),
        ]
    ),
    "ask_user": StateConfig(
        state_name="ask_user",
        description="Ask user for clarification",
        action=StateAction(
            event_type="notification.human_input",
            response_event="user.clarification.provided",
            data={"question": "No results found. Can you provide more details?"},
        ),
        transitions=[
            StateTransition(on_event="user.clarification.provided", to_state="searching"),
        ]
    ),
    "analyzing": StateConfig(
        state_name="analyzing",
        description="Analyzing search results",
        action=StateAction(
            event_type="content.analyze.requested",
            response_event="content.analyze.completed",
        ),
        transitions=[
            StateTransition(on_event="content.analyze.completed", to_state="done"),
        ]
    ),
    "done": StateConfig(
        state_name="done",
        description="Plan completed successfully",
        is_terminal=True,
    ),
    "failed": StateConfig(
        state_name="failed",
        description="Plan failed",
        is_terminal=True,
    ),
}
```

**Planner with on_goal() and on_transition() decorators:**
```python
class Planner(Agent):
    def on_goal(self, event_type: str):
        """Register handler for goal events."""
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                goal = GoalContext.from_event(event, context)
                await func(goal, context)
            return func
        return decorator
    
    def on_transition(self):
        """
        Register handler for ALL state transitions.
        Called for any event on action-requests or action-results
        where correlation_id matches a known plan.
        """
        def decorator(func):
            # Subscribe to both topics
            @self.on_event(topic="action-requests", event_type="*")
            @self.on_event(topic="action-results", event_type="*")
            async def wrapper(event, context):
                correlation_id = event.get("correlation_id")
                if not correlation_id:
                    return
                
                # Check if we have a plan for this correlation
                plan = await PlanContext.restore(correlation_id, context)
                if plan:
                    transition = TransitionContext(event=event, plan=plan)
                    await func(transition, context)
            return func
        return decorator
    
    async def create_plan(
        self,
        goal: GoalContext,
        agents: List[AgentDefinition],
        context: PlatformContext,
    ) -> PlanContext:
        """
        Create a plan using LLM reasoning.
        
        This method discovers available agents, their capabilities,
        and generates a state machine for achieving the goal.
        """
        # Implementation uses AI toolkit for LLM reasoning
        pass
    
    async def reason_next_action(
        self,
        plan: PlanContext,
        event: EventContext,
        context: PlatformContext,
    ) -> Optional[str]:
        """
        Use LLM to decide next action for dynamic plans.
        
        Returns the event_type to publish, or None if plan is complete.
        """
        # Implementation uses AI toolkit for LLM reasoning
        pass
```

---

### 4.4 Phase 4: Event & Agent Discovery

#### RF-SDK-007: Event Registration Tied to Agent
**Priority:** 🟡 Medium  
**Files:** [context.py](../sdk/python/soorma/context.py), Registry Service

**Current:** Events registered flat, no ownership relationship

**Target:** Events registered as part of agent registration, with agent_id as owner

```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # ← Full definition, not just name
    produced_events: List[EventDefinition]  # ← Full definitions
```

**Registry Service Changes:**
- Store `agent_id` as owner of events
- On agent deregistration, optionally cleanup owned events
- Query events by owning agent

---

#### RF-SDK-008: Agent Discovery by Capability (A2A Alignment)
**Priority:** 🟡 Medium  
**Files:** [context.py](../sdk/python/soorma/context.py#L54-L107)

**Current:** `registry.find(capability)` returns agent info

**Target:** Enhanced discovery for LLM reasoning, aligned with A2A Agent Card standard

**A2A Agent Card Compatibility Analysis:**

The [A2A (Agent-to-Agent) protocol](https://google.github.io/agent-to-agent/) defines an "Agent Card" for discovery. Here's how our models align:

| A2A Agent Card Field | Soorma Equivalent | Notes |
|---------------------|-------------------|-------|
| `name` | `AgentDefinition.name` | ✅ Direct match |
| `description` | `AgentDefinition.description` | ✅ Direct match |
| `url` | N/A (we use events, not HTTP) | ⚠️ Different paradigm |
| `provider` | `AgentDefinition.tenant_id` | ✅ Maps to tenant |
| `version` | Add to `AgentDefinition` | 🔧 Need to add |
| `capabilities` | `AgentCapability` list | ✅ Similar concept |
| `skills` | `AgentCapability.task_name` + description | ✅ Maps to capabilities |
| `inputModes` / `outputModes` | Event schemas | ⚠️ Different approach |
| `authentication` | Platform-level (not per-agent) | ⚠️ Different approach |

**Recommendation:** Provide compatibility layer, not full A2A compliance
- Our event-driven model is fundamentally different from A2A's HTTP-based model
- We can export Agent Cards for interop, but internal model stays event-centric
- Add `version` field to `AgentDefinition` for better alignment
- **A2A conversion handled by `A2AGatewayHelper`** (see [RF-SDK-012](#rf-sdk-012-common-library-dtos)), not RegistryClient

```python
class RegistryClient:
    async def discover(
        self,
        requirements: List[str],  # Capability requirements
        include_events: bool = True,  # Include event schemas
    ) -> List[DiscoveredAgent]:
        """
        Discover agents matching requirements.
        
        Returns agents with their capabilities AND the event schemas
        needed to communicate with them.
        """
        pass
    
    # NOTE: A2A Agent Card export is handled by A2AGatewayHelper.agent_to_card()
    # in the gateway module, not here. This keeps RegistryClient focused on
    # internal discovery while gateway handles external protocol translation.

@dataclass
class DiscoveredAgent:
    agent_id: str
    name: str
    description: str
    version: str  # Added for A2A alignment
    capabilities: List[AgentCapability]
    
    def get_consumed_event_schema(self, capability: str) -> EventDefinition:
        """Get the request event definition for invoking a capability."""
        for cap in self.capabilities:
            if cap.task_name == capability:
                return cap.consumed_event
        return None
    
    def get_produced_event_schema(self, capability: str) -> Optional[EventDefinition]:
        """Get the response event definition for a capability."""
        for cap in self.capabilities:
            if cap.task_name == capability and cap.produced_events:
                return cap.produced_events[0]
        return None
```

#### A2A Gateway Pattern

For external-facing "gateway" agents, we'll expose A2A-compatible HTTP endpoints while internally using our event-driven architecture:

```
External Client (HTTP/A2A)           Gateway Service              Internal Agents (Events)
        │                                  │                              │
        │  POST /.well-known/agent.json    │                              │
        │─────────────────────────────────>│                              │
        │  (A2A Agent Card)                │                              │
        │<─────────────────────────────────│                              │
        │                                  │                              │
        │  POST /tasks/send                │                              │
        │  (A2A Task, OAuth/API Key)       │                              │
        │─────────────────────────────────>│                              │
        │                                  │  action.request (events)     │
        │                                  │─────────────────────────────>│
        │                                  │                              │
        │                                  │  action.result (events)      │
        │                                  │<─────────────────────────────│
        │  (A2A Task Response)             │                              │
        │<─────────────────────────────────│                              │
```

**Implementation Notes:**
- A2A DTOs (`AgentCard`, `Task`, `Message`, etc.) live in `soorma-common`
- Gateway service translates HTTP ↔ events
- SDK provides helper methods for gateway implementation

```python
# In soorma-common/a2a.py (new file)
from pydantic import BaseModel

class A2AAgentCard(BaseModel):
    """A2A Agent Card - industry standard for agent discovery."""
    name: str
    description: str
    url: str  # Gateway URL
    version: str
    provider: Dict[str, str]
    capabilities: Dict[str, Any]
    skills: List[A2ASkill]
    authentication: A2AAuthentication  # OAuth2, API Key, etc.

class A2ASkill(BaseModel):
    id: str
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]]

class A2ATask(BaseModel):
    """A2A Task - standard task format."""
    id: str
    sessionId: Optional[str]
    message: A2AMessage
    
class A2AMessage(BaseModel):
    role: str  # "user"
    parts: List[A2APart]

# SDK method to help gateway services
class GatewayHelper:
    """Helper for implementing A2A-compatible gateway services."""
    
    @staticmethod
    def task_to_event(task: A2ATask, agent_id: str) -> ActionRequestEvent:
        """Convert A2A Task to internal action-request event."""
        pass
    
    @staticmethod
    def event_to_task_response(event: ActionResultEvent) -> A2ATaskResponse:
        """Convert internal action-result to A2A response."""
        pass
```

> **📦 Common Library Note:** A2A DTOs will live in `soorma-common/a2a.py`.
> The SDK's `GatewayHelper` class provides convenience methods for translation.
> See [RF-SDK-012: Common Library DTOs](#rf-sdk-012-common-library-dtos) for details.

---

### 4.5 Phase 5: Memory SDK Methods

#### RF-SDK-010: Memory SDK Alignment with Service Endpoints
**Priority:** 🟡 Medium  
**Files:** [context.py](../sdk/python/soorma/context.py), Memory Service

**Memory Service Endpoints vs SDK Methods:**

| Service Endpoint | SDK Method | Notes |
|-----------------|------------|-------|
| `POST /v1/memory/task-context` | `memory.store_task_context()` | NEW |
| `GET /v1/memory/task-context/{id}` | `memory.get_task_context()` | NEW |
| `DELETE /v1/memory/task-context/{id}` | `memory.delete_task_context()` | NEW |
| `GET /v1/memory/task-context/by-subtask/{id}` | `memory.get_task_by_subtask()` | NEW |
| `POST /v1/memory/plan-context` | `memory.store_plan_context()` | NEW |
| `GET /v1/memory/plan-context/{id}` | `memory.get_plan_context()` | NEW |
| `POST /v1/memory/plans` | `memory.create_plan()` | NEW - Create plan record |
| `GET /v1/memory/plans` | `memory.list_plans()` | Query active/historic |
| `POST /v1/memory/sessions` | `memory.create_session()` | NEW - Create session record |
| `GET /v1/memory/sessions` | `memory.list_sessions()` | Query conversations |
| `POST /v1/working-memory/{plan_id}` | `memory.store()` | Existing |
| `GET /v1/working-memory/{plan_id}/{key}` | `memory.retrieve()` | Existing |

**Authentication Context:**
- `tenant_id`, `user_id`, `agent_id` are derived from the authentication token
- SDK extracts these from `PlatformContext` which is initialized with auth
- Memory Service validates token and uses RLS policies based on extracted IDs
- SDK methods do NOT need to pass these as explicit parameters

```python
class MemoryClient:
    """
    Memory service client.
    
    Authentication context (tenant_id, user_id) is derived from the platform
    context's authentication token. All operations are automatically scoped
    to the authenticated user's tenant.
    """
    
    # === Task Context (for async Worker completion) ===
    
    async def store_task_context(
        self,
        task_id: str,
        plan_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """Store task context for async completion."""
        # tenant_id/user_id from auth token
        pass
    
    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task context."""
        pass
    
    async def delete_task_context(self, task_id: str) -> bool:
        """Delete task context after completion."""
        pass
    
    async def get_task_by_subtask(self, sub_task_id: str) -> Optional[Dict[str, Any]]:
        """Find parent task by sub-task correlation ID."""
        pass
    
    # === Plan Context (for Planner state machine) ===
    
    async def store_plan_context(
        self,
        plan_id: str,
        session_id: Optional[str],
        context: Dict[str, Any],
    ) -> bool:
        """Store plan context."""
        pass
    
    async def get_plan_context(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve plan context."""
        pass
    
    async def get_plan_by_correlation(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Find plan by task/step correlation ID."""
        pass
    
    # === Plans & Sessions Management ===
    
    async def create_plan(
        self,
        goal_event: str,
        goal_data: Dict[str, Any],
        response_event: str,
        session_id: Optional[str] = None,
        parent_plan_id: Optional[str] = None,
    ) -> PlanSummary:
        """
        Create a new plan record.
        
        Called when a Planner receives a goal and creates a plan.
        Returns the created plan with generated plan_id.
        """
        pass
    
    async def create_session(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionSummary:
        """
        Create a new session/conversation record.
        
        Sessions group related plans and provide conversation context.
        """
        pass
    
    async def list_plans(
        self,
        status: Optional[str] = None,  # active, completed, failed, paused
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlanSummary]:
        """
        List plans for the authenticated user.
        
        Sessions represent conversation threads. Plans may be grouped by session.
        """
        pass
    
    async def list_sessions(
        self,
        limit: int = 20,
    ) -> List[SessionSummary]:
        """
        List active sessions/conversations for the authenticated user.
        
        A session groups related plans and interactions over time.
        """
        pass
    
    # === Working Memory (plan-scoped key-value) ===
    
    async def store(
        self,
        key: str,
        value: Any,
        plan_id: str,
    ) -> bool:
        """Store key-value in plan-scoped working memory."""
        pass
    
    async def retrieve(
        self,
        key: str,
        plan_id: str,
    ) -> Optional[Any]:
        """Retrieve value from plan-scoped working memory."""
        pass


@dataclass
class PlanSummary:
    """Summary of a plan for listing."""
    plan_id: str
    goal_event: str
    status: str
    session_id: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class SessionSummary:
    """Summary of a session for listing."""
    session_id: str
    plan_count: int
    created_at: str
    last_activity: str
```

**Sessions vs Plans:**
- **Session:** A conversation/interaction thread. Can contain multiple plans.
- **Plan:** A specific goal execution. Belongs to one session (optional).
- In a chatbot scenario:
  - Each conversation topic = one session
  - Each user goal within that conversation = one plan
  - Multiple plans can be active within a session

---

### 4.6 Phase 6: Remove Tracker API Calls

#### RF-SDK-011: Tracker via Events, Not API
**Priority:** 🟡 Medium  
**Files:** [worker.py](../sdk/python/soorma/agents/worker.py#L264-L280), [context.py](../sdk/python/soorma/context.py#L799-L900)

**Current Issue:** Workers call `context.tracker.emit_progress()` directly

**Target:** Workers publish events on `system-events` topic, Tracker service subscribes

```python
# Worker publishes (no direct API call)
await context.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={
        "plan_id": task.plan_id,
        "task_id": task.task_id,
        "status": "running",
        "progress": 0.5,
    },
)

# Tracker service subscribes to system-events topic
# and updates its database based on events
```

**TrackerClient Changes:**
- Keep for reading (query plan status, history)
- Remove write methods (emit_progress, complete_task, fail_task)
- SDK publishes events instead

---

### 4.7 Phase 7: Common Library DTOs

#### RF-SDK-012: Common Library DTOs
**Priority:** 🟡 Medium  
**Files:** `soorma-common/models.py`, `soorma-common/a2a.py` (new), `soorma-common/state.py` (new)

**Goal:** Move shared DTOs to `soorma-common` so services and SDK share the same contracts.

**Current `soorma-common` Exports:**
```python
# Already in soorma-common (from our earlier exploration)
from soorma_common import (
    # Agent Registry
    AgentCapability, AgentDefinition, AgentRegistrationRequest, ...
    # Event Registry  
    EventDefinition, EventRegistrationRequest, ...
    # Memory Service
    SemanticMemoryCreate, EpisodicMemoryCreate, ...
    # Event Envelopes
    EventEnvelope, ActionRequestEvent, ActionResultEvent, ...
)
```

**New DTOs to Add:**

**1. State Machine DTOs (`soorma-common/state.py`):**
```python
# Used by Planner SDK AND State Tracker Service
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class StateAction(BaseModel):
    """Action to execute when entering a state."""
    event_type: str = Field(..., description="Event to publish")
    response_event: str = Field(..., description="Expected response event")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event payload template")

class StateTransition(BaseModel):
    """A transition from one state to another."""
    on_event: str = Field(..., description="Event type that triggers this transition")
    to_state: str = Field(..., description="Target state name")
    condition: Optional[str] = Field(default=None, description="Optional condition expression")

class StateConfig(BaseModel):
    """Configuration for a state in the plan state machine."""
    state_name: str = Field(..., description="Unique state identifier")
    description: str = Field(..., description="Human-readable description")
    action: Optional[StateAction] = Field(default=None, description="Action on state entry")
    transitions: List[StateTransition] = Field(default_factory=list)
    default_next: Optional[str] = Field(default=None, description="For unconditional transitions")
    is_terminal: bool = Field(default=False, description="Whether this is a terminal state")

class PlanDefinition(BaseModel):
    """Definition of a plan's state machine - used for registration."""
    plan_type: str = Field(..., description="Type of plan (e.g., 'research.plan')")
    description: str = Field(..., description="Plan description")
    initial_state: str = Field(default="start", description="Starting state")
    states: Dict[str, StateConfig] = Field(..., description="State machine definition")

class PlanRegistrationRequest(BaseModel):
    """Request to register a plan type with State Tracker."""
    plan: PlanDefinition

class PlanInstanceRequest(BaseModel):
    """Request to create a new plan instance."""
    plan_type: str
    goal_data: Dict[str, Any]
    session_id: Optional[str] = None
    parent_plan_id: Optional[str] = None
```

**2. A2A Compatibility DTOs (`soorma-common/a2a.py`):**
```python
# For external-facing gateway agents
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum

class A2AAuthType(str, Enum):
    API_KEY = "apiKey"
    OAUTH2 = "oauth2"
    NONE = "none"

class A2AAuthentication(BaseModel):
    """A2A authentication configuration."""
    schemes: List[A2AAuthType]
    credentials: Optional[str] = None  # URL for OAuth discovery

class A2ASkill(BaseModel):
    """A2A Skill - maps to our AgentCapability."""
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    inputSchema: Optional[Dict[str, Any]] = None  # JSON Schema
    outputSchema: Optional[Dict[str, Any]] = None  # JSON Schema

class A2AAgentCard(BaseModel):
    """
    A2A Agent Card - industry standard for agent discovery.
    
    Ref: https://google.github.io/agent-to-agent/
    """
    name: str
    description: str
    url: str  # Gateway URL for this agent
    version: str = "1.0.0"
    provider: Dict[str, str] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    skills: List[A2ASkill] = Field(default_factory=list)
    authentication: A2AAuthentication

class A2APart(BaseModel):
    """Part of an A2A message."""
    type: Literal["text", "data", "file"]
    text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    mimeType: Optional[str] = None

class A2AMessage(BaseModel):
    """A2A Message in a task."""
    role: Literal["user", "agent"]
    parts: List[A2APart]

class A2ATask(BaseModel):
    """A2A Task - standard task format for external requests."""
    id: str
    sessionId: Optional[str] = None
    message: A2AMessage
    metadata: Optional[Dict[str, Any]] = None

class A2ATaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class A2ATaskResponse(BaseModel):
    """A2A Task Response."""
    id: str
    sessionId: Optional[str] = None
    status: A2ATaskStatus
    message: Optional[A2AMessage] = None
    error: Optional[str] = None
```

**SDK Re-exports:**
```python
# sdk/python/soorma/models.py - add new imports
from soorma_common import (
    # ... existing ...
    # State Machine (new)
    StateConfig, StateTransition, StateAction,
    PlanDefinition, PlanRegistrationRequest,
    # A2A (new)  
    A2AAgentCard, A2ATask, A2ATaskResponse, A2ASkill, A2AAuthentication,
)
```

**SDK Convenience Classes:**
```python
# sdk/python/soorma/gateway.py (new)
from soorma_common import A2AAgentCard, A2ATask, A2ATaskResponse
from soorma_common import ActionRequestEvent, ActionResultEvent

class A2AGatewayHelper:
    """Helper for implementing A2A-compatible gateway services."""
    
    @staticmethod
    def agent_to_card(
        agent: AgentDefinition,
        gateway_url: str,
        auth: A2AAuthentication,
    ) -> A2AAgentCard:
        """Convert internal AgentDefinition to A2A Agent Card."""
        return A2AAgentCard(
            name=agent.name,
            description=agent.description,
            url=gateway_url,
            version=agent.version or "1.0.0",
            provider={"organization": agent.tenant_id or "soorma"},
            capabilities={
                "streaming": False,
                "pushNotifications": True,
            },
            skills=[
                A2ASkill(
                    id=cap.task_name,
                    name=cap.task_name,
                    description=cap.description,
                    inputSchema=cap.consumed_event.payload_schema if hasattr(cap, 'consumed_event') else None,
                )
                for cap in agent.capabilities
            ],
            authentication=auth,
        )
    
    @staticmethod
    def task_to_event(
        task: A2ATask,
        event_type: str,
        response_event: str,
    ) -> ActionRequestEvent:
        """Convert A2A Task to internal action-request event."""
        # Extract text/data from message parts
        data = {}
        for part in task.message.parts:
            if part.type == "text":
                data["text"] = part.text
            elif part.type == "data":
                data.update(part.data or {})
        
        return ActionRequestEvent(
            source="gateway",
            type=event_type,
            data=data,
            correlation_id=task.id,
            session_id=task.sessionId,
            response_event=response_event,
        )
    
    @staticmethod
    def event_to_response(
        event: ActionResultEvent,
        task_id: str,
    ) -> A2ATaskResponse:
        """Convert internal action-result to A2A response."""
        if event.success:
            return A2ATaskResponse(
                id=task_id,
                status=A2ATaskStatus.COMPLETED,
                message=A2AMessage(
                    role="agent",
                    parts=[A2APart(type="data", data=event.result)],
                ),
            )
        else:
            return A2ATaskResponse(
                id=task_id,
                status=A2ATaskStatus.FAILED,
                error=event.error,
            )
```

---

## 5. SDK Progression Summary

### 5.1 Event Complexity Progression

| Level | Events | Agent Registration |
|-------|--------|-------------------|
| **Simple** | String event names, hardcoded | `events_consumed=["order.placed"]` |
| **Structured** | `EventDefinition` with schemas | `events_consumed=[ORDER_EVENT]` |
| **Discoverable** | Events tied to capabilities | `capabilities=[OrderCapability]` |

### 5.2 Agent Complexity Progression

| Level | Agent Type | Decorator | Behavior |
|-------|-----------|-----------|----------|
| **Primitive** | `Agent` | `@agent.on_event(topic, event_type)` | Raw event handling |
| **Sync Tool** | `Tool` | `@tool.on_invoke(event_type)` | Request/response, auto-publish |
| **Async Worker** | `Worker` | `@worker.on_task()` + `@worker.on_result()` | Task delegation, async completion |
| **Autonomous** | `Planner` | `@planner.on_goal()` + `@planner.on_transition()` | LLM reasoning, state machine |

---

## 6. Migration Guide

### 6.1 Breaking Changes

1. **Topic required in publish():**
   ```python
   # Before
   await context.bus.publish("order.created", data={...})
   
   # After
   await context.bus.publish(
       topic="business-facts",
       event_type="order.created",
       data={...}
   )
   # Or use convenience method
   await context.bus.announce("order.created", data={...})
   ```

2. **on_event() requires topic:**
   ```python
   # Before
   @agent.on_event("order.created")
   
   # After
   @agent.on_event(topic="business-facts", event_type="order.created")
   ```

3. **Worker handlers don't return result:**
   ```python
   # Before
   @worker.on_task("process")
   async def handle(task, ctx):
       return {"result": "done"}  # ← SDK published automatically
   
   # After
   @worker.on_task("process")
   async def handle(task, ctx):
       # ... do work, potentially delegate ...
       await task.complete({"result": "done"})  # ← Explicit completion
   ```

4. **Tool/Worker events unified:**
   - `tool.request` → use `action-requests` topic
   - `tool.response` → use `action-results` topic

5. **Use delegate() not direct publish() for sub-tasks:**
   ```python
   # Before (problematic - no memory persistence)
   await context.bus.publish(
       topic="action-requests",
       event_type="sub.task",
       ...
   )
   
   # After (correct - saves task context first)
   await task.delegate(
       event_type="sub.task",
       data={...},
       response_event="sub.task.done",
   )
   ```

---

## 7. Open Questions

### Q1: Event Registration Ownership ✅ RESOLVED
**Question:** Should events always be registered within capabilities, even for simple agents?

**Options:**
- A) Always within capabilities (consistent but more verbose for simple cases)
- B) Support both flat and capability-nested (flexible but inconsistent)
- C) Flat for simple, nested for discoverable (progressive but two models)

**Decision:** Option C - aligns with progressive complexity model

---

### Q2: HITL (Human-in-the-Loop) Events ✅ RESOLVED
**Question:** Should HITL use `action-requests` / `action-results` or dedicated `notifications` topic?

**Options:**
- A) Use `notifications` topic with user-agent consuming
- B) Use `action-requests` with special event types
- C) New `hitl-requests` / `hitl-responses` topics

**Decision:** Option A - keeps action topics for agent-to-agent

**HITL Flow Clarification:**

When a Worker (not Planner) needs human input during task execution:

```
Worker (executing task)                User-Agent Service              Human
        │                                    │                           │
        │ notification.human_input           │                           │
        │ (correlation_id=task_id)           │                           │
        │───────────────────────────────────>│                           │
        │                                    │   Push/display question   │
        │                                    │──────────────────────────>│
        │                                    │                           │
        │                                    │   Human response          │
        │ {response_event} on notifications  │<──────────────────────────│
        │<───────────────────────────────────│                           │
        │                                    │                           │
    (Worker continues task)                  │                           │
```

**Workers can directly send HITL requests** - no need to notify Planner first:
```python
@worker.on_task(event_type="document.review.requested")
async def handle_review(task: TaskContext, context: PlatformContext):
    # Worker needs human approval - TIME-BOUND waiting
    await context.bus.publish(
        topic="notification-events",
        event_type="notification.human_input",
        data={
            "question": "Please review this document",
            "document_url": task.data["url"],
            "response_event": "document.approval.received",
            "timeout_seconds": 3600,  # 1 hour timeout - Worker HITL is time-bound
        },
        correlation_id=task.task_id,  # Links back to this task
    )
    await task.save()  # Save state while waiting

@worker.on_result(event_type="document.approval.received")
async def handle_approval(result: ResultContext, context: PlatformContext):
    task = await result.restore_task()
    if result.data["approved"]:
        await task.complete({"status": "approved"})
    else:
        await task.complete({"status": "rejected", "reason": result.data["reason"]})
```

**Plan-Level Pause vs Worker-Level HITL - Key Distinction:**

| Aspect | Plan-Level Pause | Worker-Level HITL |
|--------|------------------|-------------------|
| **Timeout** | Extended/indefinite (no timeout) | Time-bound (`timeout_seconds` required) |
| **Scope** | Entire plan execution halts | Single task waits, plan may continue other branches |
| **Use Case** | External approvals, compliance gates | User input, confirmations, clarifications |
| **Tracker Handling** | Normal pause state | Timeout treated as exception/failure |
| **Example** | Budget approval, legal review | "Is this correct?", "Which option?" |

**Worker HITL timeout handling by Tracker Service:**
```python
# Tracker service monitors HITL requests with timeout_seconds
# If timeout expires before response:
# 1. Emits task.timeout event
# 2. Marks task as failed with reason="hitl_timeout"
# 3. Plan can have transition for timeout events
```

**When to use Planner's pause/resume:**
- `plan.pause()` is for **plan-level** waiting - can be extended/indefinite
- Use when the plan itself (not a worker task) needs external gate
- No automatic timeout - resumes only via explicit external event

```python
# Planner pauses plan (not individual task) for approval
async def handle_transition(transition, context):
    plan = transition.plan
    
    if plan.current_state == "awaiting_budget_approval":
        await plan.pause(reason="budget_approval_required")
        # Plan is now paused - will resume when external event arrives

# Resume is triggered by external event (e.g., webhook → event)
@planner.on_event(topic="business-facts", event_type="budget.approved")
async def handle_approval(event, context):
    plan = await PlanContext.restore_by_correlation(event.correlation_id)
    if plan and plan.status == "paused":
        await plan.resume({"approved_amount": event.data["amount"]})
```

---

### Q3: State Tracker Coupling
**Question:** Can Planner state transitions be implemented without State Tracker service?

**Analysis:** Yes, for MVP:
- Plan state stored in Working Memory
- Planner handles transitions via `on_transition()` decorator
- State Tracker service provides observability (read-only) later

---

### Q4: Re-entrant Plans for Long-Running Conversations
**Question:** Does the data model support re-entrant plans for chatbot-like use cases?

**Requirements:**
1. User can have long-running conversation on a topic with multiple sub-goals
2. Plans can pause (e.g., waiting for human input) and resume
3. User can have multiple parallel conversations (different goals)
4. Plans can be nested (sub-plans for complex goals)

**Design Support:**

```python
@dataclass
class PlanContext:
    # Re-entrancy support
    parent_plan_id: Optional[str]  # For nested sub-plans
    session_id: Optional[str]      # Groups related plans in conversation
    status: str                    # Includes 'paused' state
    
    # Pause/resume methods
    async def pause(self, reason: str): ...
    async def resume(self, input_data: Dict): ...
```

**Session Model:**
```
User (tenant_id + user_id)
├── Session A (conversation about "AI research")
│   ├── Plan A1 (goal: "find papers") - completed
│   ├── Plan A2 (goal: "summarize findings") - running
│   │   └── Sub-plan A2.1 (delegated sub-goal) - running
│   └── Plan A3 (goal: "draft report") - pending (depends on A2)
│
├── Session B (conversation about "budget planning")
│   └── Plan B1 (goal: "analyze expenses") - paused (waiting for input)
```

**Key Points:**
1. Plans can reference `parent_plan_id` for nesting
2. Plans grouped by `session_id` for conversation context
3. `status: paused` allows waiting for HITL without losing state
4. Memory service queries support filtering by session and status

---

### Q5: Schema Validation at Runtime
**Question:** Should SDK validate payloads against registry schemas?

**Options:**
- A) No validation (trust producer/consumer)
- B) Validate on publish (fail fast)
- C) Validate on receive (protective)
- D) Both publish and receive

**Current Leaning:** Option B for action-requests (catch errors early), no validation for business-facts (loose coupling)

---

## 8. References

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Platform architecture
- [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) - Agent design patterns
- [EVENT_PATTERNS.md](EVENT_PATTERNS.md) - Event-driven patterns
- [TOPICS.md](TOPICS.md) - Topic definitions
- [A2A Agent Card](https://google.github.io/agent-to-agent/) - Industry standard for agent discovery
