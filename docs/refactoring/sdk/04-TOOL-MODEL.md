# SDK Refactoring: Tool Model

**Document:** 04-TOOL-MODEL.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 2)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Task** | RF-SDK-005: Tool Synchronous Model |
| **Files** | `sdk/python/soorma/agents/tool.py` |
| **Dependencies** | 01-EVENT-SYSTEM |
| **Blocks** | None |
| **Estimated Effort** | 1-2 days |

---

## Context

### Why This Matters

Tools are the **simplest agent type** - synchronous request/response:

1. Tool receives invocation request
2. Tool executes handler synchronously
3. Handler returns result
4. Decorator auto-publishes result to `response_event`

### Current State

- Uses custom `tool.request` / `tool.response` topics (non-standard)
- Should use standard `action-requests` / `action-results` topics

### Key Files

```
sdk/python/soorma/
└── agents/
    └── tool.py         # Tool class, on_invoke
```

### Prerequisite Concepts

From **01-EVENT-SYSTEM** (must complete first):
- `bus.respond()` - Publish result to caller's `response_event`
- Topic routing on `action-requests` / `action-results`

### Tool vs Worker

| Aspect | Tool | Worker |
|--------|------|--------|
| Handler Model | Sync - returns result | Async - manages completion |
| State | Stateless | Stateful (TaskContext) |
| Delegation | Cannot delegate | Can delegate to sub-agents |
| Result | Auto by decorator | Manual via `task.complete()` |

---

## Summary

This document covers the synchronous Tool model:
- **RF-SDK-005:** Tool Synchronous Model with `on_invoke()` decorator

This is a simpler pattern than Worker, designed for stateless request/response operations.

---

## Tasks

### RF-SDK-005: Tool Synchronous Model

**Files:** [tool.py](../../sdk/python/soorma/agents/tool.py)

#### Current Issue

Uses custom `tool.request` / `tool.response` events (non-standard topics).

#### Target

Use same `action-requests` / `action-results` topics but with synchronous handler model. Tool decorator auto-publishes response.

---

## Schema Ownership Pattern

**Key Design Decision:** For all request/response patterns:

| Element | Owner | Notes |
|---------|-------|-------|
| Request event name | Requestor (caller) | Caller chooses the name |
| Response event name | Requestor (caller) | Via `response_event` field |
| Request payload schema | Responder (Tool/Worker) | Defined at registration |
| Response payload schema | Responder (Tool/Worker) | Defined at registration |

This pattern means:
1. Tools/Workers **must** define both `consumed_event` (request schema) AND `produced_events` (response schema) in capabilities
2. Callers with LLM can dynamically generate/parse payloads matching the registry schemas
3. Callers without LLM work with predefined schemas they know at compile time

---

## Target Design

### 1. InvocationContext

```python
@dataclass
class InvocationContext:
    """Context for tool invocation (lighter than TaskContext)."""
    request_id: str
    event_type: str
    correlation_id: str
    data: Dict[str, Any]
    response_event: str   # ← Caller-specified response event name
    response_topic: str   # ← Usually "action-results"
    
    # Authentication context
    tenant_id: str
    user_id: str
    
    @classmethod
    def from_event(cls, event: EventContext, context: PlatformContext):
        return cls(
            request_id=event.data.get("request_id", str(uuid4())),
            event_type=event.event_type,
            correlation_id=event.data.get("correlation_id"),
            data=event.data,
            response_event=event.data.get("response_event"),
            response_topic=event.data.get("response_topic", "action-results"),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
```

### 2. Tool Class with on_invoke() Decorator

```python
class Tool(Agent):
    def on_invoke(self, event_type: str):
        """
        Register handler for tool invocations.
        
        Unlike Worker, Tool handlers are synchronous:
        - Handler returns result directly
        - Decorator auto-publishes result to response_event
        - No state persistence needed
        """
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

---

## Usage Examples

### Tool Declaration with Schema

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

### Simple Tool Handler

```python
@tool.on_invoke(event_type="calculate.requested")
async def handle_calculate(request: InvocationContext, context: PlatformContext):
    """
    Synchronous handler - just return the result.
    Decorator handles publishing to response_event.
    """
    expr = request.data["expression"]
    result = eval(expr)  # In real code, use safe evaluation
    return {"result": result, "expression": expr}
```

### Caller Using Tool Dynamically

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
        data={"expression": "2 + 2"},  # Must match request_schema
        response_event="my.calc.done",  # Caller chooses name
    )

@worker.on_result(event_type="my.calc.done")
async def handle_calc_result(result: ResultContext, context: PlatformContext):
    # Result payload follows Tool's response_schema
    # Caller must handle according to that schema
    calc_result = result.data["result"]
```

---

## Tool vs Worker Comparison

| Aspect | Tool | Worker |
|--------|------|--------|
| Handler Model | Synchronous - returns result | Async - manages completion |
| State | Stateless | Stateful (TaskContext) |
| Delegation | Cannot delegate | Can delegate to sub-agents |
| Result Publishing | Auto by decorator | Manual via `task.complete()` |
| Use Case | Simple operations | Complex orchestration |

---

## Tests to Add

```python
# test/test_tool.py

async def test_tool_on_invoke_publishes_result():
    """Tool should auto-publish result to response_event."""
    @tool.on_invoke(event_type="echo.requested")
    async def handler(request, ctx):
        return {"echoed": request.data["message"]}
    
    # Trigger event
    # Verify action-result published with success=True

async def test_tool_on_invoke_handles_error():
    """Tool should publish error on exception."""
    @tool.on_invoke(event_type="fail.requested")
    async def handler(request, ctx):
        raise ValueError("Something went wrong")
    
    # Trigger event
    # Verify action-result published with success=False, error message

async def test_tool_uses_caller_response_event():
    """Tool should publish to caller-specified response_event."""
    pass

async def test_invocation_context_from_event():
    """InvocationContext should parse event correctly."""
    pass
```

---

## Implementation Checklist

- [ ] **Read existing code** in `tool.py`
- [ ] **Write tests first** for `InvocationContext.from_event()`
- [ ] **Implement** `InvocationContext` dataclass
- [ ] **Write tests first** for `on_invoke()` decorator
- [ ] **Implement** Tool class with `on_invoke()` decorator
- [ ] **Verify** error handling publishes failure response
- [ ] **Update examples** to use new pattern

---

## Dependencies

- **Depends on:** [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) (RF-SDK-001, RF-SDK-002, RF-SDK-003)
- **No memory dependency** - Tools are stateless
- **Blocked by:** Nothing

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Agent progression model
- [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) - Event publishing (dependency)
- [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Async pattern comparison
