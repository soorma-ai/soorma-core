"""
Tests for Worker async model (RF-SDK-004).
"""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from soorma_common.events import EventEnvelope, EventTopic

from soorma.task_context import TaskContext, SubTaskInfo, ResultContext
from soorma import Worker


@pytest.mark.asyncio
async def test_task_context_save_calls_memory():
    context = MagicMock()
    context.memory = AsyncMock()

    task = TaskContext(
        task_id="task-1",
        event_type="demo.requested",
        plan_id="plan-1",
        data={"input": "value"},
        response_event="demo.completed",
        response_topic="action-results",
        _context=context,
    )
    task.sub_tasks["sub-1"] = SubTaskInfo(
        sub_task_id="sub-1",
        event_type="sub.requested",
        response_event="sub.completed",
        status="pending",
    )
    task.state["note"] = "working"

    await task.save()

    context.memory.store_task_context.assert_awaited_once()
    kwargs = context.memory.store_task_context.await_args.kwargs
    assert kwargs["task_id"] == "task-1"
    assert kwargs["event_type"] == "demo.requested"
    assert kwargs["response_event"] == "demo.completed"
    assert kwargs["sub_tasks"] == ["sub-1"]
    assert kwargs["state"]["note"] == "working"
    assert kwargs["state"]["_sub_tasks"]["sub-1"]["status"] == "pending"


@pytest.mark.asyncio
async def test_task_context_delegate_publishes_request():
    context = MagicMock()
    context.memory = AsyncMock()
    context.bus = AsyncMock()

    task = TaskContext(
        task_id="task-2",
        event_type="demo.requested",
        plan_id="plan-2",
        data={"input": "value"},
        response_event="demo.completed",
        response_topic="action-results",
        _context=context,
    )

    sub_task_id = await task.delegate(
        event_type="child.requested",
        data={"x": 1},
        response_event="child.completed",
    )

    assert sub_task_id in task.sub_tasks
    context.bus.request.assert_awaited_once()
    call_kwargs = context.bus.request.await_args.kwargs
    assert call_kwargs["event_type"] == "child.requested"
    assert call_kwargs["response_event"] == "child.completed"
    assert call_kwargs["correlation_id"] == sub_task_id


@pytest.mark.asyncio
async def test_result_context_restore_task():
    context = MagicMock()
    context.memory = AsyncMock()

    task_data = SimpleNamespace(
        task_id="task-3",
        plan_id="plan-3",
        event_type="demo.requested",
        response_event="demo.completed",
        response_topic="action-results",
        data={"input": "value"},
        sub_tasks=["sub-2"],
        state={
            "_sub_tasks": {
                "sub-2": {
                    "sub_task_id": "sub-2",
                    "event_type": "child.requested",
                    "response_event": "child.completed",
                    "status": "pending",
                }
            }
        },
        tenant_id=None,
        user_id=None,
    )

    context.memory.get_task_by_subtask = AsyncMock(return_value=task_data)

    result = ResultContext(
        event_type="child.completed",
        correlation_id="sub-2",
        data={"result": "ok"},
        success=True,
        error=None,
        _context=context,
    )

    task = await result.restore_task()

    assert task.task_id == "task-3"
    assert "sub-2" in task.sub_tasks


@pytest.mark.asyncio
async def test_worker_on_task_wrapper_passes_task_context():
    worker = Worker(name="demo-worker")
    received = {}

    @worker.on_task("demo.requested")
    async def handle(task, context):
        received["task"] = task

    event = EventEnvelope(
        source="tester",
        type="demo.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data={"task_id": "task-4"},
        response_event="demo.completed",
    )

    context = MagicMock()
    wrapper = worker._event_handlers["action-requests:demo.requested"][0]
    await wrapper(event, context)

    assert isinstance(received.get("task"), TaskContext)
    assert received["task"].task_id == "task-4"


@pytest.mark.asyncio
async def test_worker_on_result_wrapper_passes_result_context():
    worker = Worker(name="demo-worker")
    received = {}

    @worker.on_result("demo.completed")
    async def handle(result, context):
        received["result"] = result

    event = EventEnvelope(
        source="tester",
        type="demo.completed",
        topic=EventTopic.ACTION_RESULTS,
        data={"status": "completed"},
    )

    context = MagicMock()
    wrapper = worker._event_handlers["action-results:demo.completed"][0]
    await wrapper(event, context)

    assert isinstance(received.get("result"), ResultContext)
    assert received["result"].event_type == "demo.completed"
