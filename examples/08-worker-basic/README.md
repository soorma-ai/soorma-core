# 08 - Worker Basic (Async Worker)

**Concepts:** action-requests, action-results, task delegation, async completion

**Difficulty:** Beginner

**Prerequisites:** [01-hello-world](../01-hello-world/), [02-events-simple](../02-events-simple/)

**Teaching Focus:** This example demonstrates the async Worker model:
- Use `action-requests` + caller-specified `response_event`
- Delegate sub-tasks and wait for results
- Complete the parent task explicitly

**Goal:** Learn the basics of async Worker choreography on top of the event
chaining pattern from [02-events-simple](../02-events-simple/).

## Why This Example Exists

This example builds on [02-events-simple](../02-events-simple/) and shows how to move from
event chaining with `announce()` to async task delegation with explicit
completion:

- [02-events-simple](../02-events-simple/) uses business-fact events and
    `announce()` for choreography.
- This example uses action requests/results with `response_event` and
    `task.complete()` to manage async workflows with sub-tasks.

## What You Will Learn

- How to send action requests with `response_event`
- How a Worker delegates sub-tasks and restores state
- How to complete a task after collecting results

## The Pattern

A caller publishes a task request, the Worker delegates sub-tasks, and then completes
once all results arrive.

```
publisher.py                      subscriber.py
    |                                   |
    |-- order.process.requested ------->|  on_task(order.process.requested)
                                        |     |-- delegate inventory.reserve.requested
                                        |     |-- delegate payment.process.requested
                                        |
                                        |<-- inventory.reserve.completed
                                        |<-- payment.process.completed
                                        |
    |<-- order.process.completed -------|
```

## Code Walkthrough

### Publisher ([publisher.py](publisher.py))

The publisher sends an action request and waits for completion:

```python
await client.publish(
    event_type="order.process.requested",
    topic=EventTopic.ACTION_REQUESTS,
    response_event="order.process.completed",
    data={...},
)
```

### Subscriber ([subscriber.py](subscriber.py))

The worker handles the main task and delegates in parallel:

```python
@worker.on_task("order.process.requested")
async def handle_order(task, context):
    group_id = await task.delegate_parallel([
        DelegationSpec(...),
        DelegationSpec(...),
    ])
    task.state["pending_group"] = group_id
    await task.save()
```

Results restore the parent task and complete it when all sub-tasks finish:

```python
@worker.on_result("inventory.reserve.completed")
@worker.on_result("payment.process.completed")
async def handle_subtask_result(result, context):
    task = await result.restore_task()
    task.update_sub_task_result(result.correlation_id, result.data["result"])
    if task.aggregate_parallel_results(task.state["pending_group"]):
        await task.complete({...})
```

## Running the Example

### Terminal 1: Start Platform Services

```bash
soorma dev --build
```

### Terminal 2: Start the Worker

```bash
cd examples/08-worker-basic
python subscriber.py
```

### Terminal 3: Send the Request

```bash
cd examples/08-worker-basic
python publisher.py
```

You should see the worker delegate inventory and payment tasks, then respond with
`order.process.completed`.
