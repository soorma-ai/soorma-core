"""Tests for task context functionality."""

import pytest
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.services.task_context_service import TaskContextService
from memory_service.crud.task_context import (
    upsert_task_context,
    get_task_context,
    update_task_context,
    delete_task_context,
    get_task_by_subtask,
)
from soorma_common.models import TaskContextCreate, TaskContextUpdate


class TestTaskContextCRUD:
    """Test task context CRUD operations."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "user_id": uuid4(),
            "task_id": str(uuid4()),
            "plan_id": str(uuid4()),
        }

    @pytest.fixture
    def task_data(self, test_ids):
        """Generate test task context data."""
        return {
            "tenant_id": test_ids["tenant_id"],
            "user_id": test_ids["user_id"],
            "task_id": test_ids["task_id"],
            "plan_id": test_ids["plan_id"],
            "event_type": "order.process.requested",
            "response_event": "order.process.completed",
            "response_topic": "action-results",
            "data": {"order_id": "ORD-001", "customer": "Alice"},
            "sub_tasks": ["subtask-1", "subtask-2"],
            "state": {"status": "pending", "progress": 0},
        }

    async def test_upsert_create(self, db_session: AsyncSession, task_data):
        """Test upsert creates new task context."""
        result = await upsert_task_context(db_session, **task_data)
        
        assert result.task_id == task_data["task_id"]
        assert result.plan_id == task_data["plan_id"]
        assert result.event_type == task_data["event_type"]
        assert result.response_event == task_data["response_event"]
        assert result.data == task_data["data"]
        assert result.sub_tasks == task_data["sub_tasks"]
        assert result.state == task_data["state"]

    async def test_upsert_update(self, db_session: AsyncSession, task_data):
        """Test upsert updates existing task context."""
        # Create initial task context
        await upsert_task_context(db_session, **task_data)
        
        # Update with new data
        updated_data = task_data.copy()
        updated_data["sub_tasks"] = ["subtask-1", "subtask-2", "subtask-3"]
        updated_data["state"] = {"status": "in_progress", "progress": 50}
        updated_data["data"] = {"order_id": "ORD-001", "customer": "Alice", "total": 1500.0}
        
        result = await upsert_task_context(db_session, **updated_data)
        
        assert result.task_id == task_data["task_id"]
        assert len(result.sub_tasks) == 3
        assert result.state["status"] == "in_progress"
        assert result.state["progress"] == 50
        assert result.data["total"] == 1500.0

    async def test_upsert_idempotent(self, db_session: AsyncSession, task_data):
        """Test upsert is idempotent - multiple calls with same data."""
        result1 = await upsert_task_context(db_session, **task_data)
        result2 = await upsert_task_context(db_session, **task_data)
        result3 = await upsert_task_context(db_session, **task_data)
        
        # All should have same task_id but potentially different updated_at
        assert result1.task_id == result2.task_id == result3.task_id
        assert result1.tenant_id == result2.tenant_id == result3.tenant_id
        assert result1.data == result2.data == result3.data

    async def test_get_task_context(self, db_session: AsyncSession, task_data):
        """Test retrieving task context by task_id."""
        await upsert_task_context(db_session, **task_data)
        
        result = await get_task_context(
            db_session,
            task_data["tenant_id"],
            task_data["task_id"],
        )
        
        assert result is not None
        assert result.task_id == task_data["task_id"]
        assert result.data == task_data["data"]

    async def test_get_task_context_not_found(self, db_session: AsyncSession, test_ids):
        """Test retrieving non-existent task context returns None."""
        result = await get_task_context(
            db_session,
            test_ids["tenant_id"],
            "non-existent-task",
        )
        
        assert result is None

    async def test_update_task_context(self, db_session: AsyncSession, task_data):
        """Test updating task context sub_tasks and state."""
        await upsert_task_context(db_session, **task_data)
        
        new_sub_tasks = ["subtask-1", "subtask-2", "subtask-3", "subtask-4"]
        new_state = {"status": "completed", "progress": 100}
        
        result = await update_task_context(
            db_session,
            task_data["tenant_id"],
            task_data["task_id"],
            sub_tasks=new_sub_tasks,
            state=new_state,
        )
        
        assert result is not None
        assert result.sub_tasks == new_sub_tasks
        assert result.state == new_state

    async def test_delete_task_context(self, db_session: AsyncSession, task_data):
        """Test deleting task context."""
        await upsert_task_context(db_session, **task_data)
        
        # Delete
        deleted = await delete_task_context(
            db_session,
            task_data["tenant_id"],
            task_data["task_id"],
        )
        
        assert deleted is True
        
        # Verify deleted
        result = await get_task_context(
            db_session,
            task_data["tenant_id"],
            task_data["task_id"],
        )
        
        assert result is None

    async def test_delete_non_existent(self, db_session: AsyncSession, test_ids):
        """Test deleting non-existent task context returns False."""
        deleted = await delete_task_context(
            db_session,
            test_ids["tenant_id"],
            "non-existent-task",
        )
        
        assert deleted is False

    async def test_get_task_by_subtask(self, db_session: AsyncSession, task_data):
        """Test finding parent task by sub-task ID."""
        await upsert_task_context(db_session, **task_data)
        
        result = await get_task_by_subtask(
            db_session,
            task_data["tenant_id"],
            "subtask-1",
        )
        
        assert result is not None
        assert result.task_id == task_data["task_id"]
        assert "subtask-1" in result.sub_tasks

    async def test_get_task_by_subtask_not_found(self, db_session: AsyncSession, test_ids):
        """Test finding parent task with non-existent sub-task returns None."""
        result = await get_task_by_subtask(
            db_session,
            test_ids["tenant_id"],
            "non-existent-subtask",
        )
        
        assert result is None

    async def test_multi_tenant_isolation(self, db_session: AsyncSession, task_data):
        """Test task context is isolated by tenant_id."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        task_id = str(uuid4())
        
        # Create task for tenant 1
        data1 = task_data.copy()
        data1["tenant_id"] = tenant1_id
        data1["task_id"] = task_id
        await upsert_task_context(db_session, **data1)
        
        # Create task with same task_id for tenant 2
        data2 = task_data.copy()
        data2["tenant_id"] = tenant2_id
        data2["task_id"] = task_id
        data2["data"] = {"different": "data"}
        await upsert_task_context(db_session, **data2)
        
        # Retrieve for tenant 1
        result1 = await get_task_context(db_session, tenant1_id, task_id)
        assert result1 is not None
        assert result1.data == data1["data"]
        
        # Retrieve for tenant 2
        result2 = await get_task_context(db_session, tenant2_id, task_id)
        assert result2 is not None
        assert result2.data == data2["data"]


class TestTaskContextService:
    """Test task context service layer."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return TaskContextService()

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "user_id": uuid4(),
            "task_id": str(uuid4()),
            "plan_id": str(uuid4()),
        }

    @pytest.fixture
    def task_context_create(self, test_ids):
        """Generate TaskContextCreate DTO."""
        return TaskContextCreate(
            task_id=test_ids["task_id"],
            plan_id=test_ids["plan_id"],
            event_type="payment.process.requested",
            response_event="payment.process.completed",
            response_topic="action-results",
            data={"amount": 1500.0, "currency": "USD"},
            sub_tasks=["validate", "charge", "notify"],
            state={"step": "validation"},
            user_id=str(test_ids["user_id"]),
        )

    async def test_service_upsert(
        self,
        db_session: AsyncSession,
        service: TaskContextService,
        test_ids,
        task_context_create,
    ):
        """Test service upsert operation."""
        result = await service.upsert(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            task_context_create,
        )
        
        assert result.task_id == task_context_create.task_id
        assert result.event_type == task_context_create.event_type
        assert result.data == task_context_create.data
        assert result.tenant_id == str(test_ids["tenant_id"])

    async def test_service_get(
        self,
        db_session: AsyncSession,
        service: TaskContextService,
        test_ids,
        task_context_create,
    ):
        """Test service get operation."""
        await service.upsert(db_session, test_ids["tenant_id"], test_ids["user_id"], task_context_create)
        
        result = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["task_id"],
        )
        
        assert result is not None
        assert result.task_id == task_context_create.task_id

    async def test_service_update(
        self,
        db_session: AsyncSession,
        service: TaskContextService,
        test_ids,
        task_context_create,
    ):
        """Test service update operation."""
        await service.upsert(db_session, test_ids["tenant_id"], test_ids["user_id"], task_context_create)
        
        update_data = TaskContextUpdate(
            sub_tasks=["validate", "charge", "notify", "confirm"],
            state={"step": "charging", "attempt": 1},
        )
        
        result = await service.update(
            db_session,
            test_ids["tenant_id"],
            test_ids["task_id"],
            update_data,
        )
        
        assert result is not None
        assert len(result.sub_tasks) == 4
        assert result.state["step"] == "charging"

    async def test_service_delete(
        self,
        db_session: AsyncSession,
        service: TaskContextService,
        test_ids,
        task_context_create,
    ):
        """Test service delete operation."""
        await service.upsert(db_session, test_ids["tenant_id"], test_ids["user_id"], task_context_create)
        
        deleted = await service.delete(
            db_session,
            test_ids["tenant_id"],
            test_ids["task_id"],
        )
        
        assert deleted is True
        
        # Verify deleted
        result = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["task_id"],
        )
        
        assert result is None

    async def test_service_get_by_subtask(
        self,
        db_session: AsyncSession,
        service: TaskContextService,
        test_ids,
        task_context_create,
    ):
        """Test service get by subtask operation."""
        await service.upsert(db_session, test_ids["tenant_id"], test_ids["user_id"], task_context_create)
        
        result = await service.get_by_subtask(
            db_session,
            test_ids["tenant_id"],
            "validate",
        )
        
        assert result is not None
        assert result.task_id == task_context_create.task_id
        assert "validate" in result.sub_tasks


class TestTaskContextSubTaskTracking:
    """Test sub-task tracking functionality."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "user_id": uuid4(),
            "parent_task_id": str(uuid4()),
            "subtask_ids": [str(uuid4()) for _ in range(3)],
        }

    async def test_parallel_subtask_tracking(self, db_session: AsyncSession, test_ids):
        """Test tracking parallel sub-tasks."""
        task_data = {
            "tenant_id": test_ids["tenant_id"],
            "user_id": test_ids["user_id"],
            "task_id": test_ids["parent_task_id"],
            "plan_id": None,
            "event_type": "order.process.requested",
            "response_event": "order.process.completed",
            "response_topic": "action-results",
            "data": {"order_id": "ORD-001"},
            "sub_tasks": test_ids["subtask_ids"],
            "state": {
                "_sub_tasks": {
                    test_ids["subtask_ids"][0]: {
                        "status": "pending",
                        "event_type": "inventory.reserve.requested",
                    },
                    test_ids["subtask_ids"][1]: {
                        "status": "pending",
                        "event_type": "payment.process.requested",
                    },
                    test_ids["subtask_ids"][2]: {
                        "status": "pending",
                        "event_type": "notification.send.requested",
                    },
                }
            },
        }
        
        result = await upsert_task_context(db_session, **task_data)
        
        assert len(result.sub_tasks) == 3
        assert len(result.state["_sub_tasks"]) == 3
        
        # Test lookup by each sub-task
        for subtask_id in test_ids["subtask_ids"]:
            parent = await get_task_by_subtask(
                db_session,
                test_ids["tenant_id"],
                subtask_id,
            )
            assert parent is not None
            assert parent.task_id == test_ids["parent_task_id"]

    async def test_subtask_state_updates(self, db_session: AsyncSession, test_ids):
        """Test updating sub-task states."""
        subtask_ids = test_ids["subtask_ids"]
        
        # Create with pending sub-tasks
        task_data = {
            "tenant_id": test_ids["tenant_id"],
            "user_id": test_ids["user_id"],
            "task_id": test_ids["parent_task_id"],
            "plan_id": None,
            "event_type": "order.process.requested",
            "response_event": "order.process.completed",
            "response_topic": "action-results",
            "data": {"order_id": "ORD-001"},
            "sub_tasks": subtask_ids,
            "state": {
                "_sub_tasks": {
                    subtask_ids[0]: {"status": "pending"},
                    subtask_ids[1]: {"status": "pending"},
                    subtask_ids[2]: {"status": "pending"},
                }
            },
        }
        
        await upsert_task_context(db_session, **task_data)
        
        # Update first sub-task to completed
        task_data["state"]["_sub_tasks"][subtask_ids[0]]["status"] = "completed"
        task_data["state"]["_sub_tasks"][subtask_ids[0]]["result"] = {"success": True}
        
        result = await upsert_task_context(db_session, **task_data)
        
        assert result.state["_sub_tasks"][subtask_ids[0]]["status"] == "completed"
        assert result.state["_sub_tasks"][subtask_ids[0]]["result"]["success"] is True
        assert result.state["_sub_tasks"][subtask_ids[1]]["status"] == "pending"
