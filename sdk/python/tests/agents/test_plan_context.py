"""
Tests for PlanContext state machine.

Tests cover:
- Persistence (to_dict, from_dict, save, restore)
- State transitions (get_next_state)
- Execution (execute_next, is_complete, finalize)
- Pause/resume for HITL workflows
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.plan_context import PlanContext
from soorma_common.state import StateConfig, StateTransition, StateAction


class TestPlanContextPersistence:
    """Tests for plan persistence and restoration."""
    
    @pytest.mark.asyncio
    async def test_plan_context_to_dict(self):
        """PlanContext.to_dict() should serialize all fields."""
        # Create plan with state machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial state",
                is_terminal=False,
                default_next="search",
            )
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            status="pending",
            state_machine=state_machine,
            current_state="start",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        # Serialize
        data = plan.to_dict()
        
        # Verify all fields present
        assert data["plan_id"] == "plan-123"
        assert data["goal_event"] == "research.goal"
        assert data["goal_data"] == {"topic": "AI"}
        assert data["response_event"] == "research.completed"
        assert data["status"] == "pending"
        assert data["current_state"] == "start"
        assert data["results"] == {}
        assert data["user_id"] == "user-1"
        assert data["tenant_id"] == "tenant-1"
        
        # Verify state machine serialized (StateConfig should be dict)
        assert "state_machine" in data
        assert "start" in data["state_machine"]
        assert data["state_machine"]["start"]["state_name"] == "start"
        assert data["state_machine"]["start"]["description"] == "Initial state"
    
    @pytest.mark.asyncio
    async def test_plan_context_from_dict(self):
        """PlanContext.from_dict() should restore from serialized data."""
        # Mock context
        context = MagicMock()
        
        # Serialized data (as would come from Memory Service)
        data = {
            "plan_id": "plan-123",
            "goal_event": "research.goal",
            "goal_data": {"topic": "AI"},
            "response_event": "research.completed",
            "status": "pending",
            "state_machine": {
                "start": {
                    "state_name": "start",
                    "description": "Initial state",
                    "is_terminal": False,
                    "default_next": "search",
                    "action": None,
                    "transitions": []
                }
            },
            "current_state": "start",
            "results": {},
            "parent_plan_id": None,
            "session_id": None,
            "user_id": "user-1",
            "tenant_id": "tenant-1",
        }
        
        # Restore
        plan = PlanContext.from_dict(data, context)
        
        # Verify all fields restored
        assert plan.plan_id == "plan-123"
        assert plan.goal_event == "research.goal"
        assert plan.goal_data == {"topic": "AI"}
        assert plan.response_event == "research.completed"
        assert plan.status == "pending"
        assert plan.current_state == "start"
        assert plan.results == {}
        assert plan.user_id == "user-1"
        assert plan.tenant_id == "tenant-1"
        
        # Verify context attached
        assert plan._context is context
        
        # Verify state machine restored as StateConfig objects
        assert "start" in plan.state_machine
        assert isinstance(plan.state_machine["start"], StateConfig)
        assert plan.state_machine["start"].state_name == "start"
    
    @pytest.mark.asyncio
    async def test_plan_context_roundtrip(self):
        """to_dict() followed by from_dict() should recreate plan."""
        # Original plan
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Start",
                default_next="process",
            ),
            "process": StateConfig(
                state_name="process",
                description="Processing",
                action=StateAction(
                    event_type="task.requested",
                    response_event="task.completed",
                    data={"input": "test"},
                ),
                transitions=[
                    StateTransition(on_event="task.completed", to_state="done")
                ],
            ),
            "done": StateConfig(
                state_name="done",
                description="Terminal",
                is_terminal=True,
            ),
        }
        
        original = PlanContext(
            plan_id="plan-roundtrip",
            goal_event="test.goal",
            goal_data={"key": "value"},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="process",
            results={"step1": "done"},
            parent_plan_id="parent-123",
            session_id="session-456",
            user_id="user-test",
            tenant_id="tenant-test",
        )
        
        # Serialize
        data = original.to_dict()
        
        # Restore
        context = MagicMock()
        restored = PlanContext.from_dict(data, context)
        
        # Verify match
        assert restored.plan_id == original.plan_id
        assert restored.goal_event == original.goal_event
        assert restored.goal_data == original.goal_data
        assert restored.response_event == original.response_event
        assert restored.status == original.status
        assert restored.current_state == original.current_state
        assert restored.results == original.results
        assert restored.parent_plan_id == original.parent_plan_id
        assert restored.session_id == original.session_id
        assert restored.user_id == original.user_id
        assert restored.tenant_id == original.tenant_id
        
        # Verify state machine structure preserved
        assert len(restored.state_machine) == len(original.state_machine)
        assert "start" in restored.state_machine
        assert "process" in restored.state_machine
        assert "done" in restored.state_machine
        
        # Verify state details
        assert restored.state_machine["process"].action is not None
        assert restored.state_machine["process"].action.event_type == "task.requested"
        assert len(restored.state_machine["process"].transitions) == 1
        assert restored.state_machine["done"].is_terminal is True
    
    @pytest.mark.asyncio
    async def test_plan_context_save_calls_memory(self):
        """save() should call memory.store_plan_context()."""
        # Mock context
        context = MagicMock()
        context.memory.store_plan_context = AsyncMock()
        
        # Create plan
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial",
            )
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={"key": "value"},
            response_event="test.completed",
            status="pending",
            state_machine=state_machine,
            current_state="start",
            results={},
            session_id="session-456",
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        # Save
        await plan.save()
        
        # Verify Memory Service called
        context.memory.store_plan_context.assert_called_once()
        call_args = context.memory.store_plan_context.call_args[1]
        assert call_args["plan_id"] == "plan-123"
        assert call_args["session_id"] == "session-456"
        assert call_args["goal_event"] == "test.goal"
        assert call_args["goal_data"] == {"key": "value"}
        assert call_args["response_event"] == "test.completed"
        assert "state" in call_args
        assert call_args["current_state"] == "start"
        assert call_args["correlation_ids"] == ["plan-123"]
    
    @pytest.mark.asyncio
    async def test_plan_context_restore(self):
        """restore() should load from Memory Service."""
        # Mock context
        context = MagicMock()
        context.memory.get_plan_context = AsyncMock(return_value={
            "plan_id": "plan-123",
            "session_id": "session-456",
            "goal_event": "test.goal",
            "goal_data": {"key": "value"},
            "response_event": "test.completed",
            "state": {
                "plan_id": "plan-123",
                "goal_event": "test.goal",
                "goal_data": {"key": "value"},
                "response_event": "test.completed",
                "status": "running",
                "state_machine": {
                    "start": {
                        "state_name": "start",
                        "description": "Initial",
                        "is_terminal": False,
                        "default_next": None,
                        "action": None,
                        "transitions": [],
                    }
                },
                "current_state": "start",
                "results": {},
                "parent_plan_id": None,
                "session_id": "session-456",
                "user_id": "user-1",
                "tenant_id": "tenant-1",
            },
            "current_state": "start",
            "correlation_ids": ["plan-123"],
        })
        
        # Restore
        plan = await PlanContext.restore("plan-123", context)
        
        # Verify
        assert plan is not None
        assert plan.plan_id == "plan-123"
        assert plan.goal_event == "test.goal"
        assert plan.status == "running"
        assert plan._context is context
        context.memory.get_plan_context.assert_called_once_with("plan-123")
    
    @pytest.mark.asyncio
    async def test_plan_context_restore_not_found(self):
        """restore() should return None if plan not found."""
        context = MagicMock()
        context.memory.get_plan_context = AsyncMock(return_value=None)
        
        plan = await PlanContext.restore("unknown", context)
        
        assert plan is None
    
    @pytest.mark.asyncio
    async def test_plan_context_restore_by_correlation(self):
        """restore_by_correlation() should find plan by correlation_id."""
        # Mock context
        context = MagicMock()
        context.memory.get_plan_by_correlation = AsyncMock(return_value={
            "plan_id": "plan-123",
            "session_id": "session-456",
            "goal_event": "test.goal",
            "goal_data": {"topic": "AI"},
            "response_event": "test.completed",
            "state": {
                "plan_id": "plan-123",
                "goal_event": "test.goal",
                "goal_data": {"topic": "AI"},
                "response_event": "test.completed",
                "status": "running",
                "state_machine": {
                    "start": {
                        "state_name": "start",
                        "description": "Initial",
                        "is_terminal": False,
                        "default_next": None,
                        "action": None,
                        "transitions": [],
                    }
                },
                "current_state": "start",
                "results": {},
                "parent_plan_id": None,
                "session_id": "session-456",
                "user_id": "user-1",
                "tenant_id": "tenant-1",
            },
            "current_state": "start",
            "correlation_ids": ["corr-456"],
        })
        
        # Restore
        plan = await PlanContext.restore_by_correlation("corr-456", context)
        
        # Verify
        assert plan is not None
        assert plan.plan_id == "plan-123"
        assert plan.goal_data == {"topic": "AI"}
        context.memory.get_plan_by_correlation.assert_called_once_with("corr-456")
    
    @pytest.mark.asyncio
    async def test_restore_by_correlation_not_found(self):
        """restore_by_correlation() should return None if not found."""
        context = MagicMock()
        context.memory.get_plan_by_correlation = AsyncMock(return_value=None)
        
        plan = await PlanContext.restore_by_correlation("unknown", context)
        
        assert plan is None


class TestPlanContextStateTransitions:
    """Tests for state machine transitions."""
    
    @pytest.mark.asyncio
    async def test_get_next_state_with_matching_event(self):
        """get_next_state() should return target state for matching event."""
        # State machine: start -> searching (on search.completed)
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial",
                transitions=[
                    StateTransition(on_event="search.completed", to_state="searching")
                ],
            ),
            "searching": StateConfig(state_name="searching", description="Searching"),
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="start",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        # Mock event
        event = MagicMock()
        event.event_type = "search.completed"
        
        # Get next state
        next_state = plan.get_next_state(event)
        
        assert next_state == "searching"
    
    @pytest.mark.asyncio
    async def test_get_next_state_no_matching_transition(self):
        """get_next_state() should return None for unrecognized events."""
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Start state",
                transitions=[
                    StateTransition(on_event="search.completed", to_state="searching")
                ],
            ),
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="start",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        event = MagicMock()
        event.event_type = "unknown.event"
        
        next_state = plan.get_next_state(event)
        
        assert next_state is None
    
    @pytest.mark.asyncio
    async def test_get_next_state_multiple_transitions(self):
        """State can have multiple transitions based on different events."""
        state_machine = {
            "processing": StateConfig(
                state_name="processing",
                description="Processing",
                transitions=[
                    StateTransition(on_event="task.succeeded", to_state="success"),
                    StateTransition(on_event="task.failed", to_state="retry"),
                ],
            ),
            "success": StateConfig(state_name="success", description="Success"),
            "retry": StateConfig(state_name="retry", description="Retry"),
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="processing",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        # Test success path
        success_event = MagicMock(event_type="task.succeeded")
        assert plan.get_next_state(success_event) == "success"
        
        # Test failure path
        failure_event = MagicMock(event_type="task.failed")
        assert plan.get_next_state(failure_event) == "retry"

