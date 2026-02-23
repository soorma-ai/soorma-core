"""
Feedback Fetcher Worker.

Simulates loading customer feedback from a datastore.
"""

import asyncio
from typing import Dict, List

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext

from events import DATA_FETCH_REQUESTED_EVENT, DATA_FETCHED_EVENT


worker = Worker(
    name="feedback-fetcher",
    description="Fetches customer feedback entries",
    capabilities=["feedback_fetch"],
    events_consumed=[DATA_FETCH_REQUESTED_EVENT],
    events_produced=[DATA_FETCHED_EVENT],
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

    print(f"[fetcher] Loading feedback for {product} (n={sample_size})")
    await asyncio.sleep(0.3)

    feedback = _sample_feedback(product)[:sample_size]
    await task.complete(
        {
            "product": product,
            "sample_size": sample_size,
            "entries": feedback,
            "source": "mock-db",
        }
    )


@worker.on_startup
async def startup() -> None:
    """Worker startup hook."""
    print("[fetcher] feedback-fetcher started")


@worker.on_shutdown
async def shutdown() -> None:
    """Worker shutdown hook."""
    print("[fetcher] feedback-fetcher shutting down")


if __name__ == "__main__":
    worker.run()
