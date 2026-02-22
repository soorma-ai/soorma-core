"""
Feedback Reporter Worker.

Generates a concise report from analysis results.
"""

from typing import Dict

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext


worker = Worker(
    name="feedback-reporter",
    description="Summarizes analyzed feedback",
    capabilities=["feedback_reporting"],
    events_consumed=["report.requested"],
    events_produced=["report.ready"],
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
    print(f"[reporter] Building report for {product}")

    report = _format_report(product, summary)
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
    print("[reporter] feedback-reporter started")


@worker.on_shutdown
async def shutdown() -> None:
    """Worker shutdown hook."""
    print("[reporter] feedback-reporter shutting down")


if __name__ == "__main__":
    """
    Feedback Reporter Worker.

    Generates a concise report from analysis results.
    """

    from typing import Dict, List

    from soorma import Worker
    from soorma.context import PlatformContext
    from soorma.task_context import TaskContext


    worker = Worker(
        name="feedback-reporter",
        description="Summarizes analyzed feedback",
        capabilities=["feedback_reporting"],
        events_consumed=["report.requested"],
        events_produced=["report.ready"],
    )


    def _build_report(product: str, summary: Dict[str, object], highlights: List[str]) -> Dict[str, object]:
        """Create a concise report payload.

        Args:
            product: Product name.
            summary: Sentiment summary data.
            highlights: Highlight comments.

        Returns:
            Report payload dict.
        """
        return {
            "product": product,
            "sentiment": {
                "positive": summary.get("positive", 0),
                "negative": summary.get("negative", 0),
                "neutral": summary.get("neutral", 0),
                "average_rating": summary.get("average_rating", 0.0),
            },
            "highlights": highlights,
            "summary": (
                f"Feedback on {product}: avg rating "
                f"{summary.get('average_rating', 0.0)} with "
                f"{summary.get('positive', 0)} positive notes."
            ),
        }


    @worker.on_task("report.requested")
    async def handle_report(task: TaskContext, context: PlatformContext) -> None:
        """Generate report from analysis results.

        Args:
            task: TaskContext containing analysis summary.
            context: PlatformContext for service access (unused).
        """
        _ = context
        product = task.data.get("product", "the product")
        analysis = task.data.get("summary", {})
        highlights = analysis.get("highlights", [])

        print(f"[reporter] Building report for {product}")
        report = _build_report(product, analysis, list(highlights))
        await task.complete({"report": report})


    @worker.on_startup
    async def startup() -> None:
        """Worker startup hook."""
        print("[reporter] feedback-reporter started")


    @worker.on_shutdown
    async def shutdown() -> None:
        """Worker shutdown hook."""
        print("[reporter] feedback-reporter shutting down")


    if __name__ == "__main__":
        worker.run()
