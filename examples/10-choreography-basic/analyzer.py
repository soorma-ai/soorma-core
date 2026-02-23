"""
Feedback Analyzer Worker.

Simulates sentiment analysis for feedback items.
"""

import logging
from typing import Dict, List

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext

from events import ANALYSIS_REQUESTED_EVENT, ANALYSIS_COMPLETED_EVENT


worker = Worker(
    name="feedback-analyzer",
    description="Analyzes feedback sentiment",
    capabilities=["feedback_analysis"],
    events_consumed=[ANALYSIS_REQUESTED_EVENT],
    events_produced=[ANALYSIS_COMPLETED_EVENT],
)


def _summarize(entries: List[Dict[str, object]]) -> Dict[str, object]:
    """Compute a basic sentiment summary from feedback entries.

    Args:
        entries: List of feedback entries with rating fields.

    Returns:
        Summary metrics and highlights.
    """
    positive = 0
    negative = 0
    neutral = 0
    ratings: List[int] = []
    highlights: List[str] = []

    for entry in entries:
        rating = int(entry.get("rating", 3))
        ratings.append(rating)
        if rating >= 4:
            positive += 1
            highlights.append(str(entry.get("comment", "")))
        elif rating <= 2:
            negative += 1
            highlights.append(str(entry.get("comment", "")))
        else:
            neutral += 1

    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    return {
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "average_rating": round(avg_rating, 2),
        "highlights": highlights[:3],
    }


@worker.on_task("analysis.requested")
async def handle_analysis(task: TaskContext, context: PlatformContext) -> None:
    """Analyze feedback items for sentiment.

    Args:
        task: TaskContext containing feedback entries.
        context: PlatformContext for service access (unused).
    """
    _ = context
    product = task.data.get("product", "the product")
    entries = task.data.get("entries", [])
    
    print(f"\n[analyzer] ▶ Received: analysis.requested")
    print(f"[analyzer] Task ID: {task.task_id}")
    print(f"[analyzer] Analyzing {len(entries)} entries for {product}")

    summary = _summarize(entries)
    print(f"[analyzer] Summary: {summary['positive']} positive, {summary['negative']} negative, avg={summary['average_rating']}")
    print(f"[analyzer] ✓ Completing with analysis.completed response")
    await task.complete(
        {
            "product": product,
            "summary": summary,
            "entries": entries,
        }
    )


@worker.on_startup
async def startup() -> None:
    """Worker startup hook."""
    print("\n[analyzer] feedback-analyzer started")
    print("[analyzer] Listening for: analysis.requested")
    print("[analyzer] Produces: analysis.completed")


@worker.on_shutdown
async def shutdown() -> None:
    """Worker shutdown hook."""
    print("[analyzer] feedback-analyzer shutting down")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    worker.run()
