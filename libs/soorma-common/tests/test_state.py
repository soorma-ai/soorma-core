"""Tests for state machine DTOs."""

import pytest
from soorma_common.state import (
    StateAction,
    StateTransition,
    StateConfig,
    PlanDefinition,
    PlanRegistrationRequest,
    PlanInstanceRequest,
)


def test_state_action():
    """Test StateAction validation."""
    action = StateAction(
        event_type="web.search.requested",
        response_event="web.search.completed",
        data={"query": "AI trends"},
    )
    
    assert action.event_type == "web.search.requested"
    assert action.response_event == "web.search.completed"
    assert action.data == {"query": "AI trends"}


def test_state_transition():
    """Test StateTransition validation."""
    transition = StateTransition(
        on_event="web.search.completed",
        to_state="analyze",
        condition="data.results.count > 0",
    )
    
    assert transition.on_event == "web.search.completed"
    assert transition.to_state == "analyze"
    assert transition.condition == "data.results.count > 0"


def test_state_config():
    """Test StateConfig validation."""
    state = StateConfig(
        state_name="search",
        description="Search the web",
        action=StateAction(
            event_type="web.search.requested",
            response_event="web.search.completed",
        ),
        transitions=[
            StateTransition(
                on_event="web.search.completed",
                to_state="analyze",
            )
        ],
        is_terminal=False,
    )
    
    assert state.state_name == "search"
    assert state.action.event_type == "web.search.requested"
    assert len(state.transitions) == 1
    assert not state.is_terminal


def test_state_config_terminal():
    """Test StateConfig with terminal state."""
    state = StateConfig(
        state_name="done",
        description="Plan completed",
        is_terminal=True,
    )
    
    assert state.state_name == "done"
    assert state.is_terminal
    assert state.action is None


def test_plan_definition():
    """Test PlanDefinition validation."""
    plan_def = PlanDefinition(
        plan_type="research.plan",
        description="Research plan",
        initial_state="start",
        states={
            "start": StateConfig(
                state_name="start",
                description="Start state",
                action=StateAction(
                    event_type="research.started",
                    response_event="research.initialized",
                ),
                transitions=[
                    StateTransition(on_event="research.initialized", to_state="search")
                ],
            ),
            "search": StateConfig(
                state_name="search",
                description="Search state",
                is_terminal=True,
            ),
        },
    )
    
    assert plan_def.plan_type == "research.plan"
    assert plan_def.initial_state == "start"
    assert len(plan_def.states) == 2
    assert "start" in plan_def.states
    assert "search" in plan_def.states


def test_plan_registration_request():
    """Test PlanRegistrationRequest validation."""
    plan_def = PlanDefinition(
        plan_type="test.plan",
        description="Test plan",
        states={
            "start": StateConfig(
                state_name="start",
                description="Start",
                is_terminal=True,
            )
        },
    )
    
    request = PlanRegistrationRequest(plan=plan_def)
    
    assert request.plan.plan_type == "test.plan"


def test_plan_instance_request():
    """Test PlanInstanceRequest validation."""
    request = PlanInstanceRequest(
        plan_type="research.plan",
        goal_data={"topic": "AI trends"},
        session_id="sess-123",
        parent_plan_id="plan-456",
    )
    
    assert request.plan_type == "research.plan"
    assert request.goal_data == {"topic": "AI trends"}
    assert request.session_id == "sess-123"
    assert request.parent_plan_id == "plan-456"
