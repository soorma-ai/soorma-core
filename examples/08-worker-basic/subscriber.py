#!/usr/bin/env python3
"""
Event Subscriber (Worker async model).

Demonstrates async choreography using action-requests/action-results with
task delegation and explicit completion.
"""

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import DelegationSpec, ResultContext, TaskContext


worker = Worker(
    name="order-processor",
    description="Processes order requests with async delegation",
)


@worker.on_task("order.process.requested")
async def handle_order(task: TaskContext, context: PlatformContext) -> None:
    order_id = task.data.get("order_id")
    items = task.data.get("items", [])

    print("\n" + "=" * 60)
    print("📦 Order received")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Items: {', '.join(items)}")
    print("   Delegating inventory and payment...\n")

    group_id = await task.delegate_parallel([
        DelegationSpec(
            event_type="inventory.reserve.requested",
            data={"order_id": order_id, "items": items},
            response_event="inventory.reserve.completed",
        ),
        DelegationSpec(
            event_type="payment.process.requested",
            data={"order_id": order_id, "amount": task.data.get("total", 0)},
            response_event="payment.process.completed",
        ),
    ])
    task.state["pending_group"] = group_id
    await task.save()


@worker.on_task("inventory.reserve.requested")
async def handle_inventory(task: TaskContext, context: PlatformContext) -> None:
    order_id = task.data.get("order_id")
    items = task.data.get("items", [])
    print(f"🔒 Reserving inventory for {order_id}: {', '.join(items)}")
    await task.complete({"reserved": True, "items": items})


@worker.on_task("payment.process.requested")
async def handle_payment(task: TaskContext, context: PlatformContext) -> None:
    order_id = task.data.get("order_id")
    amount = task.data.get("amount", 0)
    print(f"💳 Processing payment for {order_id}: ${amount:.2f}")
    await task.complete({"charged": True, "amount": amount})


@worker.on_result("inventory.reserve.completed")
@worker.on_result("payment.process.completed")
async def handle_subtask_result(result: ResultContext, context: PlatformContext) -> None:
    task = await result.restore_task()
    task.update_sub_task_result(
        result.correlation_id,
        result.data.get("result", result.data),
    )

    group_id = task.state.get("pending_group")
    aggregated = task.aggregate_parallel_results(group_id) if group_id else None

    if not aggregated:
        await task.save()
        return

    inventory_result = next(
        (info.result for info in task.sub_tasks.values()
         if info.event_type == "inventory.reserve.requested"),
        None,
    )
    payment_result = next(
        (info.result for info in task.sub_tasks.values()
         if info.event_type == "payment.process.requested"),
        None,
    )

    await task.complete({
        "order_id": task.data.get("order_id"),
        "inventory": inventory_result,
        "payment": payment_result,
    })


@worker.on_startup
async def startup() -> None:
    print("\n" + "=" * 60)
    print("🚀 Order Processor Worker started!")
    print("=" * 60)
    print(f"   Name: {worker.name}")
    print("   Listening for action-requests...")
    print("   • order.process.requested")
    print("   • inventory.reserve.requested")
    print("   • payment.process.requested")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    print()


@worker.on_shutdown
async def shutdown() -> None:
    print("\n👋 Order Processor Worker shutting down\n")


if __name__ == "__main__":
    worker.run()
