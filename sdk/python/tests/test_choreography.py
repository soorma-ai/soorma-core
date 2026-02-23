"""Tests for ChoreographyPlanner - Autonomous LLM-based orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soorma.ai.choreography import ChoreographyPlanner
from soorma.plan_context import PlanContext
from soorma_common.decisions import (
    PlannerDecision,
    PlanAction,
    PublishAction,
    CompleteAction,
    WaitAction,
    DelegateAction,
)


class TestChoreographyPlannerInitialization:
    """Tests for ChoreographyPlanner initialization."""
    
    def test_choreography_planner_initialization(self):
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
        assert planner.planning_strategy == "balanced"  # Default
        assert planner.system_instructions is None  # Default
    
    def test_choreography_planner_with_system_instructions(self):
        """ChoreographyPlanner accepts system_instructions."""
        instructions = "You are a financial planning agent. Always require approval for >$5k."
        
        planner = ChoreographyPlanner(
            name="financial-planner",
            reasoning_model="gpt-4o",
            system_instructions=instructions,
        )
        
        assert planner.system_instructions == instructions
    
    def test_choreography_planner_with_planning_strategy(self):
        """ChoreographyPlanner accepts planning_strategy."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            planning_strategy="conservative",
        )
        
        assert planner.planning_strategy == "conservative"


class TestChoreographyPlannerPromptBuilding:
    """Tests for prompt generation and strategy guidance."""
    
    def test_build_prompt_includes_trigger(self):
        """_build_prompt includes trigger in prompt."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = [
            MagicMock(event_name="search.requested", description="Search for information"),
        ]
        
        prompt = planner._build_prompt("New goal received", mock_events)
        
        assert "New goal received" in prompt
        assert "Trigger:" in prompt
    
    def test_build_prompt_includes_available_events(self):
        """_build_prompt lists available events."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = [
            MagicMock(event_name="search.requested", description="Search for info"),
            MagicMock(event_name="analyze.requested", description="Analyze data"),
        ]
        
        prompt = planner._build_prompt("trigger", mock_events)
        
        assert "search.requested" in prompt
        assert "analyze.requested" in prompt
        assert "Available events" in prompt
    
    def test_build_prompt_with_custom_context(self):
        """_build_prompt includes custom_context when provided."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = []
        custom_context = {
            "customer": {"tier": "premium"},
            "inventory": {"stock_level": "low"},
        }
        
        prompt = planner._build_prompt("trigger", mock_events, custom_context)
        
        assert "premium" in prompt
        assert "stock_level" in prompt
        assert "Additional Context" in prompt
    
    def test_get_strategy_guidance_conservative(self):
        """_get_strategy_guidance returns conservative strategy text."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            planning_strategy="conservative",
        )
        
        guidance = planner._get_strategy_guidance()
        
        assert "safety" in guidance.lower()
        assert "compliance" in guidance.lower() or "human review" in guidance.lower()
    
    def test_get_strategy_guidance_aggressive(self):
        """_get_strategy_guidance returns aggressive strategy text."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            planning_strategy="aggressive",
        )
        
        guidance = planner._get_strategy_guidance()
        
        assert "speed" in guidance.lower() or "automation" in guidance.lower()
    
    def test_get_strategy_guidance_balanced(self):
        """_get_strategy_guidance returns balanced strategy text."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            planning_strategy="balanced",
        )
        
        guidance = planner._get_strategy_guidance()
        
        assert "balance" in guidance.lower()


class TestChoreographyPlannerReasoning:
    """Tests for LLM reasoning and event discovery."""
    
    @pytest.mark.asyncio
    async def test_reason_next_action_discovers_events(self):
        """reason_next_action queries Registry for available events."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        # Mock context
        context = MagicMock()
        mock_events = [MagicMock(event_name="search.requested")]
        context.toolkit.discover_actionable_events = AsyncMock(return_value=mock_events)
        
        # Mock LiteLLM module import
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"plan_id":"p1","current_state":"s","next_action":{"action":"publish","event_type":"search.requested","reasoning":"search"},"reasoning":"test","confidence":1.0}'
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        
        # Inject mock directly into planner to simulate successful import
        planner._litellm = mock_litellm
        
        decision = await planner.reason_next_action("trigger", context)
        
        # Verify event discovery called
        context.toolkit.discover_actionable_events.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reason_next_action_calls_litellm(self):
        """reason_next_action calls LiteLLM with correct parameters."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            temperature=0.7,
        )
        
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(
            return_value=[MagicMock(event_name="complete.action", description="Complete")]
        )
        
        # Mock LiteLLM
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"plan_id":"p1","current_state":"s","next_action":{"action":"complete","result":{},"reasoning":"done"},"reasoning":"test","confidence":1.0}'
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        await planner.reason_next_action("trigger", context)
        
        # Verify LiteLLM called
        mock_litellm.acompletion.assert_called_once()
        call_args = mock_litellm.acompletion.call_args
        
        assert call_args.kwargs["model"] == "gpt-4o"
        assert call_args.kwargs["temperature"] == 0.7
        assert len(call_args.kwargs["messages"]) == 2  # system + user
    
    @pytest.mark.asyncio
    async def test_reason_next_action_with_custom_context(self):
        """reason_next_action includes custom_context in prompt."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(
            return_value=[MagicMock(event_name="complete.action", description="Complete")]
        )
        
        custom_context = {"customer": {"tier": "premium"}}
        
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"plan_id":"p1","current_state":"s","next_action":{"action":"complete","result":{},"reasoning":"done"},"reasoning":"test","confidence":1.0}'
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        await planner.reason_next_action("trigger", context, custom_context=custom_context)
        
        # Verify custom context in prompt
        call_args = mock_litellm.acompletion.call_args
        user_message = call_args.kwargs["messages"][1]["content"]
        
        assert "premium" in user_message


class TestChoreographyPlannerValidation:
    """Tests for event validation and hallucination prevention."""
    
    @pytest.mark.asyncio
    async def test_validate_decision_events_accepts_valid_event(self):
        """_validate_decision_events accepts event that exists in Registry."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = [MagicMock(event_name="search.requested")]
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="s",
            next_action=PublishAction(
                event_type="search.requested",
                reasoning="test",
            ),
            reasoning="test",
        )
        
        # Should not raise
        await planner._validate_decision_events(decision, mock_events)
    
    @pytest.mark.asyncio
    async def test_validate_decision_events_rejects_hallucinated_event(self):
        """_validate_decision_events raises ValueError for non-existent event."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = [MagicMock(event_name="real.event")]
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="s",
            next_action=PublishAction(
                event_type="hallucinated.event",  # Not in Registry
                reasoning="test",
            ),
            reasoning="test",
        )
        
        with pytest.raises(ValueError, match="not found in Registry"):
            await planner._validate_decision_events(decision, mock_events)
    
    @pytest.mark.asyncio
    async def test_validate_decision_events_allows_non_publish_actions(self):
        """_validate_decision_events doesn't validate non-PUBLISH actions."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        mock_events = []
        
        # COMPLETE action (no event validation needed)
        decision = PlannerDecision(
            plan_id="p1",
            current_state="s",
            next_action=CompleteAction(
                result={"done": True},
                reasoning="test",
            ),
            reasoning="test",
        )
        
        # Should not raise even with empty events
        await planner._validate_decision_events(decision, mock_events)


class TestChoreographyPlannerExecution:
    """Tests for decision execution."""
    
    @pytest.mark.asyncio
    async def test_execute_decision_publish_without_response_event(self):
        """execute_decision publishes event when response_event is not set."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.bus.publish = AsyncMock()
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="s",
            next_action=PublishAction(
                event_type="search.requested",
                data={"query": "ai"},
                reasoning="test",
            ),
            reasoning="test",
        )
        
        await planner.execute_decision(decision, context)
        
        # Verify publish called
        context.bus.publish.assert_called_once()
        call_args = context.bus.publish.call_args
        assert call_args.kwargs["event_type"] == "search.requested"
        assert call_args.kwargs["data"]["query"] == "ai"
        assert "action_id" in call_args.kwargs["data"]  # Unique per-action ID injected for tracker

    @pytest.mark.asyncio
    async def test_execute_decision_publish_with_response_event(self):
        """execute_decision uses request when response_event is provided."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")

        context = MagicMock()
        context.bus.request = AsyncMock()

        goal_event = MagicMock()
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        goal_event.session_id = "session-1"

        decision = PlannerDecision(
            plan_id="p1",
            current_state="s",
            next_action=PublishAction(
                event_type="search.requested",
                data={"query": "ai"},
                response_event="search.completed",
                correlation_id="task-1",
                reasoning="test",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=goal_event)

        context.bus.request.assert_called_once()
        call_args = context.bus.request.call_args
        assert call_args.kwargs["event_type"] == "search.requested"
        assert call_args.kwargs["response_event"] == "search.completed"
        assert call_args.kwargs["correlation_id"] == "task-1"
        assert call_args.kwargs["tenant_id"] == "tenant-1"
        assert call_args.kwargs["user_id"] == "user-1"
        assert call_args.kwargs["session_id"] == "session-1"
        assert call_args.kwargs["data"]["task_id"] == "task-1"
    
    @pytest.mark.asyncio
    async def test_execute_decision_complete(self):
        """execute_decision sends response for COMPLETE action."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.bus.respond = AsyncMock()
        
        # Mock goal event
        goal_event = MagicMock()
        goal_event.response_event = "research.completed"
        goal_event.correlation_id = "corr-123"
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        goal_event.session_id = "session-1"
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="done",
            next_action=CompleteAction(
                result={"summary": "Research done"},
                reasoning="test",
            ),
            reasoning="test",
        )
        
        await planner.execute_decision(decision, context, goal_event=goal_event)
        
        # Verify respond called
        context.bus.respond.assert_called_once()
        call_args = context.bus.respond.call_args
        assert call_args.kwargs["event_type"] == "research.completed"
        assert call_args.kwargs["correlation_id"] == "corr-123"
        assert call_args.kwargs["data"] == {"summary": "Research done"}
        assert call_args.kwargs["tenant_id"] == "tenant-1"
        assert call_args.kwargs["user_id"] == "user-1"
        assert call_args.kwargs["session_id"] == "session-1"
    
    @pytest.mark.asyncio
    async def test_execute_decision_wait_pauses_plan(self):
        """execute_decision pauses plan for WAIT action."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.bus.publish = AsyncMock()
        
        # Mock plan
        plan = MagicMock()
        plan.plan_id = "plan-123"
        plan.correlation_id = "corr-123"
        plan.results = {}
        plan.pause = AsyncMock()
        plan.save = AsyncMock()
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="waiting",
            next_action=WaitAction(
                reason="Need approval",
                expected_event="approval.granted",
            ),
            reasoning="test",
        )
        
        await planner.execute_decision(decision, context, plan=plan)
        
        # Verify pause called
        plan.pause.assert_called_once()
        assert plan.results["_waiting_for"] == "approval.granted"
        plan.save.assert_called_once()
        
        # Verify notification published
        context.bus.publish.assert_called_once()
        call_args = context.bus.publish.call_args
        assert call_args.kwargs["event_type"] == "plan.waiting_for_input"
    
    @pytest.mark.asyncio
    async def test_execute_decision_wait_requires_plan(self):
        """execute_decision raises ValueError if WAIT action without plan."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="waiting",
            next_action=WaitAction(
                reason="Need approval",
                expected_event="approval.granted",
            ),
            reasoning="test",
        )
        
        with pytest.raises(ValueError, match="WAIT action requires PlanContext"):
            await planner.execute_decision(decision, context, plan=None)
    
    @pytest.mark.asyncio
    async def test_execute_decision_delegate(self):
        """execute_decision publishes goal event for DELEGATE action."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.bus.publish = AsyncMock()
        
        decision = PlannerDecision(
            plan_id="p1",
            current_state="delegate",
            next_action=DelegateAction(
                target_planner="specialist",
                goal_event="analysis.goal",
                goal_data={"dataset": "sales"},
                reasoning="test",
            ),
            reasoning="test",
        )
        
        await planner.execute_decision(decision, context)
        
        # Verify publish called
        context.bus.publish.assert_called_once()
        call_args = context.bus.publish.call_args
        assert call_args.kwargs["event_type"] == "analysis.goal"
        assert call_args.kwargs["data"] == {"dataset": "sales"}
    
    @pytest.mark.asyncio
    async def test_execute_decision_from_json_deserialization(self):
        """execute_decision works with JSON-deserialized decisions (LLM path)."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.bus.publish = AsyncMock()
        
        # Simulate LLM returning JSON string (real production path)
        json_decision = '''{
            "plan_id": "p1",
            "current_state": "searching",
            "next_action": {
                "action": "publish",
                "event_type": "search.requested",
                "data": {"query": "test"},
                "reasoning": "Need to search"
            },
            "reasoning": "Starting search",
            "confidence": 0.9
        }'''
        
        # Deserialize from JSON (this is what happens with LLM output)
        decision = PlannerDecision.model_validate_json(json_decision)
        
        # Should not crash with AttributeError on .value
        await planner.execute_decision(decision, context)
        
        # Verify it executed correctly
        context.bus.publish.assert_called_once()
        call_args = context.bus.publish.call_args
        assert call_args.kwargs["event_type"] == "search.requested"

    @pytest.mark.asyncio
    async def test_execute_decision_plan_id_overridden_by_plan_context(self):
        """execute_decision uses plan.plan_id (UUID) NOT decision.plan_id (LLM string).

        The LLM may return any string as plan_id (e.g. 'feedback-analysis-001').
        PlanContext.plan_id is the canonical UUID that the tracker client uses to
        look up progress. Both must agree or get_plan_progress() returns 404.
        """
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")

        context = MagicMock()
        context.bus.request = AsyncMock()

        goal_event = MagicMock()
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        goal_event.session_id = "session-1"

        # LLM hallucinates a semantic name
        decision = PlannerDecision(
            plan_id="feedback-analysis-001",  # LLM-generated string
            current_state="s",
            next_action=PublishAction(
                event_type="search.requested",
                data={"query": "ai"},
                response_event="search.completed",
                correlation_id="task-1",
                reasoning="test",
            ),
            reasoning="test",
        )

        # PlanContext carries the authoritative UUID
        plan = MagicMock()
        plan.plan_id = "41339b18-3200-4292-bb5e-121cef1205c4"

        await planner.execute_decision(decision, context, goal_event=goal_event, plan=plan)

        context.bus.request.assert_called_once()
        call_args = context.bus.request.call_args
        # Must use the PlanContext UUID, NOT the LLM string
        assert call_args.kwargs["plan_id"] == "41339b18-3200-4292-bb5e-121cef1205c4"


class TestChoreographyPlannerCircuitBreaker:
    """Tests for circuit breaker (max_actions limit)."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_enforces_max_actions(self):
        """reason_next_action raises RuntimeError when max_actions exceeded."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            max_actions=3,  # Low limit for testing
        )
        
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(
            return_value=[MagicMock(event_name="complete.action", description="Complete")]
        )
        
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"plan_id":"p1","current_state":"s","next_action":{"action":"complete","result":{},"reasoning":"done"},"reasoning":"test","confidence":1.0}'
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        # Call 3 times (within limit)
        for i in range(3):
            await planner.reason_next_action("trigger", context, plan_id="plan-1")
        
        # 4th call should trigger circuit breaker
        with pytest.raises(RuntimeError, match="Circuit breaker"):
            await planner.reason_next_action("trigger", context, plan_id="plan-1")


class TestChoreographyPlannerBYOModel:
    """Tests for BYO (Bring Your Own) model credentials."""
    
    def test_byo_model_accepts_api_key(self):
        """ChoreographyPlanner accepts explicit API key."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            api_key="sk-test-key",
        )
        
        assert planner.api_key == "sk-test-key"
    
    def test_byo_model_accepts_api_base(self):
        """ChoreographyPlanner accepts custom API base URL."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="azure/gpt-4",
            api_base="https://my-azure.openai.azure.com",
        )
        
        assert planner.api_base == "https://my-azure.openai.azure.com"
    
    def test_byo_model_accepts_llm_kwargs(self):
        """ChoreographyPlanner accepts additional LiteLLM kwargs."""
        planner = ChoreographyPlanner(
            name="test",
            reasoning_model="gpt-4o",
            max_tokens=1000,
            top_p=0.9,
        )
        
        assert planner.llm_kwargs["max_tokens"] == 1000
        assert planner.llm_kwargs["top_p"] == 0.9


class TestChoreographyPlannerImportError:
    """Tests for litellm import error handling."""
    
    @pytest.mark.asyncio
    async def test_reason_next_action_raises_import_error_without_litellm(self):
        """reason_next_action raises ImportError if litellm not installed."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        
        # Simulate litellm not installed by patching builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == 'litellm':
                raise ImportError("No module named 'litellm'")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            with pytest.raises(ImportError, match="litellm is required"):
                await planner.reason_next_action("trigger", context)


class TestChoreographyPlannerCorrelationId:
    """Tests for correlation_id propagation in choreography (regression for plan restoration bug)."""
    
    def test_resolve_publish_metadata_uses_plan_correlation_id(self):
        """_resolve_publish_metadata prioritizes plan.correlation_id over action.correlation_id."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        # Mock action with LLM-suggested correlation_id
        action = PublishAction(
            action="publish",
            event_type="data.fetch.requested",
            data={"product": "Widget"},
            response_event="data.fetched",
            correlation_id="fetch-001",  # LLM suggestion
            reasoning="Fetch product data",
        )
        
        # Mock plan with actual plan correlation_id
        plan = MagicMock()
        plan.correlation_id = "plan-abc-123"  # Actual plan ID
        
        # Mock goal event for tenant/user context
        goal_event = MagicMock()
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        
        metadata = planner._resolve_publish_metadata(action, goal_event, plan)
        
        # Should use plan's correlation_id, NOT action's
        assert metadata["correlation_id"] == "plan-abc-123"
        assert metadata["response_event"] == "data.fetched"
    
    def test_resolve_publish_metadata_falls_back_to_action_correlation_id(self):
        """_resolve_publish_metadata uses action.correlation_id when no plan provided."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        action = PublishAction(
            action="publish",
            event_type="data.fetch.requested",
            data={"product": "Widget"},
            response_event="data.fetched",
            correlation_id="fetch-001",
            reasoning="Fetch data",
        )
        
        goal_event = None
        plan = None  # No plan context
        
        metadata = planner._resolve_publish_metadata(action, goal_event, plan)
        
        # Should fall back to action's correlation_id
        assert metadata["correlation_id"] == "fetch-001"
    
    def test_resolve_publish_metadata_with_none_plan(self):
        """_resolve_publish_metadata uses action.correlation_id when plan is None."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        action = PublishAction(
            action="publish",
            event_type="task.requested",
            correlation_id="action-123",
            reasoning="Execute task",
        )
        
        # No plan provided
        plan = None
        
        metadata = planner._resolve_publish_metadata(action, None, plan)
        
        # Should use action's correlation_id
        assert metadata["correlation_id"] == "action-123"
    
    @pytest.mark.asyncio
    async def test_execute_decision_passes_plan_to_metadata_resolver(self):
        """execute_decision passes plan to _resolve_publish_metadata for correlation tracking."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="executing",
            reasoning="Test execution",
            confidence=0.9,
            next_action=PublishAction(
                action="publish",
                event_type="worker.requested",
                data={"foo": "bar"},
                response_event="worker.completed",
                correlation_id="task-abc",
                reasoning="Request worker execution",
            ),
        )
        
        # Mock context
        context = MagicMock()
        context.bus = MagicMock()
        context.bus.request = AsyncMock()
        
        # Mock plan
        plan = MagicMock()
        plan.correlation_id = "plan-real-id"
        
        # Mock goal event
        goal_event = MagicMock()
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        
        # Execute decision with plan
        await planner.execute_decision(decision, context, goal_event=goal_event, plan=plan)
        
        # Verify bus.request was called with plan's correlation_id
        context.bus.request.assert_called_once()
        call_kwargs = context.bus.request.call_args.kwargs
        assert call_kwargs["correlation_id"] == "plan-real-id", \
            "Should use plan correlation_id for worker request tracking"


class TestChoreographyPlannerCompleteAction:
    """Tests for COMPLETE action metadata fallback (transition scenarios)."""
    
    @pytest.mark.asyncio
    async def test_complete_uses_goal_event_metadata(self):
        """COMPLETE uses goal_event metadata when available."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="completed",
            reasoning="Analysis complete",
            confidence=1.0,
            next_action=CompleteAction(
                action="complete",
                result={"status": "done", "summary": "Analysis finished"},
                reasoning="All steps completed",
            ),
        )
        
        # Mock context with bus.respond
        context = MagicMock()
        context.bus = MagicMock()
        context.bus.respond = AsyncMock()
        
        # Mock goal event (original client request)
        goal_event = MagicMock()
        goal_event.response_event = "feedback.report.ready"
        goal_event.correlation_id = "client-123"
        goal_event.tenant_id = "tenant-1"
        goal_event.user_id = "user-1"
        goal_event.session_id = "session-1"
        
        # Execute COMPLETE
        await planner.execute_decision(decision, context, goal_event=goal_event, plan=None)
        
        # Verify response sent with goal_event metadata
        context.bus.respond.assert_called_once()
        call_kwargs = context.bus.respond.call_args.kwargs
        assert call_kwargs["event_type"] == "feedback.report.ready"
        assert call_kwargs["correlation_id"] == "client-123"
        assert call_kwargs["tenant_id"] == "tenant-1"
        assert call_kwargs["user_id"] == "user-1"
    
    @pytest.mark.asyncio
    async def test_complete_falls_back_to_plan_metadata_in_transition(self):
        """COMPLETE falls back to plan metadata when goal_event is a worker response."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="completed",
            reasoning="All workers done",
            confidence=1.0,
            next_action=CompleteAction(
                action="complete",
                result={"report": "Final analysis"},
                reasoning="Workflow complete",
            ),
        )
        
        # Mock context
        context = MagicMock()
        context.bus = MagicMock()
        context.bus.respond = AsyncMock()
        
        # Mock plan with original goal metadata
        plan = MagicMock()
        plan.response_event = "analyze.feedback.completed"
        plan.correlation_id = "plan-goal-123"
        plan.tenant_id = "tenant-1"
        plan.user_id = "user-1"
        plan.session_id = "session-1"
        plan.save = AsyncMock()  # COMPLETE action calls save()
        
        # Mock goal_event as worker response (has no response_event)
        goal_event = MagicMock()
        goal_event.type = "report.ready"
        goal_event.response_event = None  # Worker response, not client request
        goal_event.correlation_id = None  # getattr will return None
        goal_event.tenant_id = None
        goal_event.user_id = None
        goal_event.session_id = None
        
        # Execute COMPLETE from transition
        await planner.execute_decision(decision, context, goal_event=goal_event, plan=plan)
        
        # Verify response sent with PLAN metadata (fallback)
        context.bus.respond.assert_called_once()
        call_kwargs = context.bus.respond.call_args.kwargs
        assert call_kwargs["event_type"] == "analyze.feedback.completed", \
            "Should use plan.response_event for final response"
        assert call_kwargs["correlation_id"] == "plan-goal-123", \
            "Should use plan.correlation_id to route response back to client"
        assert call_kwargs["tenant_id"] == "tenant-1"
        assert call_kwargs["user_id"] == "user-1"
    
    @pytest.mark.asyncio
    async def test_complete_prefers_goal_event_over_plan(self):
        """COMPLETE prefers goal_event metadata over plan metadata."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="completed",
            reasoning="Done",
            confidence=1.0,
            next_action=CompleteAction(
                action="complete",
                result={"result": "final"},
                reasoning="Complete",
            ),
        )
        
        context = MagicMock()
        context.bus = MagicMock()
        context.bus.respond = AsyncMock()
        
        # Create plan with one set of metadata
        plan = MagicMock()
        plan.response_event = "plan.response"
        plan.correlation_id = "plan-id"
        plan.tenant_id = "plan-tenant"
        plan.user_id = "plan-user"
        plan.save = AsyncMock()  # COMPLETE action calls save()
        
        # Create goal_event with different metadata (should take precedence)
        goal_event = MagicMock()
        goal_event.response_event = "goal.response"
        goal_event.correlation_id = "goal-id"
        goal_event.tenant_id = "goal-tenant"
        goal_event.user_id = "goal-user"
        goal_event.session_id = "goal-session"
        
        # Execute
        await planner.execute_decision(decision, context, goal_event=goal_event, plan=plan)
        
        # Verify GOAL_EVENT metadata was used, not plan
        call_kwargs = context.bus.respond.call_args.kwargs
        assert call_kwargs["event_type"] == "goal.response", \
            "Should prefer goal_event.response_event"
        assert call_kwargs["correlation_id"] == "goal-id", \
            "Should prefer goal_event.correlation_id"
        assert call_kwargs["tenant_id"] == "goal-tenant"
        assert call_kwargs["user_id"] == "goal-user"
    
    @pytest.mark.asyncio
    async def test_complete_updates_plan_status_to_completed(self):
        """COMPLETE action sets plan.status = 'completed' and persists it."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="final",
            reasoning="Workflow complete",
            confidence=1.0,
            next_action=CompleteAction(
                action="complete",
                result={"output": "done"},
                reasoning="All steps finished",
            ),
        )
        
        context = MagicMock()
        context.bus = MagicMock()
        context.bus.respond = AsyncMock()
        
        # Create plan mock with save() method
        plan = MagicMock()
        plan.response_event = "workflow.completed"
        plan.correlation_id = "corr-123"
        plan.tenant_id = "tenant-1"
        plan.user_id = "user-1"
        plan.status = "running"  # Initially running
        plan.save = AsyncMock()
        
        # Execute COMPLETE action
        await planner.execute_decision(decision, context, plan=plan)
        
        # Verify plan status was set to "completed"
        assert plan.status == "completed", \
            "Plan status should be set to 'completed' to prevent infinite loop"
        
        # Verify plan was saved to persist status change
        plan.save.assert_called_once(), \
            "Plan must be saved to persist completed status"
        
        # Verify response was still sent
        context.bus.respond.assert_called_once()


class TestPlanContextCompleteStatus:
    """Tests for PlanContext.is_complete() method (prevents infinite loops)."""
    
    def test_is_complete_returns_true_for_completed_status(self):
        """PlanContext.is_complete() returns True when status='completed'."""
        from soorma_common.state import StateConfig
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="completed",
            state_machine={},
            current_state="any",
            results={},
        )
        
        assert plan.is_complete() is True
    
    def test_is_complete_returns_true_for_failed_status(self):
        """PlanContext.is_complete() returns True when status='failed'."""
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="failed",
            state_machine={},
            current_state="any",
            results={},
        )
        
        assert plan.is_complete() is True
    
    def test_is_complete_returns_false_for_pending_status(self):
        """PlanContext.is_complete() returns False when status='pending'."""
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="pending",
            state_machine={},
            current_state="any",
            results={},
        )
        
        assert plan.is_complete() is False
    
    def test_is_complete_returns_false_for_running_status(self):
        """PlanContext.is_complete() returns False when status='running'."""
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="running",
            state_machine={},
            current_state="any",
            results={},
        )
        
        assert plan.is_complete() is False
    
    def test_is_complete_returns_false_for_paused_status(self):
        """PlanContext.is_complete() returns False when status='paused'."""
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="paused",
            state_machine={},
            current_state="any",
            results={},
        )
        
        assert plan.is_complete() is False
    
    def test_is_complete_returns_true_for_terminal_state(self):
        """PlanContext.is_complete() returns True when state machine state is terminal."""
        from soorma_common.state import StateConfig
        
        plan = PlanContext(
            plan_id="plan-123",
            goal_event="goal",
            goal_data={},
            response_event="response",
            status="running",  # Status still running
            state_machine={
                "done": StateConfig(
                    state_name="done",
                    description="Terminal state",
                    is_terminal=True,
                )
            },
            current_state="done",  # But state is terminal
            results={},
        )
        
        assert plan.is_complete() is True, "State machine terminal flag should make plan complete"


class TestExecuteDecisionEnvelopeMetadata:
    """Tests that plan_id and goal_id are propagated as envelope metadata in all action types.
    
    These tests guard against regressions where workflow correlation fields (plan_id, goal_id)
    are dropped from event envelopes, breaking Tracker Service observability and goal tracing.
    """

    def _make_goal_event(self) -> MagicMock:
        """Create a fully-populated goal event mock."""
        goal = MagicMock()
        goal.tenant_id = "tenant-1"
        goal.user_id = "user-1"
        goal.session_id = "session-1"
        goal.goal_id = "goal-abc"
        goal.response_event = "workflow.completed"
        goal.correlation_id = "corr-123"
        return goal

    @pytest.mark.asyncio
    async def test_publish_request_propagates_plan_id_and_goal_id(self):
        """PUBLISH with response_event passes plan_id and goal_id in envelope."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.request = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="s",
            next_action=PublishAction(
                event_type="data.fetch.requested",
                data={"product": "Widget"},
                response_event="data.fetched",
                correlation_id="task-1",
                reasoning="fetch data",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=self._make_goal_event())

        context.bus.request.assert_called_once()
        kwargs = context.bus.request.call_args.kwargs
        assert kwargs["plan_id"] == "plan-xyz", "plan_id must be in envelope for Tracker"
        assert kwargs["goal_id"] == "goal-abc", "goal_id must be in envelope for tracing"

    @pytest.mark.asyncio
    async def test_publish_fire_and_forget_propagates_plan_id_and_goal_id(self):
        """PUBLISH without response_event (fire-and-forget) passes plan_id and goal_id."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.publish = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="s",
            next_action=PublishAction(
                event_type="notification.sent",
                data={"msg": "done"},
                reasoning="notify",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=self._make_goal_event())

        context.bus.publish.assert_called_once()
        kwargs = context.bus.publish.call_args.kwargs
        assert kwargs["plan_id"] == "plan-xyz", "plan_id must be in fire-and-forget envelope"
        assert kwargs["goal_id"] == "goal-abc", "goal_id must be in fire-and-forget envelope"

    @pytest.mark.asyncio
    async def test_complete_propagates_plan_id_and_goal_id(self):
        """COMPLETE action passes plan_id and goal_id in respond() envelope."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.respond = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="done",
            next_action=CompleteAction(
                result={"summary": "done"},
                reasoning="complete",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=self._make_goal_event())

        context.bus.respond.assert_called_once()
        kwargs = context.bus.respond.call_args.kwargs
        assert kwargs["plan_id"] == "plan-xyz", "plan_id must be in COMPLETE envelope for Tracker"
        assert kwargs["goal_id"] == "goal-abc", "goal_id must be in COMPLETE envelope for tracing"

    @pytest.mark.asyncio
    async def test_wait_propagates_tenant_and_plan_metadata(self):
        """WAIT action system event carries tenant_id, user_id, session_id, and plan_id."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.publish = AsyncMock()

        plan = MagicMock()
        plan.plan_id = "plan-xyz"
        plan.correlation_id = "corr-1"
        plan.tenant_id = "tenant-1"
        plan.user_id = "user-1"
        plan.session_id = "session-1"
        plan.results = {}
        plan.pause = AsyncMock()
        plan.save = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="waiting",
            next_action=WaitAction(
                reason="Need approval",
                expected_event="approval.granted",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, plan=plan)

        context.bus.publish.assert_called_once()
        kwargs = context.bus.publish.call_args.kwargs
        assert kwargs["plan_id"] == "plan-xyz", "system event must carry plan_id"
        assert kwargs["tenant_id"] == "tenant-1", "system event must carry tenant_id"
        assert kwargs["user_id"] == "user-1", "system event must carry user_id"
        assert kwargs["session_id"] == "session-1", "system event must carry session_id"

    @pytest.mark.asyncio
    async def test_delegate_propagates_all_metadata(self):
        """DELEGATE action carries tenant, user, session, goal_id, and plan_id."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.publish = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="delegating",
            next_action=DelegateAction(
                target_planner="specialist",
                goal_event="analysis.goal",
                goal_data={"dataset": "sales"},
                reasoning="delegate to specialist",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=self._make_goal_event())

        context.bus.publish.assert_called_once()
        kwargs = context.bus.publish.call_args.kwargs
        assert kwargs["plan_id"] == "plan-xyz", "DELEGATE must carry plan_id"
        assert kwargs["goal_id"] == "goal-abc", "DELEGATE must carry goal_id"
        assert kwargs["tenant_id"] == "tenant-1", "DELEGATE must carry tenant_id"
        assert kwargs["user_id"] == "user-1", "DELEGATE must carry user_id"
        assert kwargs["session_id"] == "session-1", "DELEGATE must carry session_id"

    @pytest.mark.asyncio
    async def test_plan_id_not_in_data_payload(self):
        """plan_id must be in envelope metadata, NOT in event data payload."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")
        context = MagicMock()
        context.bus.request = AsyncMock()

        decision = PlannerDecision(
            plan_id="plan-xyz",
            current_state="s",
            next_action=PublishAction(
                event_type="data.fetch.requested",
                data={"product": "Widget"},
                response_event="data.fetched",
                correlation_id="task-1",
                reasoning="test",
            ),
            reasoning="test",
        )

        await planner.execute_decision(decision, context, goal_event=self._make_goal_event())

        kwargs = context.bus.request.call_args.kwargs
        # plan_id should be envelope kwarg, not smuggled into data dict
        assert "plan_id" not in kwargs["data"], \
            "plan_id must be envelope metadata, not data payload"

    def test_resolve_publish_metadata_extracts_goal_id(self):
        """_resolve_publish_metadata extracts goal_id from goal_event."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")

        action = PublishAction(
            event_type="task.requested",
            reasoning="test",
        )
        goal_event = MagicMock()
        goal_event.tenant_id = "t1"
        goal_event.user_id = "u1"
        goal_event.session_id = "s1"
        goal_event.goal_id = "goal-999"

        metadata = planner._resolve_publish_metadata(action, goal_event, plan=None)

        assert metadata["goal_id"] == "goal-999"

    def test_resolve_publish_metadata_goal_id_none_when_no_goal_event(self):
        """_resolve_publish_metadata returns None goal_id when no goal_event."""
        planner = ChoreographyPlanner(name="test", reasoning_model="gpt-4o")

        action = PublishAction(event_type="task.requested", reasoning="test")

        metadata = planner._resolve_publish_metadata(action, goal_event=None, plan=None)

        assert metadata["goal_id"] is None
