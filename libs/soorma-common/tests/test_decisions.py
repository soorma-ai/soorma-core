"""Tests for decision types."""

import pytest
from soorma_common.decisions import (
    PlanAction,
    PublishAction,
    CompleteAction,
    WaitAction,
    DelegateAction,
    PlannerDecision,
)


def test_plan_action_enum_values():
    """Verify PlanAction enum has all required actions."""
    assert PlanAction.PUBLISH.value == "publish"
    assert PlanAction.COMPLETE.value == "complete"
    assert PlanAction.WAIT.value == "wait"
    assert PlanAction.DELEGATE.value == "delegate"


def test_publish_action_validation():
    """PublishAction requires event_type and reasoning."""
    action = PublishAction(
        event_type="search.requested",
        reasoning="Need to search for information",
    )
    
    assert action.action == PlanAction.PUBLISH
    assert action.event_type == "search.requested"
    assert action.topic == "action-requests"  # Default
    assert action.data == {}  # Default
    assert action.reasoning == "Need to search for information"


def test_publish_action_with_custom_topic():
    """PublishAction accepts custom topic."""
    action = PublishAction(
        event_type="search.requested",
        topic="custom-topic",
        data={"query": "AI agents"},
        reasoning="Custom search",
    )
    
    assert action.topic == "custom-topic"
    assert action.data == {"query": "AI agents"}


def test_complete_action_validation():
    """CompleteAction requires result and reasoning."""
    action = CompleteAction(
        result={"answer": "42"},
        reasoning="Goal achieved",
    )
    
    assert action.action == PlanAction.COMPLETE
    assert action.result == {"answer": "42"}
    assert action.reasoning == "Goal achieved"


def test_wait_action_validation():
    """WaitAction requires reason and expected_event."""
    action = WaitAction(
        reason="Need human approval",
        expected_event="approval.granted",
    )
    
    assert action.action == PlanAction.WAIT
    assert action.reason == "Need human approval"
    assert action.expected_event == "approval.granted"
    assert action.timeout_seconds == 3600  # Default 1 hour


def test_wait_action_custom_timeout():
    """WaitAction accepts custom timeout."""
    action = WaitAction(
        reason="Waiting for data",
        expected_event="data.uploaded",
        timeout_seconds=7200,  # 2 hours
    )
    
    assert action.timeout_seconds == 7200


def test_delegate_action_validation():
    """DelegateAction requires target_planner, goal_event, and reasoning."""
    action = DelegateAction(
        target_planner="research-specialist",
        goal_event="research.goal",
        goal_data={"topic": "quantum computing"},
        reasoning="Specialized knowledge required",
    )
    
    assert action.action == PlanAction.DELEGATE
    assert action.target_planner == "research-specialist"
    assert action.goal_event == "research.goal"
    assert action.goal_data == {"topic": "quantum computing"}
    assert action.reasoning == "Specialized knowledge required"


def test_planner_decision_with_publish_action():
    """PlannerDecision correctly handles PublishAction."""
    action = PublishAction(
        event_type="search.requested",
        reasoning="Need to search",
    )
    
    decision = PlannerDecision(
        plan_id="plan-123",
        current_state="search",
        next_action=action,
        reasoning="Starting search phase",
    )
    
    assert decision.plan_id == "plan-123"
    assert decision.current_state == "search"
    assert decision.next_action.action == PlanAction.PUBLISH
    assert decision.reasoning == "Starting search phase"
    assert decision.confidence == 1.0  # Default


def test_planner_decision_with_complete_action():
    """PlannerDecision correctly handles CompleteAction."""
    action = CompleteAction(
        result={"summary": "Research completed"},
        reasoning="All tasks done",
    )
    
    decision = PlannerDecision(
        plan_id="plan-456",
        current_state="done",
        next_action=action,
        reasoning="Goal achieved",
    )
    
    assert decision.next_action.action == PlanAction.COMPLETE
    assert isinstance(decision.next_action, CompleteAction)
    assert decision.next_action.result == {"summary": "Research completed"}


def test_planner_decision_with_wait_action():
    """PlannerDecision correctly handles WaitAction."""
    action = WaitAction(
        reason="Need approval",
        expected_event="approval.granted",
    )
    
    decision = PlannerDecision(
        plan_id="plan-789",
        current_state="waiting",
        next_action=action,
        reasoning="Requires human review",
    )
    
    assert decision.next_action.action == PlanAction.WAIT
    assert isinstance(decision.next_action, WaitAction)
    assert decision.next_action.expected_event == "approval.granted"


def test_planner_decision_with_delegate_action():
    """PlannerDecision correctly handles DelegateAction."""
    action = DelegateAction(
        target_planner="specialist",
        goal_event="analysis.goal",
        goal_data={"dataset": "sales-2024"},
        reasoning="Specialized analysis needed",
    )
    
    decision = PlannerDecision(
        plan_id="plan-abc",
        current_state="delegate",
        next_action=action,
        reasoning="Delegating to specialist",
    )
    
    assert decision.next_action.action == PlanAction.DELEGATE
    assert isinstance(decision.next_action, DelegateAction)
    assert decision.next_action.target_planner == "specialist"


def test_planner_decision_with_confidence():
    """PlannerDecision accepts confidence score."""
    action = PublishAction(
        event_type="search.requested",
        reasoning="Uncertain about search terms",
    )
    
    decision = PlannerDecision(
        plan_id="plan-123",
        current_state="search",
        next_action=action,
        confidence=0.75,
        reasoning="75% confident in this approach",
    )
    
    assert decision.confidence == 0.75


def test_planner_decision_confidence_bounds():
    """PlannerDecision confidence must be between 0 and 1."""
    action = PublishAction(
        event_type="test.event",
        reasoning="test",
    )
    
    # Valid: 0.0
    decision = PlannerDecision(
        plan_id="plan-1",
        current_state="test",
        next_action=action,
        confidence=0.0,
        reasoning="test",
    )
    assert decision.confidence == 0.0
    
    # Valid: 1.0
    decision = PlannerDecision(
        plan_id="plan-2",
        current_state="test",
        next_action=action,
        confidence=1.0,
        reasoning="test",
    )
    assert decision.confidence == 1.0
    
    # Invalid: >1.0 should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        PlannerDecision(
            plan_id="plan-3",
            current_state="test",
            next_action=action,
            confidence=1.5,
            reasoning="test",
        )
    
    # Invalid: <0.0 should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        PlannerDecision(
            plan_id="plan-4",
            current_state="test",
            next_action=action,
            confidence=-0.1,
            reasoning="test",
        )


def test_planner_decision_with_alternative_actions():
    """PlannerDecision can include alternative actions."""
    primary = PublishAction(
        event_type="search.requested",
        reasoning="Primary approach",
    )
    
    alt1 = CompleteAction(
        result={"note": "Using cached result"},
        reasoning="Alternative: use cache",
    )
    
    alt2 = DelegateAction(
        target_planner="expert",
        goal_event="expert.consult",
        goal_data={},
        reasoning="Alternative: ask expert",
    )
    
    decision = PlannerDecision(
        plan_id="plan-multi",
        current_state="decide",
        next_action=primary,
        alternative_actions=[alt1, alt2],
        reasoning="Chose search over cache or delegation",
    )
    
    assert len(decision.alternative_actions) == 2
    assert decision.alternative_actions[0].action == PlanAction.COMPLETE
    assert decision.alternative_actions[1].action == PlanAction.DELEGATE


def test_planner_decision_json_schema():
    """PlannerDecision generates valid JSON schema for LLM."""
    schema = PlannerDecision.model_json_schema()
    
    # Verify schema structure
    assert "properties" in schema
    assert "next_action" in schema["properties"]
    assert "plan_id" in schema["properties"]
    assert "current_state" in schema["properties"]
    assert "reasoning" in schema["properties"]
    
    # Verify required fields
    assert "required" in schema
    assert "plan_id" in schema["required"]
    assert "current_state" in schema["required"]
    assert "next_action" in schema["required"]
    assert "reasoning" in schema["required"]


def test_planner_decision_serialization():
    """PlannerDecision can be serialized to JSON."""
    action = PublishAction(
        event_type="search.requested",
        data={"query": "AI agents"},
        reasoning="Need search",
    )
    
    decision = PlannerDecision(
        plan_id="plan-serialize",
        current_state="search",
        next_action=action,
        reasoning="Test serialization",
    )
    
    # Serialize to dict
    data = decision.model_dump()
    
    assert data["plan_id"] == "plan-serialize"
    assert data["current_state"] == "search"
    assert data["next_action"]["action"] == "publish"
    assert data["next_action"]["event_type"] == "search.requested"
    
    # Deserialize from dict
    restored = PlannerDecision.model_validate(data)
    
    assert restored.plan_id == decision.plan_id
    assert restored.next_action.event_type == action.event_type
