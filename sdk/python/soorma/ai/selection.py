"""EventSelector — LLM-based event routing utility (RF-SDK-017).

EventSelector enables agents to dynamically pick the most appropriate event to
publish given the current agent state, using an LLM for reasoning. It reuses
``context.toolkit`` (EventToolkit) for event discovery, keeping it fully within
the two-layer architecture — no direct RegistryClient access.

Design decisions (see ACTION_PLAN_Phase3_SDK_Implementation.md §5):
  - FDE-1: f-string templates instead of Jinja2 (avoid extra dependency)
  - FDE-3: EventSelectionError co-located in this file (premature to extract)

Usage::

    selector = EventSelector(
        context=context,
        topic=EventTopic.ACTION_REQUESTS,
        model="gpt-4o-mini",
    )
    decision = await selector.select_event(state={"user_goal": "find flights"})
    await selector.publish_decision(decision, correlation_id=task.id)
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from soorma_common.decisions import EventDecision
from soorma_common.events import EventTopic
from soorma_common import EventDefinition

if TYPE_CHECKING:
    # Avoid circular import at runtime — PlatformContext imports this module indirectly
    from soorma.context import PlatformContext

# litellm is an optional dependency (pip install soorma-core[ai]).
# Module-level import makes the name patchable via patch("soorma.ai.selection.litellm").
try:
    import litellm  # type: ignore[import]
except ImportError:
    litellm = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default prompt template (FDE-1: f-string substitution, no Jinja2)
# Placeholders: {state_json} and {events_json}
# ---------------------------------------------------------------------------

DEFAULT_SELECTOR_PROMPT = """\
You are an event routing agent. Given the current state and available events, \
select the most appropriate event to publish.

Current State:
{state_json}

Available Events:
{events_json}

Respond with a JSON object:
{{
  "event_type": "<selected event name>",
  "topic": "<event topic>",
  "payload": {{<generated payload conforming to event schema>}},
  "reasoning": "<why this event was selected>"
}}
"""


# ---------------------------------------------------------------------------
# Custom exception (FDE-3: co-located for now)
# ---------------------------------------------------------------------------

class EventSelectionError(Exception):
    """Raised when EventSelector cannot produce a valid routing decision.

    Possible causes:
      - LLM returned malformed JSON
      - LLM selected an event that does not exist in the registry
      - No events discovered for the given topic
    """


# ---------------------------------------------------------------------------
# EventSelector
# ---------------------------------------------------------------------------

class EventSelector:
    """LLM-based event selector for intelligent event routing.

    Discovers available events for a topic via ``context.toolkit``, constructs
    an LLM prompt from the agent state and event catalogue, and returns a
    validated :class:`~soorma_common.decisions.EventDecision`.

    Requires ``litellm`` (install with ``pip install soorma-core[ai]``).

    Args:
        context: PlatformContext providing ``context.toolkit`` for event
                 discovery and ``context.bus`` for publishing decisions.
        topic: EventTopic to discover candidate events from.
        prompt_template: Optional f-string template with ``{state_json}`` and
                         ``{events_json}`` placeholders.  Defaults to
                         :data:`DEFAULT_SELECTOR_PROMPT`.
        model: LiteLLM model identifier (default: ``"gpt-4o-mini"``).
        api_key: Optional API key override (uses provider env var if omitted).
        api_base: Optional base URL for custom LLM endpoints (Azure, etc.).

    Example::

        selector = EventSelector(
            context=context,
            topic=EventTopic.ACTION_REQUESTS,
            model="gpt-4o-mini",
        )
        decision = await selector.select_event(state={"objective": "book flight"})
        await selector.publish_decision(
            decision,
            correlation_id=task.id,
            response_event="booking.completed",
        )
    """

    def __init__(
        self,
        context: "PlatformContext",
        topic: EventTopic,
        prompt_template: Optional[str] = None,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> None:
        self.context = context
        self.topic = topic
        # Use the provided template or fall back to the default (FDE-1)
        self.prompt_template = prompt_template or DEFAULT_SELECTOR_PROMPT
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    async def select_event(
        self,
        state: Dict[str, Any],
    ) -> EventDecision:
        """Select the best event for the current agent state using an LLM.

        Discovers available events for this selector's topic, builds an
        f-string prompt from ``state`` and the event catalogue, calls the LLM,
        and validates the selected event exists in the registry before returning.

        Args:
            state: Current agent state dict (any JSON-serialisable structure).

        Returns:
            EventDecision with a validated ``event_type``, ``topic``,
            ``payload``, and ``reasoning``.

        Raises:
            EventSelectionError: If LLM output is malformed or references an
                                 event not present in the discovered list.
            RuntimeError: If litellm is not installed.
        """
        if litellm is None:
            raise RuntimeError(
                "litellm is not installed. Install with: pip install soorma-core[ai]"
            )

        # 1. Discover available events via context.toolkit (two-layer compliance §2)
        events: List[EventDefinition] = await self.context.toolkit.discover_events(
            topic=self.topic
        )

        # 2. Build prompt
        prompt = self._build_prompt(state, events)

        # 3. Call LLM (BYO model — litellm handles provider routing)
        logger.debug(
            "[EventSelector] Calling %s for event selection (topic=%s, events=%d)",
            self.model,
            self.topic.value,
            len(events),
        )
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an event routing agent. Respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                api_key=self.api_key,
                api_base=self.api_base,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.error("[EventSelector] LLM call failed: %s", exc)
            raise RuntimeError(
                f"LLM call failed for model {self.model}. Check API key and availability. Error: {exc}"
            ) from exc

        # 4. Parse and validate response
        content: str = response.choices[0].message.content
        discovered_event_names = [e.event_name for e in events]
        decision = self._parse_llm_response(content, discovered_event_names)

        logger.info(
            "[EventSelector] Selected event: %s (topic=%s)",
            decision.event_type,
            decision.topic,
        )
        return decision

    async def publish_decision(
        self,
        decision: EventDecision,
        correlation_id: str,
        response_event: Optional[str] = None,
        response_topic: Optional[str] = None,
    ) -> None:
        """Publish the routing decision via ``context.bus``.

        Passes ``response_event`` explicitly to the bus publish call to
        satisfy the ARCHITECTURE_PATTERNS.md §3 requirement for explicit
        response event names (no inferred names).

        Args:
            decision: Validated EventDecision from :meth:`select_event`.
            correlation_id: Correlation ID for request/response tracking.
            response_event: Optional response event name (explicit per §3).
            response_topic: Optional response topic (defaults to
                            EventTopic.ACTION_RESULTS).

        Returns:
            None
        """
        await self.context.bus.publish(
            topic=decision.topic,
            event_type=decision.event_type,
            data=decision.payload,
            correlation_id=correlation_id,
            response_event=response_event,
            response_topic=response_topic,
        )

    def _build_prompt(
        self,
        state: Dict[str, Any],
        events: List[EventDefinition],
    ) -> str:
        """Build the LLM routing prompt from state and event catalogue.

        Uses f-string substitution (FDE-1) on the configured template.

        Args:
            state: Current agent state.
            events: Discovered event definitions.

        Returns:
            Formatted prompt string ready for LLM consumption.
        """
        events_formatted = self.context.toolkit.format_for_llm(events)
        state_json = json.dumps(state, indent=2, default=str)
        events_json = json.dumps(events_formatted, indent=2, default=str)
        # f-string substitution (FDE-1 — no Jinja2 needed for single-level templates)
        return self.prompt_template.format(
            state_json=state_json,
            events_json=events_json,
        )

    def _parse_llm_response(
        self,
        content: str,
        discovered_event_names: List[str],
    ) -> EventDecision:
        """Parse LLM JSON response into an EventDecision and validate it.

        Args:
            content: Raw LLM response content (expected JSON string).
            discovered_event_names: List of valid event names from registry.

        Returns:
            Validated EventDecision.

        Raises:
            EventSelectionError: If JSON is malformed or event_type is not in
                                 discovered_event_names.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise EventSelectionError(
                f"LLM returned malformed JSON: {exc}\nRaw content: {content[:200]}"
            ) from exc

        # Validate that the selected event exists in the registry
        # This prevents LLM hallucinations from triggering non-existent events
        event_type = data.get("event_type", "")
        if event_type not in discovered_event_names:
            raise EventSelectionError(
                f"LLM selected event '{event_type}' which is not in the discovered event list: "
                f"{discovered_event_names}"
            )

        try:
            return EventDecision(
                event_type=data["event_type"],
                topic=data["topic"],
                payload=data.get("payload", {}),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence"),
            )
        except Exception as exc:
            raise EventSelectionError(
                f"Failed to construct EventDecision from LLM output: {exc}"
            ) from exc
