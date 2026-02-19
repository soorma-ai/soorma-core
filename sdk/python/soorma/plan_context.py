"""
Plan Context - State machine container for Planner orchestration.

PlanContext manages the lifecycle of a plan execution:
- Creation from goal events
- State persistence via Memory Service  
- Event-driven state transitions
- Task execution based on state actions
- Completion with response publication

Usage:
    @planner.on_goal("research.goal")
    async def plan_research(goal: GoalContext, context: PlatformContext):
        # Define state machine
        state_machine = {
            "start": StateConfig(
                state_name="start",
                description="Initial state",
                default_next="search",
            ),
            "search": StateConfig(
                state_name="search",
                description="Search for papers",
                action=StateAction(
                    event_type="search.requested",
                    response_event="search.completed",
                    data={"query": "{{goal_data.topic}}"},
                ),
                transitions=[
                    StateTransition(on_event="search.completed", to_state="done")
                ],
            ),
            "done": StateConfig(
                state_name="done",
                description="Plan completed",
                is_terminal=True,
            ),
        }
        
        # Create and execute plan
        plan = PlanContext(
            plan_id=goal.correlation_id,
            goal_event=goal.event_type,
            goal_data=goal.data,
            response_event=goal.response_event,
            status="pending",
            state_machine=state_machine,
            current_state="start",
            results={},
            session_id=goal.session_id,
            user_id=goal.user_id,
            tenant_id=goal.tenant_id,
            _context=context,
        )
        await plan.save()
        await plan.execute_next()
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from soorma_common.state import StateConfig, StateAction, StateTransition

logger = logging.getLogger(__name__)

# Forward reference for PlatformContext (import at runtime to avoid circular dependency)
if TYPE_CHECKING:
    from .context import PlatformContext


@dataclass
class PlanContext:
    """
    State machine context for a plan execution.
    
    Manages plan lifecycle:
    - Creation from goal events
    - State persistence via Memory Service
    - Event-driven state transitions
    - Task execution based on state actions
    - Completion with response publication
    
    Attributes:
        plan_id: Unique plan identifier
        goal_event: Original goal event type
        goal_data: Goal parameters from the original request
        response_event: Event type for final result (from original request)
        correlation_id: Original goal's correlation ID for response routing
        status: Plan execution status (pending|running|completed|failed|paused)
        state_machine: State definitions (state_name -> StateConfig)
        current_state: Current state name in the state machine
        results: Aggregated results from completed steps
        parent_plan_id: Optional parent plan for nested workflows
        session_id: Optional session for conversation context
        user_id: User authentication context
        tenant_id: Tenant isolation
        _context: PlatformContext for service access (not persisted)
    """
    
    plan_id: str
    goal_event: str
    goal_data: Dict[str, Any]
    response_event: str
    status: str  # pending, running, completed, failed, paused
    state_machine: Dict[str, StateConfig]
    current_state: str
    results: Dict[str, Any]
    correlation_id: str = ""  # Original goal's correlation ID
    parent_plan_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str = ""
    tenant_id: str = ""
    _context: Optional['PlatformContext'] = field(default=None, repr=False)
    
    # Persistence methods (Day 2)
    
    async def save(self) -> None:
        """
        Persist plan context to Memory Service.
        
        Called after state transitions to ensure plan state is durable.
        Memory Service API handles upsert (insert or update).
        """
        if not self._context:
            raise ValueError("PlanContext._context is required for save()")
        
        # Serialize plan state
        state_dict = self.to_dict()
        
        # Store/update in Memory Service (API handles upsert)
        await self._context.memory.store_plan_context(
            plan_id=self.plan_id,
            session_id=self.session_id,
            goal_event=self.goal_event,
            goal_data=self.goal_data,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            response_event=self.response_event,
            state=state_dict,
            current_state=self.current_state,
            correlation_ids=[self.plan_id, self.correlation_id],  # Track both plan_id and original correlation
        )
    
    @classmethod
    async def restore(
        cls,
        plan_id: str,
        context: 'PlatformContext',
        tenant_id: str,
        user_id: str,
    ) -> Optional['PlanContext']:
        """
        Restore plan context from Memory Service by plan ID.
        
        Args:
            plan_id: Plan identifier
            context: PlatformContext for service access
            tenant_id: Tenant ID from event context
            user_id: User ID from event context
            
        Returns:
            PlanContext instance if found, None otherwise
        """
        # Get plan from Memory Service
        plan_data = await context.memory.get_plan_context(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if not plan_data:
            return None
        
        # Extract state from response (handle both dict and Pydantic model)
        if hasattr(plan_data, 'state'):
            # PlanContextResponse Pydantic model
            state = plan_data.state
        else:
            # Dict (for tests/backwards compatibility)
            state = plan_data.get("state", {})
        
        if not state:
            return None
        
        # Deserialize using from_dict
        return cls.from_dict(state, context)
    
    @classmethod
    async def restore_by_correlation(
        cls,
        correlation_id: str,
        context: 'PlatformContext',
        tenant_id: str,
        user_id: str,
    ) -> Optional['PlanContext']:
        """
        Restore plan context by correlation ID (for event routing).
        
        Args:
            correlation_id: Correlation identifier from incoming event
            context: PlatformContext for service access
            tenant_id: Tenant ID from event context
            user_id: User ID from event context
            
        Returns:
            PlanContext instance if found, None otherwise
        """
        # Get plan by correlation_id from Memory Service
        plan_data = await context.memory.get_plan_by_correlation(
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if not plan_data:
            return None
        
        # Extract state from response (handle both dict and Pydantic model)
        if hasattr(plan_data, 'state'):
            # PlanContextResponse Pydantic model
            state = plan_data.state
        else:
            # Dict (for tests/backwards compatibility)
            state = plan_data.get("state", {})
        
        if not state:
            return None
        
        # Deserialize using from_dict
        return cls.from_dict(state, context)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize plan context to dictionary.
        
        Returns:
            Dictionary representation for persistence
        """
        # Serialize state machine (StateConfig -> dict)
        state_machine_dict = {}
        for state_name, state_config in self.state_machine.items():
            # Use Pydantic's model_dump() method
            state_machine_dict[state_name] = state_config.model_dump()
        
        return {
            "plan_id": self.plan_id,
            "goal_event": self.goal_event,
            "goal_data": self.goal_data,
            "response_event": self.response_event,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "state_machine": state_machine_dict,
            "current_state": self.current_state,
            "results": self.results,
            "parent_plan_id": self.parent_plan_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], context: 'PlatformContext') -> 'PlanContext':
        """
        Deserialize plan context from dictionary.
        
        Args:
            data: Dictionary representation from Memory Service
            context: PlatformContext for service access
            
        Returns:
            PlanContext instance
        """
        # Deserialize state machine (dict -> StateConfig)
        state_machine_dict = data.get("state_machine", {})
        state_machine = {}
        for state_name, state_data in state_machine_dict.items():
            # Use Pydantic's model_validate() to create StateConfig from dict
            state_machine[state_name] = StateConfig.model_validate(state_data)
        
        return cls(
            plan_id=data["plan_id"],
            goal_event=data["goal_event"],
            goal_data=data["goal_data"],
            response_event=data["response_event"],
            correlation_id=data.get("correlation_id", ""),
            status=data["status"],
            state_machine=state_machine,
            current_state=data["current_state"],
            results=data["results"],
            parent_plan_id=data.get("parent_plan_id"),
            session_id=data.get("session_id"),
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            _context=context,
        )
    
    # State machine methods (Day 2-3)
    
    def get_next_state(self, event: Any) -> Optional[str]:
        """
        Determine next state based on incoming event.
        
        Args:
            event: EventEnvelope from transition
            
        Returns:
            Next state name if transition found, None otherwise
        """
        # Get current state configuration
        current_state_config = self.state_machine.get(self.current_state)
        if not current_state_config:
            return None
        
        # Check transitions for matching event
        if not current_state_config.transitions:
            return None
        
        # Get event type from event object
        event_type = event.type if hasattr(event, 'type') else str(event)
        
        # Find matching transition
        for transition in current_state_config.transitions:
            if transition.on_event == event_type:
                return transition.to_state
        
        return None
    
    async def execute_next(self, trigger_event: Optional[Any] = None) -> None:
        """
        Execute the next state action.
        
        Args:
            trigger_event: Optional event that triggered this transition
        """
        if not self._context:
            raise ValueError("PlanContext._context is required for execute_next()")
        
        # Determine next state
        if trigger_event:
            # Transition based on incoming event
            next_state_name = self.get_next_state(trigger_event)
            if not next_state_name:
                # No matching transition, no-op
                return
        else:
            # Initial execution: use default_next from current state
            current_config = self.state_machine.get(self.current_state)
            if not current_config or not current_config.default_next:
                return
            next_state_name = current_config.default_next
        
        # Get next state config
        next_state_config = self.state_machine.get(next_state_name)
        if not next_state_config:
            return
        
        # Update current state
        self.current_state = next_state_name
        self.status = "running"
        
        # Execute state action if present
        if next_state_config.action:
            action = next_state_config.action
            
            # Interpolate data with goal_data
            action_data = self._interpolate_data(action.data)
            
            # Publish action event using bus.request()
            await self._context.bus.request(
                event_type=action.event_type,
                data=action_data,
                response_event=action.response_event,
                correlation_id=self.plan_id,
            )
        
        # Save state
        await self.save()
    
    def is_complete(self) -> bool:
        """
        Check if plan has reached a terminal state.
        
        Returns:
            True if current state is terminal, False otherwise
        """
        current_config = self.state_machine.get(self.current_state)
        if not current_config:
            return False
        
        return current_config.is_terminal if current_config.is_terminal is not None else False
    
    async def finalize(self, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Complete the plan and publish final result.
        
        Args:
            result: Optional final result to include in response
        """
        if not self._context:
            raise ValueError("PlanContext._context is required for finalize()")
        
        # Update status
        self.status = "completed"
        
        # Publish final result using original correlation_id
        logger.info(f"📤 Publishing response: {self.response_event}")
        logger.info(f"   Correlation: {self.correlation_id}")
        logger.info(f"   Topic: action-results")
        logger.info(f"   Data: {result}")
        
        await self._context.bus.respond(
            event_type=self.response_event,
            data={
                "plan_id": self.plan_id,
                "result": result,
            },
            correlation_id=self.correlation_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            session_id=self.session_id,
        )
        
        logger.info("✅ Response published")
        
        # Save final state
        await self.save()
    
    async def pause(self, reason: str = "user_input_required") -> None:
        """
        Pause plan execution (HITL workflow).
        
        Args:
            reason: Reason for pausing
        """
        if not self._context:
            raise ValueError("PlanContext._context is required for pause()")
        
        # Update status
        self.status = "paused"
        
        # Save paused state
        await self.save()
    
    async def resume(self, input_data: Dict[str, Any]) -> None:
        """
        Resume paused plan execution.
        
        Args:
            input_data: User input or approval data
        """
        if not self._context:
            raise ValueError("PlanContext._context is required for resume()")
        
        # Update status
        self.status = "running"
        
        # Store user input in results
        self.results["user_input"] = input_data
        
        # Continue execution
        await self.execute_next()
    
    # Helper methods
    
    def _interpolate_data(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace {{goal_data.field}} placeholders with actual values.
        
        Args:
            template: Data template with placeholders
            
        Returns:
            Interpolated data dictionary
            
        Example:
            template: {"query": "{{goal_data.topic}}"}
            goal_data: {"topic": "AI agents"}
            result: {"query": "AI agents"}
        """
        import json
        import re
        
        # Convert to JSON string for easy replacement
        json_str = json.dumps(template)
        
        # Replace {{goal_data.field}} patterns
        for match in re.finditer(r'\{\{goal_data\.(\w+)\}\}', json_str):
            field = match.group(1)
            value = self.goal_data.get(field, "")
            json_str = json_str.replace(match.group(0), json.dumps(value)[1:-1] if isinstance(value, str) else str(value))
        
        return json.loads(json_str)

