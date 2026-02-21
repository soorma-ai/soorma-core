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
        # correlation_ids now includes both plan_id and correlation_id (empty string initially)
        assert call_args["correlation_ids"] == ["plan-123", ""]
    
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
        plan = await PlanContext.restore(
            plan_id="plan-123",
            context=context,
            tenant_id="tenant-1",
            user_id="user-1"
        )
        
        # Verify
        assert plan is not None
        assert plan.plan_id == "plan-123"
        assert plan.goal_event == "test.goal"
        assert plan.status == "running"
        assert plan._context is context
        context.memory.get_plan_context.assert_called_once_with(
            plan_id="plan-123", tenant_id="tenant-1", user_id="user-1"
        )
    
    @pytest.mark.asyncio
    async def test_plan_context_restore_not_found(self):
        """restore() should return None if plan not found."""
        context = MagicMock()
        context.memory.get_plan_context = AsyncMock(return_value=None)
        
        plan = await PlanContext.restore(
            plan_id="unknown",
            context=context,
            tenant_id="tenant-1",
            user_id="user-1"
        )
        
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
        plan = await PlanContext.restore_by_correlation(
            correlation_id="corr-456",
            context=context,
            tenant_id="tenant-1",
            user_id="user-1"
        )
        
        # Verify
        assert plan is not None
        assert plan.plan_id == "plan-123"
        assert plan.goal_data == {"topic": "AI"}
        context.memory.get_plan_by_correlation.assert_called_once_with(
            correlation_id="corr-456", tenant_id="tenant-1", user_id="user-1"
        )
    
    @pytest.mark.asyncio
    async def test_restore_by_correlation_not_found(self):
        """restore_by_correlation() should return None if not found."""
        context = MagicMock()
        context.memory.get_plan_by_correlation = AsyncMock(return_value=None)
        
        plan = await PlanContext.restore_by_correlation(
            correlation_id="unknown",
            context=context,
            tenant_id="tenant-1",
            user_id="user-1"
        )
        
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


class TestPlanContextExecution:
    """Tests for state execution."""
    
    @pytest.mark.asyncio
    async def test_execute_next_initial_state(self):
        """execute_next() should start from initial state when no trigger_event."""
        # State machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial",
                default_next="search",
            ),
            "search": StateConfig(
                state_name="search",
                description="Search state",
                action=StateAction(
                    event_type="search.requested",
                    response_event="search.completed",
                    data={"query": "AI research"},
                ),
            ),
        }
        
        # Mock context
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={"topic": "AI"},
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
        
        # Execute
        await plan.execute_next()
        
        # Verify: published action event
        context.bus.request.assert_called_once()
        call_args = context.bus.request.call_args[1]
        assert call_args["event_type"] == "search.requested"
        assert call_args["response_event"] == "search.completed"
        assert call_args["data"]["query"] == "AI research"
        assert call_args["correlation_id"] == "plan-123"
        
        # Verify: state updated
        assert plan.current_state == "search"
        assert plan.status == "running"
        
        # Verify: saved
        context.memory.store_plan_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_next_with_trigger_event(self):
        """execute_next() should transition based on trigger_event."""
        state_machine = {
            "search": StateConfig(
                state_name="search",
                description="Searching",
                transitions=[
                    StateTransition(on_event="search.completed", to_state="summarize")
                ],
            ),
            "summarize": StateConfig(
                state_name="summarize",
                description="Summarizing",
                action=StateAction(
                    event_type="summarize.requested",
                    response_event="summarize.completed",
                    data={"input": "results"},
                ),
            ),
        }
        
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="search",
            results={},
            session_id="session-456",
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        # Trigger event
        trigger = MagicMock(event_type="search.completed")
        trigger.data = {"papers": ["Paper1", "Paper2"]}
        
        # Execute
        await plan.execute_next(trigger_event=trigger)
        
        # Verify transitioned to summarize
        assert plan.current_state == "summarize"
        context.bus.request.assert_called_once()
        assert context.bus.request.call_args[1]["event_type"] == "summarize.requested"
    
    @pytest.mark.asyncio
    async def test_execute_next_no_action(self):
        """execute_next() should handle states without actions."""
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Start",
                default_next="done",
            ),
            "done": StateConfig(
                state_name="done",
                description="Done",
                is_terminal=True,
            ),
        }
        
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="pending",
            state_machine=state_machine,
            current_state="start",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        # Execute
        await plan.execute_next()
        
        # Verify: transitioned but no event published
        assert plan.current_state == "done"
        context.bus.request.assert_not_called()
        context.memory.store_plan_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_complete_terminal_state(self):
        """is_complete() should return True for terminal states."""
        state_machine = {
            "done": StateConfig(
                state_name="done",
                description="Terminal",
                is_terminal=True,
            ),
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="done",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        assert plan.is_complete() is True
    
    @pytest.mark.asyncio
    async def test_is_complete_non_terminal_state(self):
        """is_complete() should return False for non-terminal states."""
        state_machine = {
            "running": StateConfig(
                state_name="running",
                description="Running",
                is_terminal=False,
            ),
        }
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine=state_machine,
            current_state="running",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        assert plan.is_complete() is False
    
    @pytest.mark.asyncio
    async def test_finalize_uses_response_event(self):
        """finalize() should publish result using original correlation_id."""
        context = MagicMock()
        context.bus.respond = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",  # Explicit from goal
            correlation_id="original-correlation-456",  # Original goal's correlation
            status="running",
            state_machine={},
            current_state="done",
            results={"step1": "data"},
            session_id="session-456",
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        # Finalize
        result = {"summary": "AI is evolving"}
        await plan.finalize(result)
        
        # Verify published to response_event with original correlation_id
        context.bus.respond.assert_called_once()
        call_args = context.bus.respond.call_args[1]
        assert call_args["event_type"] == "research.completed"
        assert call_args["data"]["plan_id"] == "plan-123"
        assert call_args["data"]["result"] == result
        assert call_args["correlation_id"] == "original-correlation-456"
        assert call_args["tenant_id"] == "tenant-1"
        assert call_args["user_id"] == "user-1"
        assert call_args["session_id"] == "session-456"
        
        # Verify status updated
        assert plan.status == "completed"
        context.memory.store_plan_context.assert_called_once()


class TestPlanContextPauseResume:
    """Tests for pause/resume HITL workflows."""
    
    @pytest.mark.asyncio
    async def test_pause_sets_status(self):
        """pause() should update status to paused."""
        context = MagicMock()
        context.memory.store_plan_context = AsyncMock()
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="running",
            state_machine={},
            current_state="waiting",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        await plan.pause(reason="user_approval_required")
        
        assert plan.status == "paused"
        context.memory.store_plan_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resume_continues_execution(self):
        """resume() should update status and call execute_next()."""
        context = MagicMock()
        context.bus.request = AsyncMock()
        context.memory.store_plan_context = AsyncMock()
        
        state_machine = {
            "waiting": StateConfig(
                state_name="waiting",
                description="Waiting",
                default_next="process",
            ),
            "process": StateConfig(
                state_name="process",
                description="Processing",
                action=StateAction(
                    event_type="process.requested",
                    response_event="process.completed",
                    data={"step": "execute"},
                ),
            ),
        }
        
        plan = PlanContext(
            plan_id="plan-hitl",
            goal_event="test.goal",
            goal_data={},
            response_event="test.completed",
            status="paused",
            state_machine=state_machine,
            current_state="waiting",
            results={},
            user_id="user-1",
            tenant_id="tenant-1",
            _context=context,
        )
        
        # Resume
        await plan.resume({"user_input": "approved"})
        
        # Verify status updated
        assert plan.status == "running"
        assert "user_input" in plan.results
        assert plan.results["user_input"] == {"user_input": "approved"}
        
        # Verify execute_next called (state transitioned)
        assert plan.current_state == "process"
        context.bus.request.assert_called_once()


class TestPlanContextCreateFromGoal:
    """Tests for PlanContext.create_from_goal() utility method."""
    
    @pytest.mark.asyncio
    async def test_create_from_goal_creates_plan_record(self):
        """create_from_goal() should call context.memory.create_plan()."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="plan-123"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal
        goal = MagicMock()
        goal.correlation_id = "corr-123"
        goal.data = {"topic": "AI agents"}
        goal.response_event = "research.completed"
        goal.session_id = "session-1"
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "research.goal"
        
        # Define state machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial state",
                default_next="process",
            )
        }
        
        # Create plan from goal
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
        )
        
        # Verify create_plan called
        context.memory.create_plan.assert_called_once()
        call_args = context.memory.create_plan.call_args
        assert call_args.kwargs["plan_id"] == "corr-123"  # Should use correlation_id as plan_id
        assert call_args.kwargs["goal_event"] == "research.goal"
        assert call_args.kwargs["goal_data"] == {"topic": "AI agents"}
        assert call_args.kwargs["tenant_id"] == "tenant-1"
        assert call_args.kwargs["user_id"] == "user-1"
        assert call_args.kwargs["session_id"] == "session-1"
    
    @pytest.mark.asyncio
    async def test_create_from_goal_persists_plan_context(self):
        """create_from_goal() should save PlanContext before returning."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="plan-123"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal
        goal = MagicMock()
        goal.correlation_id = "corr-123"
        goal.data = {"topic": "AI"}
        goal.response_event = "research.completed"
        goal.session_id = "session-1"
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "research.goal"
        
        state_machine = {
            "start": StateConfig(state_name="start", description="Start")
        }
        
        # Create plan from goal
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
        )
        
        # Verify store_plan_context called (plan was saved)
        context.memory.store_plan_context.assert_called_once()
        call_args = context.memory.store_plan_context.call_args
        assert call_args.kwargs["plan_id"] == "corr-123"
        assert call_args.kwargs["session_id"] == "session-1"
    
    @pytest.mark.asyncio
    async def test_create_from_goal_defaults_plan_id_from_correlation(self):
        """plan_id should default to goal.correlation_id when present."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="corr-456"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal with correlation_id
        goal = MagicMock()
        goal.correlation_id = "corr-456"
        goal.data = {}
        goal.response_event = "test.completed"
        goal.session_id = None
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "test.goal"
        
        state_machine = {
            "start": StateConfig(state_name="start", description="Start")
        }
        
        # Create plan without explicit plan_id
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
        )
        
        # Verify plan_id equals correlation_id
        assert plan.plan_id == "corr-456"
        assert plan.correlation_id == "corr-456"
    
    @pytest.mark.asyncio
    async def test_create_from_goal_generates_uuid_when_missing_correlation(self):
        """plan_id should generate UUID when goal.correlation_id is empty."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="generated-uuid"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal without correlation_id
        goal = MagicMock()
        goal.correlation_id = ""  # Empty
        goal.data = {}
        goal.response_event = "test.completed"
        goal.session_id = None
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "test.goal"
        
        state_machine = {
            "start": StateConfig(state_name="start", description="Start")
        }
        
        # Create plan
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
        )
        
        # Verify plan_id was generated (not empty)
        assert plan.plan_id != ""
        assert len(plan.plan_id) > 0
        # UUID format check (should have dashes)
        assert "-" in plan.plan_id
    
    @pytest.mark.asyncio
    async def test_create_from_goal_accepts_explicit_plan_id(self):
        """create_from_goal() should allow explicit plan_id override."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="custom-plan-123"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal
        goal = MagicMock()
        goal.correlation_id = "corr-999"
        goal.data = {}
        goal.response_event = "test.completed"
        goal.session_id = None
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "test.goal"
        
        state_machine = {
            "start": StateConfig(state_name="start", description="Start")
        }
        
        # Create plan with explicit plan_id
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="pending",
            plan_id="custom-plan-123",  # Explicit override
        )
        
        # Verify explicit plan_id was used
        assert plan.plan_id == "custom-plan-123"
        # But correlation_id should still be from goal
        assert plan.correlation_id == "corr-999"
    
    @pytest.mark.asyncio
    async def test_create_from_goal_initializes_all_fields(self):
        """create_from_goal() should properly initialize all PlanContext fields."""
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="plan-full"))
        context.memory.store_plan_context = AsyncMock()
        
        # Mock goal
        goal = MagicMock()
        goal.correlation_id = "corr-full"
        goal.data = {"key": "value"}
        goal.response_event = "goal.completed"
        goal.session_id = "session-abc"
        goal.user_id = "user-xyz"
        goal.tenant_id = "tenant-123"
        goal.event_type = "test.goal"
        
        state_machine = {
            "start": StateConfig(state_name="start", description="Start"),
            "done": StateConfig(state_name="done", description="Done", is_terminal=True),
        }
        
        # Create plan with all parameters
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine=state_machine,
            current_state="start",
            status="running",
            results={"initial": "data"},
            parent_plan_id="parent-123",
        )
        
        # Verify all fields initialized correctly
        assert plan.plan_id == "corr-full"
        assert plan.goal_event == "test.goal"
        assert plan.goal_data == {"key": "value"}
        assert plan.response_event == "goal.completed"
        assert plan.correlation_id == "corr-full"
        assert plan.status == "running"
        assert plan.state_machine == state_machine
        assert plan.current_state == "start"
        assert plan.results == {"initial": "data"}
        assert plan.parent_plan_id == "parent-123"
        assert plan.session_id == "session-abc"
        assert plan.user_id == "user-xyz"
        assert plan.tenant_id == "tenant-123"
        assert plan._context is context

