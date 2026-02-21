"""ChoreographyPlanner - Autonomous orchestration using LLM reasoning.

ChoreographyPlanner is a high-level Planner that uses LLMs to autonomously
decide what to do next based on plan context and available events.

This is a simplified wrapper above the base Planner - developers write minimal code
while the framework handles event discovery, validation, and execution.

Usage:
    from soorma.ai.choreography import ChoreographyPlanner
    
    planner = ChoreographyPlanner(
        name="research-advisor",
        reasoning_model="gpt-4o",  # BYO model, uses OPENAI_API_KEY env var
    )
    
    @planner.on_goal("research.goal")
    async def handle_goal(goal, context):
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine={},  # ChoreographyPlanner uses LLM, not state machine
            current_state="reasoning",
            status="running",
        )
        decision = await planner.reason_next_action(
            trigger=f"New goal: {goal.data['objective']}",
            context=context,
        )
        await planner.execute_decision(decision, context, goal_event=goal, plan=plan)

Performance & Cost Notes:
- LLM calls may have latency (0.5-5 seconds depending on provider)
- Cost varies by model and usage (OpenAI GPT-4: ~$0.01-0.10 per decision)
- Use BYO credentials to control costs
- Consider local models (ollama) for cost-sensitive applications
"""

import json
import logging
from typing import Any, Dict, List, Optional

from soorma.agents.planner import Planner
from soorma.context import PlatformContext
from soorma.plan_context import PlanContext
from soorma_common.decisions import (
    PlannerDecision,
    PlanAction,
    PublishAction,
    CompleteAction,
    WaitAction,
    DelegateAction,
)
from soorma_common.events import EventEnvelope

logger = logging.getLogger(__name__)


class ChoreographyPlanner(Planner):
    """Autonomous Planner that uses LLM reasoning for decision-making.
    
    Reduces boilerplate from ~400 lines (manual orchestration) to ~50 lines
    by automating:
    - Event discovery from Registry Service
    - LLM-based decision making
    - Event validation (prevent hallucinations)
    - Type-safe execution
    
    Attributes:
        reasoning_model: LLM model identifier (e.g., "gpt-4o", "claude-3-opus")
        api_key: Optional API key override (defaults to env var)
        api_base: Optional base URL for custom endpoints (e.g., Azure)
        temperature: Temperature for LLM generation (0-2)
        max_actions: Circuit breaker - max actions per plan (prevents runaway loops)
        system_instructions: Custom business logic/rules for LLM (optional)
        planning_strategy: Pre-configured strategy (balanced|conservative|aggressive)
        **llm_kwargs: Additional parameters passed to LiteLLM (e.g., max_tokens, top_p)
    
    Example:
        ```python
        # Simple usage with OpenAI (uses OPENAI_API_KEY env var)
        planner = ChoreographyPlanner(
            name="advisor",
            reasoning_model="gpt-4o",
        )
        
        # With custom business logic
        planner = ChoreographyPlanner(
            name="financial-advisor",
            reasoning_model="gpt-4o",
            system_instructions='''
                You are a financial planning agent for a regulated banking platform.
                CRITICAL RULES:
                - Transactions >$5,000 require human approval (use WAIT action)
                - Never auto-execute wire transfers (always DELEGATE to compliance-checker)
                - Prioritize security over speed
            ''',
            planning_strategy="conservative",
        )
        
        # With local model (no API key needed)
        planner = ChoreographyPlanner(
            name="advisor",
            reasoning_model="ollama/llama2",
        )
        ```
    """
    
    def __init__(
        self,
        name: str,
        reasoning_model: str = "gpt-4o",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        max_actions: int = 20,
        system_instructions: Optional[str] = None,
        planning_strategy: str = "balanced",
        **llm_kwargs: Any,
    ):
        """Initialize ChoreographyPlanner with LLM configuration.
        
        Args:
            name: Planner name
            reasoning_model: LLM model identifier (e.g., "gpt-4o", "claude-3-opus", "ollama/llama2")
            api_key: Optional API key (if None, uses provider's env var)
            api_base: Optional base URL for custom LLM endpoints
            temperature: LLM temperature (lower = deterministic, higher = creative)
            max_actions: Circuit breaker limit for actions per plan
            system_instructions: Custom business logic for the LLM (e.g., compliance rules, domain expertise)
            planning_strategy: Pre-configured strategy ("balanced"|"conservative"|"aggressive")
            **llm_kwargs: Additional LiteLLM parameters (max_tokens, top_p, etc.)
            
        Raises:
            ImportError: If litellm is not installed
            
        Examples:
            # Using environment variables (recommended)
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="gpt-4o",  # Uses OPENAI_API_KEY from env
            )
            
            # Explicit API key
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="gpt-4o",
                api_key="sk-...",  # Direct key, not recommended for production
            )
            
            # Azure OpenAI
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="azure/my-gpt4-deployment",
                api_base="https://my-resource.openai.azure.com",
                api_key=os.environ["AZURE_API_KEY"],
            )
            
            # Local Ollama (no API key needed)
            planner = ChoreographyPlanner(
                name="advisor",
                reasoning_model="ollama/llama2",
            )
            
            # Custom business logic
            planner = ChoreographyPlanner(
                name="financial-advisor",
                reasoning_model="gpt-4o",
                system_instructions='''
                    You are a financial planning agent for a regulated banking platform.
                    CRITICAL RULES:
                    - Transactions >$5,000 require human approval (use WAIT action)
                    - Never auto-execute wire transfers (always DELEGATE to compliance-checker)
                    - Prioritize security over speed
                ''',
                planning_strategy="conservative",
            )
        """
        super().__init__(
            name=name,
            description=f"Autonomous planner using {reasoning_model}",
        )
        
        self.reasoning_model = reasoning_model
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature
        self.max_actions = max_actions
        self.system_instructions = system_instructions
        self.planning_strategy = planning_strategy
        self.llm_kwargs = llm_kwargs
        
        # Will be lazily imported to avoid hard dependency
        self._litellm = None
        self._action_count: Dict[str, int] = {}  # plan_id -> action count
    
    async def reason_next_action(
        self,
        trigger: str,
        context: PlatformContext,
        plan_id: Optional[str] = None,
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> PlannerDecision:
        """Use LLM to decide the next action in the plan.
        
        This method:
        1. Discovers available events from Registry Service
        2. Builds a schema-based prompt
        3. Calls the configured LLM model
        4. Validates that referenced events exist
        5. Returns a type-safe PlannerDecision
        
        Args:
            trigger: What triggered this decision (e.g., "search.completed")
            context: PlatformContext for service access
            plan_id: Optional plan ID for decision tracking
            custom_context: Runtime-specific context for this decision (e.g., customer tier, inventory levels)
            
        Returns:
            PlannerDecision with next action to take
            
        Raises:
            ValueError: If referenced event doesn't exist in Registry
            ImportError: If litellm is not installed
            
        Examples:
            decision = await planner.reason_next_action(
                trigger="search.completed",
                context=context,
            )
            # Returns PlannerDecision with PUBLISH, COMPLETE, WAIT, or DELEGATE action
            
            # With custom runtime context
            decision = await planner.reason_next_action(
                trigger="order.received",
                context=context,
                custom_context={
                    "customer": {"tier": "premium", "region": "EU"},
                    "inventory": {"stock_level": "low"},
                },
            )
        """
        # Lazy import to avoid hard dependency
        if not self._litellm:
            try:
                import litellm
                self._litellm = litellm
            except ImportError as e:
                raise ImportError(
                    "litellm is required for ChoreographyPlanner. "
                    "Install with: pip install 'soorma-core[ai]' or pip install litellm"
                ) from e
        
        # Circuit breaker: prevent runaway loops
        if plan_id:
            if plan_id not in self._action_count:
                self._action_count[plan_id] = 0
            self._action_count[plan_id] += 1
            
            if self._action_count[plan_id] > self.max_actions:
                logger.error(
                    f"Circuit breaker triggered for plan {plan_id}: "
                    f"{self._action_count[plan_id]} > {self.max_actions} actions"
                )
                raise RuntimeError(
                    f"Circuit breaker: plan {plan_id} exceeded max_actions "
                    f"({self.max_actions}). Possible infinite loop detected."
                )
        
        # Discover available events from Registry
        events = await context.toolkit.discover_actionable_events(topic="action-requests")
        
        # Build schema-based prompt
        prompt = self._build_prompt(trigger, events, custom_context)
        
        # Build system message with strategy guidance
        system_msg = self.system_instructions or "You are a planning agent that decides the next step in a workflow."
        strategy_guidance = self._get_strategy_guidance()
        full_system_msg = f"{system_msg}\n\n{strategy_guidance}"
        
        # Call LLM with decision schema
        decision_schema = PlannerDecision.model_json_schema()
        
        logger.debug(f"Calling LLM {self.reasoning_model} for decision (plan_id={plan_id})")
        
        try:
            # Use litellm for model-agnostic LLM calls
            response = await self._litellm.acompletion(
                model=self.reasoning_model,
                messages=[
                    {"role": "system", "content": full_system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                api_key=self.api_key,
                api_base=self.api_base,
                response_format={"type": "json_object"},  # Force JSON output
                **self.llm_kwargs,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(
                f"LLM reasoning failed for model {self.reasoning_model}. "
                f"Check API key and model availability. Error: {e}"
            ) from e
        
        # Parse response into PlannerDecision
        decision_data = response.choices[0].message.content
        logger.debug(f"LLM response: {decision_data[:200]}...")  # Log first 200 chars
        
        try:
            decision = PlannerDecision.model_validate_json(decision_data)
        except Exception as e:
            logger.error(f"Failed to parse LLM response as PlannerDecision: {e}")
            logger.debug(f"Raw LLM output: {decision_data}")
            raise ValueError(
                f"LLM returned invalid decision format. "
                f"Ensure the model supports structured output. Error: {e}"
            ) from e
        
        # Validate that referenced events exist
        await self._validate_decision_events(decision, events)
        
        logger.info(
            f"Decision for plan {plan_id}: {decision.next_action.action.value} "
            f"(confidence: {decision.confidence:.2f})"
        )
        
        return decision
    
    async def execute_decision(
        self,
        decision: PlannerDecision,
        context: PlatformContext,
        goal_event: Optional[Any] = None,  # GoalContext type, but avoiding circular import
        plan: Optional[PlanContext] = None,
    ) -> None:
        """Execute the decided action safely.
        
        This method dispatches based on action type:
        - PUBLISH: Publish event to action-requests topic
        - COMPLETE: Send response_event with results
        - WAIT: Pause plan and wait for expected event
        - DELEGATE: Forward to another planner
        
        Args:
            decision: PlannerDecision from reason_next_action()
            context: PlatformContext for service access
            goal_event: Original goal event (for response routing)
            plan: PlanContext for WAIT action (required for pause/resume)
            
        Raises:
            ValueError: If action validation fails or plan missing for WAIT
            
        Examples:
            await planner.execute_decision(decision, context, goal_event=goal, plan=plan)
        """
        action = decision.next_action
        
        logger.info(f"Executing {action.action.value} action for plan {decision.plan_id}")
        
        if action.action == PlanAction.PUBLISH:
            # PUBLISH: Publish new event to trigger workers
            publish_action = action  # Type hint for IDE
            await context.bus.publish(
                topic=publish_action.topic or "action-requests",
                event_type=publish_action.event_type,
                data=publish_action.data,
            )
            logger.debug(
                f"Published {publish_action.event_type} to {publish_action.topic}: "
                f"{publish_action.reasoning}"
            )
        
        elif action.action == PlanAction.COMPLETE:
            # COMPLETE: Finalize plan with response
            complete_action = action  # Type hint for IDE
            if goal_event:
                await context.bus.respond(
                    event_type=goal_event.response_event,
                    correlation_id=goal_event.correlation_id,
                    data=complete_action.result,
                )
                logger.info(
                    f"Plan {decision.plan_id} completed: {complete_action.reasoning}"
                )
            else:
                logger.warning(
                    f"COMPLETE action for plan {decision.plan_id} but no goal_event provided. "
                    f"Cannot send response."
                )
        
        elif action.action == PlanAction.WAIT:
            # WAIT: Pause plan and wait for external input
            wait_action = action  # Type hint for IDE
            
            if not plan:
                raise ValueError(
                    "WAIT action requires PlanContext for pause/resume. "
                    "Pass plan parameter to execute_decision()."
                )
            
            # 1. Pause the plan (sets status="paused")
            await plan.pause(reason=wait_action.reason)
            
            # 2. Store expected event in plan metadata
            plan.results["_waiting_for"] = wait_action.expected_event
            plan.results["_wait_timeout"] = wait_action.timeout_seconds
            await plan.save()
            
            # 3. Publish wait notification for external systems/UIs
            await context.bus.publish(
                topic="system-events",
                event_type="plan.waiting_for_input",
                data={
                    "plan_id": plan.plan_id,
                    "correlation_id": plan.correlation_id,
                    "reason": wait_action.reason,
                    "expected_event": wait_action.expected_event,
                    "timeout_seconds": wait_action.timeout_seconds,
                },
            )
            
            logger.info(
                f"Plan {plan.plan_id} paused, waiting for {wait_action.expected_event}: "
                f"{wait_action.reason}"
            )
        
        elif action.action == PlanAction.DELEGATE:
            # DELEGATE: Forward to another planner
            delegate_action = action  # Type hint for IDE
            await context.bus.publish(
                topic="action-requests",
                event_type=delegate_action.goal_event,
                data=delegate_action.goal_data,
            )
            logger.info(
                f"Delegated to {delegate_action.target_planner} via {delegate_action.goal_event}: "
                f"{delegate_action.reasoning}"
            )
    
    def _build_prompt(
        self,
        trigger: str,
        available_events: List[Any],
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build LLM prompt with available events schema and custom context.
        
        Args:
            trigger: Event that triggered this decision
            available_events: List of EventDefinition objects
            custom_context: Runtime-specific context for this decision
            
        Returns:
            Formatted prompt string with event schemas
        """
        # Format events for LLM (simple text descriptions)
        event_descriptions = "\n".join([
            f"- {e.event_name}: {e.description}" 
            for e in available_events
        ])
        
        # Planning strategy guidance (affects prompt tone)
        strategy_guidance = self._get_strategy_guidance()
        
        # Custom context section
        context_section = ""
        if custom_context:
            context_section = f"""

Additional Context:
{json.dumps(custom_context, indent=2)}

Consider this context when making decisions.
"""
        
        return f"""
{strategy_guidance}

Current Situation:
Trigger: {trigger}

Available events to publish:
{event_descriptions}
{context_section}

Decide on the next action:
- PUBLISH: Publish one of the above events to trigger a worker
- COMPLETE: End the workflow with final result
- WAIT: Wait for external input (e.g., human approval)
- DELEGATE: Forward to another planner

Respond with JSON matching the PlannerDecision schema.
Include:
- plan_id: (provide a unique identifier)
- current_state: (current state in the plan)
- next_action: (one of the action types above with required fields)
- reasoning: (explain why you chose this action)
- confidence: (0.0-1.0, how confident are you in this decision)
"""
    
    def _get_strategy_guidance(self) -> str:
        """Return planning strategy-specific guidance.
        
        Returns:
            Strategy guidance text for LLM prompt
        """
        strategies = {
            "conservative": (
                "Prioritize safety and compliance. When uncertain, use WAIT for human review. "
                "Avoid risky actions. Prefer delegation to specialized planners."
            ),
            "balanced": (
                "Balance speed and safety. Use WAIT only for high-risk decisions. "
                "Delegate complex tasks to appropriate specialists."
            ),
            "aggressive": (
                "Prioritize speed and automation. Minimize WAIT actions. "
                "Only delegate when absolutely necessary."
            ),
        }
        return strategies.get(self.planning_strategy, strategies["balanced"])
    
    async def _validate_decision_events(
        self,
        decision: PlannerDecision,
        available_events: List[Any],
    ) -> None:
        """Validate that decision references only existing events.
        
        This prevents LLM hallucinations.
        
        Args:
            decision: Decision to validate
            available_events: List of available events from Registry
            
        Raises:
            ValueError: If decision references non-existent event
        """
        # Build set of available event names
        event_names = {e.event_name for e in available_events}
        
        # Validate PUBLISH action
        if decision.next_action.action == PlanAction.PUBLISH:
            publish_action = decision.next_action
            if publish_action.event_type not in event_names:
                logger.error(
                    f"LLM hallucination detected: event '{publish_action.event_type}' "
                    f"not in Registry. Available: {event_names}"
                )
                raise ValueError(
                    f"Event '{publish_action.event_type}' not found in Registry. "
                    f"Available events: {', '.join(sorted(event_names))}. "
                    f"This appears to be an LLM hallucination."
                )
        
        # Note: We don't validate expected_event in WAIT action because it might be
        # published by external systems (e.g., approval.granted from UI)
        
        logger.debug(f"Decision validation passed for plan {decision.plan_id}")
