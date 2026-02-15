"""
Tests for TaskContext (RF-SDK-004) - Phase 3A.1.

Test coverage for:
- Persistence (save/restore/delete)
- Sequential delegation
- Parallel delegation
- Error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from uuid import uuid4

from soorma.task_context import TaskContext, SubTaskInfo, DelegationSpec, ResultContext


# ==============================================================================
# Persistence Tests (6 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_task_context_save_to_memory():
    """TaskContext.save() should call memory.store_task_context with correct data."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.memory.store_task_context = AsyncMock()

    task = TaskContext(
        task_id="task-save-1",
        event_type="order.process.requested",
        plan_id="plan-1",
        data={"order_id": "ORD-001"},
        response_event="order.process.completed",
        response_topic="action-results",
        tenant_id="tenant-1",
        user_id="user-1",
        agent_id="worker-1",
        _context=context,
    )
    task.state["step"] = "started"
    task.sub_tasks["sub-1"] = SubTaskInfo(
        sub_task_id="sub-1",
        event_type="inventory.check.requested",
        response_event="inventory.check.completed",
        status="pending",
    )

    await task.save()

    context.memory.store_task_context.assert_awaited_once()
    call_kwargs = context.memory.store_task_context.await_args.kwargs
    assert call_kwargs["task_id"] == "task-save-1"
    assert call_kwargs["event_type"] == "order.process.requested"
    assert call_kwargs["response_event"] == "order.process.completed"
    assert call_kwargs["plan_id"] == "plan-1"
    assert call_kwargs["data"] == {"order_id": "ORD-001"}
    assert call_kwargs["sub_tasks"] == ["sub-1"]
    assert call_kwargs["state"]["step"] == "started"
    assert call_kwargs["state"]["_sub_tasks"]["sub-1"]["status"] == "pending"


@pytest.mark.asyncio
async def test_task_context_restore_from_memory():
    """TaskContext.restore() should retrieve task from memory by task_id."""
    context = MagicMock()
    context.memory = AsyncMock()

    # Mock memory response
    task_data = SimpleNamespace(
        task_id="task-restore-1",
        plan_id="plan-2",
        event_type="order.process.requested",
        response_event="order.process.completed",
        response_topic="action-results",
        data={"order_id": "ORD-002"},
        sub_tasks=["sub-2"],
        state={
            "step": "delegated",
            "_sub_tasks": {
                "sub-2": {
                    "sub_task_id": "sub-2",
                    "event_type": "payment.process.requested",
                    "response_event": "payment.process.completed",
                    "status": "pending",
                }
            }
        },
        tenant_id="tenant-1",
        user_id="user-1",
    )
    context.memory.get_task_context = AsyncMock(return_value=task_data)

    task = await TaskContext.restore("task-restore-1", context)

    assert task is not None
    assert task.task_id == "task-restore-1"
    assert task.plan_id == "plan-2"
    assert task.event_type == "order.process.requested"
    assert task.response_event == "order.process.completed"
    assert task.data == {"order_id": "ORD-002"}
    assert task.state["step"] == "delegated"
    assert "sub-2" in task.sub_tasks
    assert task.sub_tasks["sub-2"].status == "pending"
    context.memory.get_task_context.assert_awaited_once_with(
        "task-restore-1", tenant_id=None, user_id=None
    )


@pytest.mark.asyncio
async def test_task_context_from_memory_factory():
    """TaskContext.from_memory() should construct TaskContext from memory data."""
    context = MagicMock()

    memory_data = SimpleNamespace(
        task_id="task-factory-1",
        plan_id="plan-3",
        event_type="order.ship.requested",
        response_event="order.ship.completed",
        response_topic="action-results",
        data={"order_id": "ORD-003"},
        sub_tasks=["sub-3"],
        state={
            "carrier": "FedEx",
            "_sub_tasks": {
                "sub-3": {
                    "sub_task_id": "sub-3",
                    "event_type": "label.print.requested",
                    "response_event": "label.print.completed",
                    "status": "completed",
                }
            }
        },
        tenant_id="tenant-2",
        user_id="user-2",
    )

    task = TaskContext.from_memory(memory_data, context)

    assert task.task_id == "task-factory-1"
    assert task.plan_id == "plan-3"
    assert task.state["carrier"] == "FedEx"
    assert "sub-3" in task.sub_tasks
    assert task.sub_tasks["sub-3"].status == "completed"
    assert task._context is context


@pytest.mark.asyncio
async def test_task_context_state_serialization():
    """TaskContext should correctly serialize nested state dicts."""
    context = MagicMock()
    context.memory = AsyncMock()

    task = TaskContext(
        task_id="task-serial-1",
        event_type="order.validate.requested",
        plan_id=None,
        data={},
        response_event="order.validate.completed",
        response_topic="action-results",
        _context=context,
    )

    # Set nested state
    task.state["order"] = {
        "items": [{"sku": "P123", "qty": 2}],
        "customer": {"id": "C456", "name": "John Doe"}
    }
    task.state["validations"] = {
        "inventory": {"status": "pending"},
        "payment": {"status": "pending"}
    }

    await task.save()

    call_kwargs = context.memory.store_task_context.await_args.kwargs
    assert call_kwargs["state"]["order"]["items"][0]["sku"] == "P123"
    assert call_kwargs["state"]["order"]["customer"]["name"] == "John Doe"
    assert call_kwargs["state"]["validations"]["inventory"]["status"] == "pending"


@pytest.mark.asyncio
async def test_task_context_save_idempotent():
    """TaskContext.save() should be idempotent (multiple saves work)."""
    context = MagicMock()
    context.memory = AsyncMock()

    task = TaskContext(
        task_id="task-idempotent-1",
        event_type="order.prepare.requested",
        plan_id=None,
        data={},
        response_event="order.prepare.completed",
        response_topic="action-results",
        _context=context,
    )

    # Save multiple times
    await task.save()
    task.state["step"] = "processing"
    await task.save()
    task.state["step"] = "finalizing"
    await task.save()

    # Should have been called 3 times
    assert context.memory.store_task_context.await_count == 3
    
    # Last call should have latest state
    last_call_kwargs = context.memory.store_task_context.await_args.kwargs
    assert last_call_kwargs["state"]["step"] == "finalizing"


@pytest.mark.asyncio
async def test_task_context_delete_after_complete():
    """TaskContext.complete() should delete task context from memory."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-delete-1",
        event_type="order.finalize.requested",
        plan_id=None,
        data={},
        response_event="order.finalize.completed",
        response_topic="action-results",
        tenant_id="tenant-1",
        user_id="user-1",
        _context=context,
    )

    await task.complete({"status": "completed"})

    # Should publish result using respond()
    context.bus.respond.assert_awaited_once()
    
    # Should delete task context
    context.memory.delete_task_context.assert_awaited_once_with(
        "task-delete-1", tenant_id="tenant-1", user_id="user-1"
    )


# ==============================================================================
# Sequential Delegation Tests (4 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_delegate_creates_subtask():
    """TaskContext.delegate() should create SubTaskInfo with correct metadata."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-delegate-1",
        event_type="order.process.requested",
        plan_id="plan-1",
        data={"order_id": "ORD-101"},
        response_event="order.process.completed",
        response_topic="action-results",
        _context=context,
    )

    sub_task_id = await task.delegate(
        event_type="inventory.reserve.requested",
        data={"product_id": "P123"},
        response_event="inventory.reserve.completed",
    )

    # Should create sub-task entry
    assert sub_task_id in task.sub_tasks
    sub_task_info = task.sub_tasks[sub_task_id]
    assert sub_task_info.sub_task_id == sub_task_id
    assert sub_task_info.event_type == "inventory.reserve.requested"
    assert sub_task_info.response_event == "inventory.reserve.completed"
    assert sub_task_info.status == "pending"
    assert sub_task_info.parallel_group_id is None  # Sequential delegation


@pytest.mark.asyncio
async def test_delegate_saves_before_publish():
    """TaskContext.delegate() should save state before publishing request."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    call_order = []

    async def track_save(**kwargs):
        call_order.append("save")

    async def track_request(**kwargs):
        call_order.append("request")

    context.memory.store_task_context.side_effect = track_save
    context.bus.request.side_effect = track_request

    task = TaskContext(
        task_id="task-order-1",
        event_type="order.process.requested",
        plan_id=None,
        data={},
        response_event="order.process.completed",
        response_topic="action-results",
        _context=context,
    )

    await task.delegate(
        event_type="payment.process.requested",
        data={"amount": 99.99},
        response_event="payment.process.completed",
    )

    # Save should happen before request
    assert call_order == ["save", "request"]


@pytest.mark.asyncio
async def test_delegate_preserves_correlation():
    """TaskContext.delegate() should use sub_task_id as correlation_id."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-corr-1",
        event_type="order.validate.requested",
        plan_id=None,
        data={},
        response_event="order.validate.completed",
        response_topic="action-results",
        tenant_id="tenant-1",
        user_id="user-1",
        _context=context,
    )

    sub_task_id = await task.delegate(
        event_type="inventory.check.requested",
        data={"product_id": "P456"},
        response_event="inventory.check.completed",
    )

    # Verify correlation_id matches sub_task_id
    call_kwargs = context.bus.request.await_args.kwargs
    assert call_kwargs["correlation_id"] == sub_task_id
    assert call_kwargs["event_type"] == "inventory.check.requested"
    assert call_kwargs["response_event"] == "inventory.check.completed"
    assert call_kwargs["tenant_id"] == "tenant-1"
    assert call_kwargs["user_id"] == "user-1"


# ==============================================================================
# Parallel Delegation Tests (5 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_delegate_parallel_creates_group():
    """TaskContext.delegate_parallel() should create sub-tasks with shared group ID."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-parallel-1",
        event_type="order.validate.requested",
        plan_id=None,
        data={},
        response_event="order.validate.completed",
        response_topic="action-results",
        _context=context,
    )

    specs = [
        DelegationSpec(
            event_type="inventory.validate.requested",
            data={"sku": "P123"},
            response_event="inventory.validate.completed",
        ),
        DelegationSpec(
            event_type="payment.validate.requested",
            data={"amount": 99.99},
            response_event="payment.validate.completed",
        ),
    ]

    group_id = await task.delegate_parallel(specs)

    # Should have 2 sub-tasks with same group ID
    assert len(task.sub_tasks) == 2
    for sub_task_id, sub_task_info in task.sub_tasks.items():
        assert sub_task_info.parallel_group_id == group_id
        assert sub_task_info.status == "pending"


@pytest.mark.asyncio
async def test_delegate_parallel_publishes_all():
    """TaskContext.delegate_parallel() should publish requests for all specs."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-publish-all",
        event_type="order.check.requested",
        plan_id=None,
        data={},
        response_event="order.check.completed",
        response_topic="action-results",
        _context=context,
    )

    specs = [
        DelegationSpec("check_inventory", {"sku": "A"}, "inventory_checked"),
        DelegationSpec("check_pricing", {"sku": "A"}, "pricing_checked"),
        DelegationSpec("check_availability", {"sku": "A"}, "availability_checked"),
    ]

    await task.delegate_parallel(specs)

    # Should publish 3 requests
    assert context.bus.request.await_count == 3
    
    # Verify event types
    published_events = [
        call.kwargs["event_type"]
        for call in context.bus.request.await_args_list
    ]
    assert "check_inventory" in published_events
    assert "check_pricing" in published_events
    assert "check_availability" in published_events


@pytest.mark.asyncio
async def test_update_sub_task_result():
    """TaskContext.update_sub_task_result() should update individual sub-task."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-update-1",
        event_type="order.process.requested",
        plan_id=None,
        data={},
        response_event="order.process.completed",
        response_topic="action-results",
        _context=context,
    )

    # Create parallel delegation
    specs = [
        DelegationSpec("validate_inventory", {}, "inventory_validated"),
        DelegationSpec("validate_payment", {}, "payment_validated"),
    ]
    await task.delegate_parallel(specs)

    # Get one sub-task ID
    sub_task_id = list(task.sub_tasks.keys())[0]

    # Update with result
    task.update_sub_task_result(sub_task_id, {"valid": True})

    # Verify sub-task updated
    assert task.sub_tasks[sub_task_id].result == {"valid": True}
    assert task.sub_tasks[sub_task_id].status == "completed"


@pytest.mark.asyncio
async def test_aggregate_parallel_results():
    """TaskContext.aggregate_parallel_results() should detect all results arrived."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-aggregate-1",
        event_type="order.validate.requested",
        plan_id=None,
        data={},
        response_event="order.validate.completed",
        response_topic="action-results",
        _context=context,
    )

    # Create parallel delegation
    specs = [
        DelegationSpec("check_inventory", {}, "inventory_checked"),
        DelegationSpec("check_payment", {}, "payment_checked"),
    ]
    group_id = await task.delegate_parallel(specs)

    # Initially, not all results arrived
    assert task.aggregate_parallel_results(group_id) is None

    # Update first sub-task
    sub_task_ids = list(task.sub_tasks.keys())
    task.update_sub_task_result(sub_task_ids[0], {"valid": True})
    
    # Still not all results
    assert task.aggregate_parallel_results(group_id) is None

    # Update second sub-task
    task.update_sub_task_result(sub_task_ids[1], {"valid": False})
    
    # Now all results arrived
    aggregated = task.aggregate_parallel_results(group_id)
    assert aggregated is not None
    assert len(aggregated) == 2


@pytest.mark.asyncio
async def test_aggregate_partial_results():
    """TaskContext.aggregate_parallel_results() should return None if incomplete."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-partial-1",
        event_type="order.check.requested",
        plan_id=None,
        data={},
        response_event="order.check.completed",
        response_topic="action-results",
        _context=context,
    )

    # Create 3 parallel delegations
    specs = [
        DelegationSpec("check_a", {}, "a_checked"),
        DelegationSpec("check_b", {}, "b_checked"),
        DelegationSpec("check_c", {}, "c_checked"),
    ]
    group_id = await task.delegate_parallel(specs)

    # Update only 2 of 3
    sub_task_ids = list(task.sub_tasks.keys())
    task.update_sub_task_result(sub_task_ids[0], {"result": "ok"})
    task.update_sub_task_result(sub_task_ids[1], {"result": "ok"})

    # Should return None (incomplete)
    assert task.aggregate_parallel_results(group_id) is None


# ==============================================================================
# Error Handling Tests (3 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_delegate_without_context():
    """TaskContext.delegate() should raise RuntimeError if no PlatformContext."""
    task = TaskContext(
        task_id="task-no-ctx",
        event_type="demo.requested",
        plan_id=None,
        data={},
        response_event="demo.completed",
        response_topic="action-results",
        _context=None,  # No context
    )

    with pytest.raises(RuntimeError, match="PlatformContext"):
        await task.delegate(
            event_type="sub.requested",
            data={},
            response_event="sub.completed",
        )


@pytest.mark.asyncio
async def test_restore_nonexistent_task():
    """TaskContext.restore() should return None if task not found."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.memory.get_task_context = AsyncMock(return_value=None)

    task = await TaskContext.restore("task-nonexistent", context)

    assert task is None
    context.memory.get_task_context.assert_awaited_once_with(
        "task-nonexistent", tenant_id=None, user_id=None
    )


@pytest.mark.asyncio
async def test_complete_twice():
    """TaskContext.complete() should be idempotent (calling twice should work)."""
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-twice",
        event_type="order.process.requested",
        plan_id=None,
        data={},
        response_event="order.process.completed",
        response_topic="action-results",
        _context=context,
    )

    # Complete twice
    await task.complete({"status": "completed"})
    await task.complete({"status": "completed"})

    # Should respond twice (or handle gracefully)
    assert context.bus.respond.await_count >= 1
    assert context.memory.delete_task_context.await_count >= 1
