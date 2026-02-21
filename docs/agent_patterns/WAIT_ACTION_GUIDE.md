# WAIT Action: Pause/Resume Guide for ChoreographyPlanner

**Feature:** Human-in-the-Loop (HITL) and External Dependency Handling  
**Status:** ✅ Implemented in Stage 4 Phase 2  
**Version:** 0.8.0+  
**Last Updated:** February 21, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [When to Use WAIT](#when-to-use-wait)
3. [How WAIT Works](#how-wait-works)
4. [Complete Example: E-Commerce Order Approval](#complete-example-e-commerce-order-approval)
5. [Implementation Requirements](#implementation-requirements)
6. [Testing WAIT Flows](#testing-wait-flows)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The **WAIT action** enables ChoreographyPlanner to pause plan execution while waiting for external input (human approval, API callbacks, user uploads, etc.). This is essential for:

- **Human-in-the-Loop (HITL)** workflows requiring manual approval
- **Async dependencies** (waiting for external services to complete)
- **User interaction** (waiting for clarification or additional data)
- **Rate limiting** (pausing when quotas exhausted)

### Key Concepts

| Concept | Description |
|---------|-------------|
| **WAIT Decision** | LLM decides to pause, specifying `expected_event` that will resume |
| **Plan Pause** | Plan status changes to "paused", execution stops |
| **Expected Event** | Event type that will break the WAIT condition |
| **Resume Trigger** | External system publishes the expected event |
| **Auto-Resume** | Planner's `on_transition()` automatically resumes when expected event arrives |

---

## When to Use WAIT

### Use Cases

#### 1. **Financial Approval Workflows**
```python
# Policy: Transactions >$5,000 require manager approval
if transaction_amount > 5000:
    # LLM returns: WaitAction(expected_event="approval.granted")
    await planner.execute_decision(decision, context, goal, plan)
    # Plan pauses until manager approves
```

#### 2. **Document Upload Requirements**
```python
# User must upload ID before account activation
# LLM returns: WaitAction(expected_event="document.uploaded")
# Plan pauses until user uploads document
```

#### 3. **External API Callbacks**
```python
# Payment processor takes 30s to verify
# LLM returns: WaitAction(expected_event="payment.verified")
# Plan pauses until webhook received
```

#### 4. **User Clarification**
```python
# Ambiguous request, need user input
# LLM returns: WaitAction(expected_event="clarification.provided")
# Plan pauses until user responds
```

#### 5. **Rate Limit Handling**
```python
# API quota exhausted, wait for reset
# LLM returns: WaitAction(expected_event="quota.reset", timeout_seconds=3600)
# Plan pauses for 1 hour
```

### When NOT to Use WAIT

- **Short synchronous calls** - Use PUBLISH and wait for result event instead
- **Simple conditionals** - Use state machine transitions
- **Fire-and-forget** - Use PUBLISH action
- **Parallel tasks** - Use multiple PUBLISH actions

---

## How WAIT Works

### Complete Flow Breakdown

#### **Phase 1: LLM Decides to WAIT**

The ChoreographyPlanner's LLM analyzes the current situation and decides a WAIT is needed:

```python
# Planner processes goal
decision = await planner.reason_next_action(
    trigger="Order received: $12,000",
    context=context,
    custom_context={
        "policy": "Orders >$5,000 require manager approval",
        "amount": 12000,
    },
)

# LLM Response (PlannerDecision):
{
    "plan_id": "plan-123",
    "current_state": "validate_order",
    "next_action": {
        "action": "wait",
        "reason": "Transaction amount $12,000 exceeds approval threshold",
        "expected_event": "approval.granted",
        "timeout_seconds": 3600
    },
    "reasoning": "Company policy requires manager approval for orders >$5k"
}
```

**Key Fields:**
- `expected_event`: **CRITICAL** - Event type that will resume the plan
- `reason`: Human-readable explanation of why waiting
- `timeout_seconds`: How long to wait before timeout (optional)

#### **Phase 2: Execute WAIT (Pause Plan)**

When `execute_decision()` receives a WAIT action:

```python
async def execute_decision(
    self,
    decision: PlannerDecision,
    context: PlatformContext,
    goal_event: Optional[EventEnvelope],
    plan: PlanContext,  # ← Required for WAIT
):
    action = decision.next_action
    
    if action.action == PlanAction.WAIT:
        # 1. Validate plan exists
        if not plan:
            raise ValueError("WAIT action requires PlanContext for pause/resume")
        
        # 2. Pause the plan (status → "paused")
        await plan.pause(reason=action.reason)
        
        # 3. Store expected event in plan metadata
        plan.results["_waiting_for"] = action.expected_event
        plan.results["_wait_timeout"] = action.timeout_seconds
        plan.results["_wait_started_at"] = time.time()
        await plan.save()
        
        # 4. Publish notification event (for UIs, external systems)
        await context.bus.publish(
            topic="system-events",
            event_type="plan.waiting_for_input",
            data={
                "plan_id": plan.plan_id,
                "correlation_id": plan.correlation_id,
                "reason": action.reason,
                "expected_event": action.expected_event,
                "timeout_seconds": action.timeout_seconds,
            },
        )
```

**What happens:**
1. ✅ Plan status changes to `"paused"`
2. ✅ Expected event stored in `plan.results["_waiting_for"]`
3. ✅ Notification published to `system-events` topic
4. ✅ Plan execution **STOPS** (does not continue to next state)

#### **Phase 3: External System Provides Input**

External system (human UI, webhook, service) publishes the expected event:

**Example: Manager Approval UI**
```python
# Manager clicks "Approve" button in admin UI
@app.post("/api/approvals/{plan_id}/approve")
async def approve_transaction(plan_id: str, approval: ApprovalRequest):
    # Validate manager permissions
    if not is_manager(approval.user_id):
        raise PermissionError("Only managers can approve")
    
    # Publish the expected event
    await event_bus.publish(
        topic="action-results",
        event_type="approval.granted",  # ← Matches expected_event
        correlation_id=plan_id,          # ← Routes to correct plan
        data={
            "status": "approved",
            "approved_by": approval.user_id,
            "approved_at": datetime.now().isoformat(),
            "notes": approval.notes,
        },
    )
    
    return {"message": "Approval published"}
```

**Example: Automated Approval Service**
```python
# Service listens for WAIT notifications and auto-approves if criteria met
@approval_service.on_event("plan.waiting_for_input")
async def auto_approve_if_eligible(event, context):
    wait_data = event.data
    
    # Check if auto-approval is allowed
    if wait_data["expected_event"] == "approval.granted":
        # Load plan to check amount
        plan = await context.memory.get_plan_context(
            plan_id=wait_data["plan_id"],
        )
        
        # Auto-approve if amount < $10k
        if plan.goal_data.get("amount", 0) < 10000:
            await context.bus.publish(
                topic="action-results",
                event_type="approval.granted",
                correlation_id=wait_data["correlation_id"],
                data={
                    "status": "approved",
                    "auto": True,
                    "reason": "Amount below auto-approval threshold",
                },
            )
```

#### **Phase 4: Planner Auto-Resumes**

Planner's `on_transition()` handler detects the expected event:

```python
class ChoreographyPlanner(Planner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register transition handler
        self.on_transition()(self._handle_transition_with_wait_check)
    
    async def _handle_transition_with_wait_check(
        self,
        event: EventEnvelope,
        context: PlatformContext,
    ):
        """Handle state transitions with WAIT resume logic."""
        
        # Restore plan by correlation ID
        plan = await PlanContext.restore_by_correlation(
            correlation_id=event.correlation_id,
            context=context,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )
        
        if not plan:
            return  # Not a plan-related event
        
        # Check if plan is paused and waiting for this event
        if plan.status == "paused":
            waiting_for = plan.results.get("_waiting_for")
            
            if waiting_for == event.event_type:
                logger.info(f"✅ WAIT condition met: {event.event_type}")
                
                # Resume plan with input data
                await plan.resume(input_data=event.data)
                
                # Plan.resume() sets status="running" and continues execution
                # It will call reason_next_action() to decide next step
                return
            else:
                # Paused but not the expected event, ignore
                logger.debug(f"Plan paused, waiting for {waiting_for}, got {event.event_type}")
                return
        
        # Normal state transition logic (not paused)
        next_state = plan.get_next_state(event)
        if next_state:
            await plan.execute_next(trigger_event=event)
        elif plan.is_complete():
            await plan.finalize(result=event.data)
```

**Auto-resume behavior:**
1. ✅ Checks if plan is paused (`status == "paused"`)
2. ✅ Compares incoming event type with expected event
3. ✅ If match, calls `plan.resume(input_data=event.data)`
4. ✅ Plan continues from where it paused
5. ✅ LLM makes next decision based on resumed context

#### **Phase 5: Plan Continues Execution**

After resume, the plan continues normally:

```python
# Inside plan.resume()
async def resume(self, input_data: Dict[str, Any]) -> None:
    """Resume paused plan execution."""
    # Update status
    self.status = "running"
    
    # Store input data
    self.results["user_input"] = input_data
    
    # Clear wait metadata
    self.results.pop("_waiting_for", None)
    
    # Continue execution (LLM decides next step)
    await self.execute_next()
```

The planner's LLM then decides what to do next:

```python
# LLM sees: "Approval received: approved"
# LLM decides: PUBLISH payment.process
decision = await planner.reason_next_action(
    trigger=f"Approval granted: {input_data}",
    context=context,
)

# Execute: Publish payment processing event
await planner.execute_decision(decision, context, None, plan)
```

---

## Complete Example: E-Commerce Order Approval

### Scenario

**Business Requirement:**
- E-commerce platform processing customer orders
- Orders >$5,000 require manager approval per compliance policy
- Orders ≤$5,000 auto-approve
- After approval, process payment and complete order

### Actors

| Actor | Role | Responsibility |
|-------|------|----------------|
| **Customer** | End user | Places order |
| **OrderPlanner** | ChoreographyPlanner | Orchestrates order workflow |
| **Manager** | Human approver | Reviews and approves high-value orders |
| **ApprovalUI** | Admin interface | Provides approval interface for managers |
| **PaymentWorker** | Worker agent | Processes payment after approval |

### Implementation

#### **Step 1: Initialize Planner with Business Rules**

```python
from soorma.ai.choreography import ChoreographyPlanner

planner = ChoreographyPlanner(
    name="order-processor",
    reasoning_model="gpt-4o",
    system_instructions="""
        You are an order processing agent for an e-commerce platform.
        
        CRITICAL BUSINESS RULES:
        1. Orders with amount >$5,000 require manager approval
           - Use WAIT action with expected_event="approval.granted"
           - Include clear reason for approval requirement
           - Set timeout to 1 hour (3600 seconds)
        
        2. Do NOT process payment before approval is granted
           - Wait for approval.granted event
           - Only then publish payment.process event
        
        3. After payment completes, mark order as complete
           - Wait for payment.completed event
           - Then use COMPLETE action to finalize order
        
        4. Always provide clear reasoning for decisions
    """,
    planning_strategy="conservative",  # Prioritize safety over speed
)

# Register goal handler
@planner.on_goal("order.received")
async def handle_order(goal, context):
    """Process incoming order."""
    order_data = goal.data
    
    # Create plan context
    plan = PlanContext(
        plan_id=goal.correlation_id,
        goal_event="order.received",
        goal_data=order_data,
        response_event=goal.response_event,
        status="running",
        state_machine={},  # ChoreographyPlanner uses LLM, not state machine
        current_state="processing",
        results={},
        tenant_id=goal.tenant_id,
        user_id=goal.user_id,
        session_id=goal.session_id,
        _context=context,
    )
    await plan.save()
    
    # LLM decides first action
    decision = await planner.reason_next_action(
        trigger=f"New order: {order_data['order_id']} for ${order_data['amount']}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={
            "order": order_data,
            "policy": "Orders >$5,000 require manager approval",
        },
    )
    
    # Execute decision (will WAIT if amount > $5k)
    await planner.execute_decision(decision, context, goal, plan)
```

#### **Step 2: LLM Decision for High-Value Order**

**Input:**
- Order amount: $12,000
- System instructions: "Orders >$5,000 require approval"

**LLM Returns:**
```python
PlannerDecision(
    plan_id="plan-abc-123",
    current_state="processing",
    next_action=WaitAction(
        action=PlanAction.WAIT,
        reason="Order amount $12,000 exceeds $5,000 approval threshold per company policy",
        expected_event="approval.granted",
        timeout_seconds=3600,
    ),
    reasoning="This order requires manager approval due to high value. Compliance policy mandates human review for transactions >$5k to prevent fraud and ensure proper oversight.",
)
```

**execute_decision() executes WAIT:**
```python
# Plan pauses
await plan.pause(reason="...")

# Expected event stored
plan.results["_waiting_for"] = "approval.granted"
await plan.save()

# Notification published
await context.bus.publish(
    topic="system-events",
    event_type="plan.waiting_for_input",
    data={
        "plan_id": "plan-abc-123",
        "correlation_id": "plan-abc-123",
        "reason": "Order amount $12,000 exceeds...",
        "expected_event": "approval.granted",
    },
)
```

#### **Step 3: Manager Approval Process**

**Manager UI subscribes to wait notifications:**

```python
# Admin dashboard listens for approval requests
@admin_ui.on_event("plan.waiting_for_input")
async def show_approval_request(event):
    if event.data["expected_event"] == "approval.granted":
        # Load plan details
        plan = await get_plan_details(event.data["plan_id"])
        
        # Show approval UI
        display_approval_dialog(
            order_id=plan.goal_data["order_id"],
            amount=plan.goal_data["amount"],
            customer=plan.goal_data["customer_id"],
            reason=event.data["reason"],
            approve_callback=lambda: approve_order(event.data["plan_id"]),
            reject_callback=lambda: reject_order(event.data["plan_id"]),
        )
```

**Manager clicks "Approve":**

```python
# Approval API endpoint
@app.post("/api/orders/{plan_id}/approve")
async def approve_order(plan_id: str, approval: ApprovalRequest):
    # Validate manager permissions
    user = get_current_user()
    if not user.has_role("manager"):
        raise HTTPException(403, "Only managers can approve orders")
    
    # Audit log
    await audit_log.log(
        action="order_approved",
        user_id=user.id,
        plan_id=plan_id,
        notes=approval.notes,
    )
    
    # Publish approval event (resumes plan)
    await event_bus.publish(
        topic="action-results",
        event_type="approval.granted",  # ← Expected event!
        correlation_id=plan_id,
        data={
            "status": "approved",
            "approved_by": user.id,
            "approved_at": datetime.now().isoformat(),
            "notes": approval.notes,
        },
    )
    
    return {"message": "Order approved, plan will resume automatically"}
```

#### **Step 4: Planner Auto-Resumes**

**Planner's on_transition() detects approval:**

```python
# approval.granted event arrives
event = EventEnvelope(
    event_type="approval.granted",
    correlation_id="plan-abc-123",
    data={"status": "approved", "approved_by": "mgr-001"},
)

# on_transition() handler
plan = await PlanContext.restore_by_correlation("plan-abc-123", context, ...)

if plan.status == "paused" and plan.results["_waiting_for"] == "approval.granted":
    # WAIT condition met!
    logger.info("✅ Approval received, resuming plan")
    await plan.resume(input_data=event.data)
```

**Plan.resume() continues execution:**

```python
# Inside resume()
self.status = "running"
self.results["user_input"] = {"status": "approved", "approved_by": "mgr-001"}

# LLM decides next step
decision = await planner.reason_next_action(
    trigger="Approval granted by mgr-001",
    context=context,
)

# LLM returns: PublishAction(event_type="payment.process")
await planner.execute_decision(decision, context, None, plan)
```

#### **Step 5: Payment Processing**

**Payment event published:**

```python
# From execute_decision(PublishAction)
await context.bus.publish(
    topic="action-requests",
    event_type="payment.process",
    data={
        "order_id": plan.goal_data["order_id"],
        "amount": plan.goal_data["amount"],
        "payment_method": plan.goal_data["payment_method"],
    },
)
```

**PaymentWorker handles it:**

```python
@payment_worker.on_task("payment.process")
async def process_payment(task, context):
    # Process payment
    result = await payment_gateway.charge(
        amount=task.data["amount"],
        method=task.data["payment_method"],
    )
    
    # Respond with result
    await context.bus.respond(
        event_type="payment.completed",
        correlation_id=task.correlation_id,
        data={
            "status": "success",
            "transaction_id": result.transaction_id,
        },
    )
```

#### **Step 6: Order Completion**

**Planner receives payment.completed:**

```python
# on_transition() routes to plan
event = EventEnvelope(
    event_type="payment.completed",
    correlation_id="plan-abc-123",
    data={"status": "success", "transaction_id": "txn-xyz"},
)

# LLM decides to complete
decision = await planner.reason_next_action(
    trigger="Payment completed successfully",
    context=context,
)

# LLM returns: CompleteAction(result={...})
await planner.execute_decision(decision, context, goal, plan)
```

**Complete action finalizes plan:**

```python
# From execute_decision(CompleteAction)
await context.bus.respond(
    event_type=goal.response_event,  # "order.completed"
    correlation_id=plan.correlation_id,
    data={
        "order_id": plan.goal_data["order_id"],
        "status": "completed",
        "approval": plan.results["user_input"],
        "payment": {"..."},
    },
)
```

### Complete Flow Diagram

```
Customer      OrderPlanner      Manager UI      PaymentWorker      Event Bus
    |               |                |                 |               |
    |--order.------->|                |                 |               |
    |  received      |                |                 |               |
    |  ($12k)        |                |                 |               |
    |               |                |                 |               |
    |               |--LLM: WAIT---->|                 |               |
    |               |  (pause plan)  |                 |               |
    |               |                |                 |               |
    |               |--plan.waiting->|                 |               |---system-events
    |               | _for_input     |                 |               |
    |               |                |                 |               |
    |               |                |[Manager reviews]|               |
    |               |                |                 |               |
    |               |                |--approval.------|--------------->|---action-results
    |               |<---------------------------------|   granted       |
    |               | (resume signal)|                 |               |
    |               |                |                 |               |
    |               |--LLM: PUBLISH->|                 |               |
    |               |  payment.      |                 |               |---action-requests
    |               |  process       |                 |-------------->|
    |               |                |                 |               |
    |               |                |                 |--charge card->|
    |               |                |                 |<-success------|
    |               |                |                 |               |
    |               |<---------------------------------|payment.------->|---action-results
    |               |                |                 | completed     |
    |               |                |                 |               |
    |               |--LLM: COMPLETE-|                 |               |
    |<--order.------|                |                 |               |---action-results
    |   completed   |                |                 |               |
    |               |                |                 |               |
```

---

## Implementation Requirements

### ChoreographyPlanner Requirements

**1. Accept `plan` parameter in execute_decision():**
```python
async def execute_decision(
    self,
    decision: PlannerDecision,
    context: PlatformContext,
    goal_event: Optional[EventEnvelope] = None,
    plan: Optional[PlanContext] = None,  # ← Required for WAIT
) -> None:
```

**2. Implement WAIT pause logic:**
```python
if action.action == PlanAction.WAIT:
    if not plan:
        raise ValueError("WAIT action requires PlanContext")
    
    await plan.pause(reason=action.reason)
    plan.results["_waiting_for"] = action.expected_event
    await plan.save()
    
    await context.bus.publish(...)
```

**3. Override on_transition() with resume check:**
```python
async def _handle_transition_with_wait_check(self, event, context):
    plan = await PlanContext.restore_by_correlation(...)
    
    if plan and plan.status == "paused":
        if plan.results.get("_waiting_for") == event.event_type:
            await plan.resume(input_data=event.data)
            return
    
    # Normal transition logic
```

### PlanContext Requirements

From Phase 1 (already implemented):

**1. pause() method:**
```python
async def pause(self, reason: str = "user_input_required") -> None:
    self.status = "paused"
    await self.save()
```

**2. resume() method:**
```python
async def resume(self, input_data: Dict[str, Any]) -> None:
    self.status = "running"
    self.results["user_input"] = input_data
    await self.execute_next()
```

**3. Metadata storage:**
- `plan.results` dictionary supports arbitrary keys
- Stores `_waiting_for`, `_wait_timeout`, `_wait_started_at`

### External System Requirements

**1. Listen for wait notifications:**
```python
@service.on_event("plan.waiting_for_input")
async def handle_wait_request(event, context):
    # Process wait notification
    pass
```

**2. Publish expected event:**
```python
await context.bus.publish(
    topic="action-results",
    event_type=event.data["expected_event"],  # ← Must match!
    correlation_id=event.data["correlation_id"],
    data={...},
)
```

**3. Correlation ID matching:**
- Must use correct correlation_id for plan routing
- Planner uses `restore_by_correlation()` to find plan

---

## Testing WAIT Flows

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.ai.choreography import ChoreographyPlanner
from soorma_common.decisions import PlannerDecision, WaitAction, PlanAction

@pytest.mark.asyncio
async def test_execute_decision_wait_pauses_plan():
    """WAIT action calls plan.pause()."""
    planner = ChoreographyPlanner(name="test")
    plan = MagicMock()
    plan.pause = AsyncMock()
    plan.save = AsyncMock()
    
    context = MagicMock()
    context.bus.publish = AsyncMock()
    
    decision = PlannerDecision(
        plan_id="p1",
        current_state="s1",
        next_action=WaitAction(
            action=PlanAction.WAIT,
            reason="Test wait",
            expected_event="test.event",
        ),
        reasoning="test",
    )
    
    await planner.execute_decision(decision, context, None, plan)
    
    # Verify pause called
    plan.pause.assert_called_once_with(reason="Test wait")
    
    # Verify expected event stored
    assert plan.results["_waiting_for"] == "test.event"
    plan.save.assert_called()
    
    # Verify notification published
    context.bus.publish.assert_called_once()
    args = context.bus.publish.call_args[1]
    assert args["event_type"] == "plan.waiting_for_input"

@pytest.mark.asyncio
async def test_execute_decision_wait_requires_plan():
    """WAIT action raises error if plan missing."""
    planner = ChoreographyPlanner(name="test")
    
    decision = PlannerDecision(
        plan_id="p1",
        current_state="s1",
        next_action=WaitAction(
            action=PlanAction.WAIT,
            reason="Test",
            expected_event="test.event",
        ),
        reasoning="test",
    )
    
    with pytest.raises(ValueError, match="requires PlanContext"):
        await planner.execute_decision(decision, MagicMock(), None, None)

@pytest.mark.asyncio
async def test_on_transition_resumes_on_expected_event():
    """on_transition() resumes plan when expected event arrives."""
    planner = ChoreographyPlanner(name="test")
    context = MagicMock()
    
    # Mock plan (paused, waiting for "approval.granted")
    plan = MagicMock()
    plan.status = "paused"
    plan.results = {"_waiting_for": "approval.granted"}
    plan.resume = AsyncMock()
    
    # Mock restore
    PlanContext.restore_by_correlation = AsyncMock(return_value=plan)
    
    # Incoming event (approval.granted)
    event = MagicMock()
    event.event_type = "approval.granted"
    event.correlation_id = "plan-123"
    event.data = {"status": "approved"}
    
    # Call transition handler
    await planner._handle_transition_with_wait_check(event, context)
    
    # Verify resume called
    plan.resume.assert_called_once_with(input_data={"status": "approved"})

@pytest.mark.asyncio
async def test_on_transition_ignores_unexpected_event_when_paused():
    """on_transition() does NOT resume if event doesn't match."""
    planner = ChoreographyPlanner(name="test")
    context = MagicMock()
    
    # Mock plan (paused, waiting for "approval.granted")
    plan = MagicMock()
    plan.status = "paused"
    plan.results = {"_waiting_for": "approval.granted"}
    plan.resume = AsyncMock()
    
    PlanContext.restore_by_correlation = AsyncMock(return_value=plan)
    
    # Incoming event (wrong event type)
    event = MagicMock()
    event.event_type = "payment.completed"  # ← Not the expected event
    event.correlation_id = "plan-123"
    
    # Call transition handler
    await planner._handle_transition_with_wait_check(event, context)
    
    # Verify resume NOT called
    plan.resume.assert_not_called()
```

### Integration Tests

```python
@pytest.mark.integration
async def test_choreography_planner_wait_and_resume_flow():
    """End-to-end: WAIT action pauses plan, resume continues execution."""
    # Setup real services
    context = create_test_context()
    
    planner = ChoreographyPlanner(
        name="approval-test",
        reasoning_model="ollama/mistral",  # Local model for testing
        system_instructions="Orders >$100 require approval. Use WAIT action.",
    )
    
    # Goal arrives (high-value order)
    goal = GoalContext(
        event_type="order.received",
        data={"order_id": "ord-123", "amount": 150},
        correlation_id="test-corr-123",
    )
    
    # Create plan
    plan = PlanContext(
        plan_id=goal.correlation_id,
        goal_event="order.received",
        goal_data=goal.data,
        response_event="order.completed",
        state_machine={},
        current_state="processing",
        results={},
        _context=context,
    )
    await plan.save()
    
    # LLM should decide to WAIT
    decision = await planner.reason_next_action(
        trigger=f"Order {goal.data['order_id']}: ${goal.data['amount']}",
        context=context,
    )
    
    # Verify WAIT decision
    assert decision.next_action.action == PlanAction.WAIT
    assert decision.next_action.expected_event == "approval.granted"
    
    # Execute WAIT
    await planner.execute_decision(decision, context, goal, plan)
    
    # Verify plan paused
    restored_plan = await PlanContext.restore(plan.plan_id, context, ...)
    assert restored_plan.status == "paused"
    assert restored_plan.results["_waiting_for"] == "approval.granted"
    
    # Simulate approval event
    approval_event = EventEnvelope(
        event_type="approval.granted",
        correlation_id=plan.plan_id,
        data={"status": "approved"},
    )
    
    # Trigger transition handler
    await planner._handle_transition_with_wait_check(approval_event, context)
    
    # Verify plan resumed
    resumed_plan = await PlanContext.restore(plan.plan_id, context, ...)
    assert resumed_plan.status == "running"
    assert resumed_plan.results["user_input"] == {"status": "approved"}
```

---

## Common Patterns

### Pattern 1: Multi-Step Approval Chain

```python
# First approval: manager
decision1 = WaitAction(
    action=PlanAction.WAIT,
    reason="Requires manager approval",
    expected_event="manager.approved",
)

# After manager approves, LLM decides:
decision2 = WaitAction(
    action=PlanAction.WAIT,
    reason="Requires director approval (>$20k)",
    expected_event="director.approved",
)

# Chain of WAIT actions for escalation workflows
```

### Pattern 2: Timeout Handling

```python
# Set timeout
decision = WaitAction(
    action=PlanAction.WAIT,
    reason="Waiting for user upload",
    expected_event="document.uploaded",
    timeout_seconds=7200,  # 2 hours
)

# External timeout service
@timeout_service.on_event("plan.waiting_for_input")
async def schedule_timeout(event):
    timeout = event.data["timeout_seconds"]
    await scheduler.schedule(
        delay=timeout,
        event_type="plan.timeout",
        correlation_id=event.data["correlation_id"],
    )

# Planner handles timeout
@planner.on_transition()
async def handle_timeout(event, context):
    if event.event_type == "plan.timeout":
        plan = await restore_plan(event.correlation_id)
        await plan.finalize(result={"status": "timeout"})
```

### Pattern 3: Conditional Auto-Approval

```python
# Business rule: auto-approve if customer is premium
decision = WaitAction(
    action=PlanAction.WAIT,
    reason="Standard approval flow (can be auto-approved for premium)",
    expected_event="approval.granted",
)

# Auto-approval service
@service.on_event("plan.waiting_for_input")
async def auto_approve_premium(event):
    plan = await get_plan(event.data["plan_id"])
    customer = await get_customer(plan.goal_data["customer_id"])
    
    if customer.tier == "premium":
        await publish_approval(plan.plan_id)
```

---

## Troubleshooting

### Issue: Plan never resumes

**Symptom:** Plan stays paused forever

**Possible Causes:**
1. **Wrong event type published**  
   - Check: Does `event.event_type` match `plan.results["_waiting_for"]`?
   - Fix: Ensure external system publishes exact event type

2. **Wrong correlation_id**  
   - Check: Does `event.correlation_id` match plan's correlation_id?
   - Fix: Use plan_id or correlation_id from wait notification

3. **on_transition() not registered**  
   - Check: Is planner's transition handler registered?
   - Fix: Ensure `on_transition()` decorator is called

**Debug Steps:**
```python
# Add logging to on_transition()
logger.info(f"Event received: {event.event_type}")
logger.info(f"Plan status: {plan.status}, waiting for: {plan.results.get('_waiting_for')}")
```

### Issue: ValueError "WAIT action requires PlanContext"

**Symptom:** `execute_decision()` raises error

**Cause:** Missing `plan` parameter in `execute_decision()` call

**Fix:**
```python
# Wrong:
await planner.execute_decision(decision, context, goal)

# Correct:
await planner.execute_decision(decision, context, goal, plan)
```

### Issue: Multiple resumes

**Symptom:** Plan resumes multiple times

**Cause:** Multiple external systems publishing expected event

**Fix:**
```python
# Add idempotency check
if plan.status != "paused":
    logger.warning("Plan already resumed, ignoring event")
    return
```

---

## Summary

The **WAIT action** is a powerful mechanism for human-in-the-loop and asynchronous workflows:

**Key Takeaways:**
1. ✅ LLM decides to WAIT based on business rules (via system_instructions)
2. ✅ `execute_decision()` pauses plan and stores expected_event
3. ✅ External system publishes expected event to resume
4. ✅ Planner's `on_transition()` auto-detects and resumes
5. ✅ Plan continues execution after resume

**Production Checklist:**
- [ ] System instructions define WAIT criteria
- [ ] External systems subscribe to `plan.waiting_for_input`
- [ ] External systems publish correct `expected_event`
- [ ] Correlation IDs match for plan routing
- [ ] Timeout handling implemented (if needed)
- [ ] Tests cover pause/resume flows

---

**Related Documentation:**
- [ACTION_PLAN_Stage4_Phase2_Implementation.md](plans/ACTION_PLAN_Stage4_Phase2_Implementation.md) - Implementation details
- [ARCHITECTURE_PATTERNS.md](../ARCHITECTURE_PATTERNS.md) - Two-layer SDK pattern
- [MASTER_PLAN_Stage4_Planner.md](plans/MASTER_PLAN_Stage4_Planner.md) - Overall planner design

**Questions?** File an issue or consult [CONTRIBUTING_REFERENCE.md](../CONTRIBUTING_REFERENCE.md)
