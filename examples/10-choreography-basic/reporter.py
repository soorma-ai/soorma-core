"""
Feedback Reporter Worker.

Generates a concise report from analysis results.
"""

import logging
from typing import Dict

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext

from events import REPORT_REQUESTED_EVENT, REPORT_READY_EVENT


worker = Worker(
    name="feedback-reporter",
    description="Summarizes analyzed feedback",
    capabilities=["feedback_reporting"],
    events_consumed=[REPORT_REQUESTED_EVENT],
    events_produced=[REPORT_READY_EVENT],
)


def _format_report(product: str, summary: Dict[str, object]) -> str:
    """Build a short report string for the analyst.

    Args:
        product: Product name for the report.
        summary: Sentiment summary metrics.

    Returns:
        Report string suitable for final output.
    """
    positive = summary.get("positive", 0)
    negative = summary.get("negative", 0)
    neutral = summary.get("neutral", 0)
    average = summary.get("average_rating", 0.0)
    highlights = summary.get("highlights", [])

    lines = [
        f"Feedback Report for {product}",
        f"Average rating: {average}",
        f"Positive: {positive} | Neutral: {neutral} | Negative: {negative}",
    ]

    if highlights:
        lines.append("Highlights:")
        lines.extend([f"- {item}" for item in highlights])

    return "\n".join(lines)


@worker.on_task("report.requested")
async def handle_report(task: TaskContext, context: PlatformContext) -> None:
    """Generate a summary report from analysis.

    Args:
        task: TaskContext containing analysis results.
        context: PlatformContext for service access (unused).
    """
    _ = context
    product = task.data.get("product", "the product")
    summary = task.data.get("summary", {})
    
    print(f"\n[reporter] ▶ Received: report.requested")
    print(f"[reporter] Task ID: {task.task_id}")
    print(f"[reporter] Building report for {product}")

    report = _format_report(product, summary)
    print(f"[reporter] Report generated ({len(report)} chars)")
    print(f"[reporter] ✓ Completing with report.ready response")
    await task.complete(
        {
            "product": product,
            "summary": summary,
            "report": report,
        }
    )


@worker.on_startup
async def startup() -> None:
    """Worker startup hook."""
    print("\n[reporter] feedback-reporter started")
    print("[reporter] Listening for: report.requested")
    print("[reporter] Produces: report.ready")


@worker.on_shutdown
async def shutdown() -> None:
    """Worker shutdown hook."""
    print("[reporter] feedback-reporter shutting down")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    worker.run()
