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
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        
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
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        
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
    async def test_execute_decision_publish(self):
        """execute_decision publishes event for PUBLISH action."""
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
        assert call_args.kwargs["data"] == {"query": "ai"}
    
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
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        
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
