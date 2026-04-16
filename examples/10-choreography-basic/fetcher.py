"""
Feedback Fetcher Worker.

Simulates loading customer feedback from a datastore.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext

from events import DATA_FETCH_REQUESTED_EVENT, DATA_FETCH_RESPONDED_EVENT

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "10-choreography-basic"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)


worker = Worker(
    name="feedback-fetcher",
    description="Fetches customer feedback entries",
    capabilities=["feedback_fetch"],
    events_consumed=[DATA_FETCH_REQUESTED_EVENT],
    events_produced=[DATA_FETCH_RESPONDED_EVENT],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


def _sample_feedback(product: str) -> List[Dict[str, object]]:
    """Provide a deterministic set of mock feedback items.

    Args:
        product: Product name for context.

    Returns:
        List of feedback entries.
    """
    return [
        {"comment": f"Love the {product} build quality.", "rating": 5},
        {"comment": f"The {product} setup was confusing.", "rating": 2},
        {"comment": f"Great battery life on the {product}.", "rating": 4},
        {"comment": f"The {product} is fine but pricey.", "rating": 3},
        {"comment": f"Had issues with {product} support.", "rating": 1},
    ]


@worker.on_task("data.fetch.requested")
async def handle_fetch(task: TaskContext, context: PlatformContext) -> None:
    """Fetch feedback payloads.

    Args:
        task: TaskContext containing fetch request data.
        context: PlatformContext for service access (unused).
    """
    _ = context
    product = task.data.get("product", "the product")
    sample_size = int(task.data.get("sample_size", 3))

    print(f"\n[fetcher] ▶ Received: data.fetch.requested")
    print(f"[fetcher] Task ID: {task.task_id}")
    print(f"[fetcher] Correlation ID: {task.correlation_id}")
    print(f"[fetcher] Response event: {task.response_event}")
    print(f"[fetcher] Loading feedback for {product} (n={sample_size})")
    await asyncio.sleep(0.3)

    feedback = _sample_feedback(product)[:sample_size]
    print(f"[fetcher] Fetched {len(feedback)} feedback entries")
    print(f"[fetcher] ✓ Completing with response_event={task.response_event}")
    await task.complete(
        {
            "product": product,
            "feedback": feedback,  # Align with schema (AnalysisRequestPayload expects 'feedback')
        }
    )


@worker.on_startup
async def startup() -> None:
    """Worker startup hook."""
    print("\n[fetcher] feedback-fetcher started")
    print("[fetcher] Listening for: data.fetch.requested")
    print("[fetcher] Produces: data.fetch.requested (on action-results topic)")


@worker.on_shutdown
async def shutdown() -> None:
    """Worker shutdown hook."""
    print("[fetcher] feedback-fetcher shutting down")


if __name__ == "__main__":
    # Configure logging - show agent logic, suppress noisy SDK logs
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    # Suppress noisy SDK/infrastructure logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("soorma.registry.client").setLevel(logging.WARNING)
    logging.getLogger("soorma.agents.base").setLevel(logging.WARNING)
    logging.getLogger("soorma.events").setLevel(logging.WARNING)
    logging.getLogger("soorma.context").setLevel(logging.WARNING)
    logging.getLogger("soorma.task_context").setLevel(logging.WARNING)
    worker.run()
