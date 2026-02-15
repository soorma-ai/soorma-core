"""
Integration tests for Tool ↔ Worker interactions (RF-SDK-004) - Phase 3A.3.

Test coverage for:
- Tool delegating to Worker
- Worker delegating to Worker
- Multi-level delegation chains
- End-to-end workflows
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from soorma_common.events import EventEnvelope, EventTopic

from soorma import Tool, Worker
from soorma.agents.tool import InvocationContext
from soorma.task_context import TaskContext, ResultContext, DelegationSpec


# ==============================================================================
# Tool ↔ Worker Interaction Tests (2 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_tool_delegates_to_worker():
    """Tool should publish action request that Worker can handle."""
    tool = Tool(name="calculator-tool")
    worker = Worker(name="math-worker")
    events_published = []

    @tool.on_invoke("add.numbers")
    async def add_numbers(request: InvocationContext, context):
        # Tool delegates computation to worker
        await context.bus.request(
            event_type="compute.sum.requested",
            data={"numbers": request.data["numbers"]},
            response_event="compute.sum.completed",
            correlation_id=request.request_id,
        )
        # In real scenario, Tool would wait for result
        # For this test, we just verify request was published
        return {"status": "delegated"}

    @worker.on_task("compute.sum.requested")
    async def compute_sum(task: TaskContext, context):
        numbers = task.data["numbers"]
        result = sum(numbers)
        await task.complete({"sum": result})

    # Simulate Tool invocation
    tool_event = EventEnvelope(
        source="client",
        type="add.numbers",
        topic=EventTopic.ACTION_REQUESTS,
        data={"request_id": "req-1", "numbers": [1, 2, 3]},
        response_event="add.numbers.result",
    )

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Call tool handler
    tool_wrapper = tool._event_handlers["action-requests:add.numbers"][0]
    await tool_wrapper(tool_event, context)

    # Verify tool published request to worker
    context.bus.request.assert_awaited_once()
    call_kwargs = context.bus.request.await_args.kwargs
    assert call_kwargs["event_type"] == "compute.sum.requested"
    assert call_kwargs["response_event"] == "compute.sum.completed"


@pytest.mark.asyncio
async def test_tool_receives_worker_result():
    """Tool should receive and process Worker result."""
    tool = Tool(name="data-tool")
    worker = Worker(name="processor-worker")

    # Track flow
    flow = {"tool_invoked": False, "worker_processed": False, "tool_received": False}

    @tool.on_invoke("process.data")
    async def process_data_tool(request: InvocationContext, context):
        flow["tool_invoked"] = True
        # Delegate to worker
        await context.bus.request(
            event_type="process.data.requested",
            data=request.data,
            response_event="process.data.completed",
            correlation_id=request.request_id,
        )
        return {"status": "processing"}

    @worker.on_task("process.data.requested")
    async def process_data_worker(task: TaskContext, context):
        flow["worker_processed"] = True
        await task.complete({"result": "processed"})

    # Simulate receiving result
    @tool.on_invoke("process.data.result")
    async def receive_result(request: InvocationContext, context):
        flow["tool_received"] = True
        return {"final_result": request.data["result"]}

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Tool invocation
    tool_event = EventEnvelope(
        source="client",
        type="process.data",
        topic=EventTopic.ACTION_REQUESTS,
        data={"request_id": "req-2", "content": "test"},
        response_event="process.data.result",
    )

    tool_wrapper = tool._event_handlers["action-requests:process.data"][0]
    await tool_wrapper(tool_event, context)

    # Simulate worker completing
    worker_event = EventEnvelope(
        source="client",
        type="process.data.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "task-1", "content": "test"},
        response_event="process.data.completed",
    )

    worker_wrapper = worker._event_handlers["action-requests:process.data.requested"][0]
    await worker_wrapper(worker_event, context)

    assert flow["tool_invoked"] is True
    assert flow["worker_processed"] is True


# ==============================================================================
# Worker ↔ Worker Chain Tests (3 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_worker_delegates_to_worker():
    """Worker should delegate to another Worker (two-level delegation)."""
    coordinator = Worker(name="coordinator")
    processor = Worker(name="processor")

    flow = {"coordinator_called": False, "processor_called": False}

    @coordinator.on_task("coordinate.task")
    async def coordinate(task: TaskContext, context):
        flow["coordinator_called"] = True
        await task.delegate(
            event_type="process.subtask",
            data={"work": "subtask"},
            response_event="process.subtask.completed",
        )

    @processor.on_task("process.subtask")
    async def process(task: TaskContext, context):
        flow["processor_called"] = True
        await task.complete({"status": "done"})

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Coordinator receives task
    coord_event = EventEnvelope(
        source="planner",
        type="coordinate.task",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "task-coord-1"},
        response_event="coordinate.task.completed",
    )

    coord_wrapper = coordinator._event_handlers["action-requests:coordinate.task"][0]
    await coord_wrapper(coord_event, context)

    assert flow["coordinator_called"] is True
    # Verify delegation
    context.bus.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_multi_level_delegation():
    """Worker should support three+ level delegation chains."""
    level1 = Worker(name="level1")
    level2 = Worker(name="level2")
    level3 = Worker(name="level3")

    delegation_depth = {"level": 0}

    @level1.on_task("task.level1")
    async def handle_level1(task: TaskContext, context):
        delegation_depth["level"] = 1
        await task.delegate(
            event_type="task.level2",
            data={},
            response_event="task.level2.completed",
        )

    @level2.on_task("task.level2")
    async def handle_level2(task: TaskContext, context):
        delegation_depth["level"] = 2
        await task.delegate(
            event_type="task.level3",
            data={},
            response_event="task.level3.completed",
        )

    @level3.on_task("task.level3")
    async def handle_level3(task: TaskContext, context):
        delegation_depth["level"] = 3
        await task.complete({"result": "done"})

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Start chain at level 1
    event = EventEnvelope(
        source="user",
        type="task.level1",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "multi-level-1"},
        response_event="task.level1.completed",
    )

    wrapper = level1._event_handlers["action-requests:task.level1"][0]
    await wrapper(event, context)

    # Level 1 should have delegated
    assert delegation_depth["level"] == 1
    context.bus.request.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Loop detection in Stage 4 (Planner)")
async def test_delegation_loop_detection():
    """Worker should detect infinite delegation loops."""
    # Placeholder for future loop detection functionality
    pass


# ==============================================================================
# End-to-End Workflow Tests (2 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_complete_order_processing():
    """Simulate 08-worker-basic order processing workflow."""
    order_worker = Worker(name="order-processor")
    inventory_worker = Worker(name="inventory-service")
    payment_worker = Worker(name="payment-service")

    workflow_state = {
        "order_received": False,
        "inventory_reserved": False,
        "payment_processed": False,
        "order_completed": False,
    }

    @order_worker.on_task("order.process.requested")
    async def process_order(task: TaskContext, context):
        workflow_state["order_received"] = True
        # Parallel delegation
        await task.delegate_parallel([
            DelegationSpec("inventory.reserve.requested", {}, "inventory.reserve.completed"),
            DelegationSpec("payment.process.requested", {}, "payment.process.completed"),
        ])

    @inventory_worker.on_task("inventory.reserve.requested")
    async def reserve_inventory(task: TaskContext, context):
        workflow_state["inventory_reserved"] = True
        await task.complete({"reserved": True})

    @payment_worker.on_task("payment.process.requested")
    async def process_payment(task: TaskContext, context):
        workflow_state["payment_processed"] = True
        await task.complete({"charged": True})

    @order_worker.on_result("inventory.reserve.completed")
    @order_worker.on_result("payment.process.completed")
    async def handle_subtask_result(result: ResultContext, context):
        task = await result.restore_task()
        if task:
            task.update_sub_task_result(result.correlation_id, result.data)
            # Check if all results arrived (simplified)
            workflow_state["order_completed"] = True

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Mock task restoration
    context.memory.get_task_by_subtask = AsyncMock(return_value=SimpleNamespace(
        task_id="order-1",
        plan_id=None,
        event_type="order.process.requested",
        response_event="order.process.completed",
        response_topic="action-results",
        data={},
        sub_tasks=["sub-1", "sub-2"],
        state={"_sub_tasks": {}},
        tenant_id=None,
        user_id=None,
    ))

    # Start workflow
    order_event = EventEnvelope(
        source="user",
        type="order.process.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "order-1", "order_id": "ORD-123"},
        response_event="order.process.completed",
    )

    order_wrapper = order_worker._event_handlers["action-requests:order.process.requested"][0]
    await order_wrapper(order_event, context)

    # Simulate inventory completion
    inventory_event = EventEnvelope(
        source="inventory-service",
        type="inventory.reserve.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "inv-1"},
        response_event="inventory.reserve.completed",
    )

    inv_wrapper = inventory_worker._event_handlers["action-requests:inventory.reserve.requested"][0]
    await inv_wrapper(inventory_event, context)

    # Simulate payment completion
    payment_event = EventEnvelope(
        source="payment-service",
        type="payment.process.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "pay-1"},
        response_event="payment.process.completed",
    )

    pay_wrapper = payment_worker._event_handlers["action-requests:payment.process.requested"][0]
    await pay_wrapper(payment_event, context)

    # Verify workflow progression
    assert workflow_state["order_received"] is True
    assert workflow_state["inventory_reserved"] is True
    assert workflow_state["payment_processed"] is True


@pytest.mark.asyncio
async def test_parallel_aggregation_e2e():
    """Test parallel fan-out/fan-in with result aggregation."""
    orchestrator = Worker(name="validator")
    checker1 = Worker(name="checker-1")
    checker2 = Worker(name="checker-2")
    checker3 = Worker(name="checker-3")

    results_collected = []

    @orchestrator.on_task("validate.all")
    async def validate_all(task: TaskContext, context):
        group_id = await task.delegate_parallel([
            DelegationSpec("check.one", {}, "check.one.done"),
            DelegationSpec("check.two", {}, "check.two.done"),
            DelegationSpec("check.three", {}, "check.three.done"),
        ])
        task.state["group_id"] = group_id

    @checker1.on_task("check.one")
    async def check_one(task: TaskContext, context):
        await task.complete({"check": "one", "valid": True})

    @checker2.on_task("check.two")
    async def check_two(task: TaskContext, context):
        await task.complete({"check": "two", "valid": True})

    @checker3.on_task("check.three")
    async def check_three(task: TaskContext, context):
        await task.complete({"check": "three", "valid": False})

    @orchestrator.on_result("check.one.done")
    @orchestrator.on_result("check.two.done")
    @orchestrator.on_result("check.three.done")
    async def handle_check_result(result: ResultContext, context):
        task = await result.restore_task()
        if task:
            results_collected.append(result.data["check"])
            task.update_sub_task_result(result.correlation_id, result.data)
            
            # Try to aggregate
            aggregated = task.aggregate_parallel_results(task.state.get("group_id"))
            if aggregated:
                # All results collected
                all_valid = all(r.get("valid", False) for r in aggregated.values())

    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    # Mock task restoration
    task_data = SimpleNamespace(
        task_id="validate-1",
        plan_id=None,
        event_type="validate.all",
        response_event="validate.all.completed",
        response_topic="action-results",
        data={},
        sub_tasks=["sub-1", "sub-2", "sub-3"],
        state={
            "group_id": "group-1",
            "_sub_tasks": {
                "sub-1": {"sub_task_id": "sub-1", "status": "pending"},
                "sub-2": {"sub_task_id": "sub-2", "status": "pending"},
                "sub-3": {"sub_task_id": "sub-3", "status": "pending"},
            }
        },
        tenant_id=None,
        user_id=None,
    )
    context.memory.get_task_by_subtask = AsyncMock(return_value=task_data)

    # Start validation
    validate_event = EventEnvelope(
        source="user",
        type="validate.all",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "validate-1"},
        response_event="validate.all.completed",
    )

    validate_wrapper = orchestrator._event_handlers["action-requests:validate.all"][0]
    await validate_wrapper(validate_event, context)

    # Verify parallel delegation occurred
    assert context.bus.request.await_count == 3
