"""
Task Context - Async Worker choreography with persistence and delegation (RF-SDK-004).

The TaskContext enables async Workers to delegate sub-tasks and resume execution
when results arrive. This implements the action request/result pattern with:
- Task persistence across delegations
- Sequential and parallel sub-task delegation
- Result correlation and aggregation
- Explicit task completion

Usage:
    @worker.on_task("process_order")
    async def handle_order(task: TaskContext, context: PlatformContext):
        # Save initial state
        task.state["order_details"] = task.data["order"]
        await task.save()
        
        # Delegate to payment worker
        payment_id = await task.delegate(
            event_type="process_payment",
            data={"amount": task.data["amount"]},
            response_event="payment_completed",
        )
        # Handler pauses - resumes when payment result arrives
    
    @worker.on_result("payment_completed")
    async def handle_payment_result(result: ResultContext, context: PlatformContext):
        # Restore parent task
        task = await result.restore_task()
        
        # Update with result
        task.update_sub_task_result(result.correlation_id, result.data)
        
        if result.success:
            # Complete the order
            await task.complete({"status": "completed"})
        else:
            await task.complete({"status": "failed", "error": result.error})

Related Patterns:
    - docs/EVENT_PATTERNS.md: Action request/result choreography
    - docs/MEMORY_PATTERNS.md: Task context persistence
    - examples/08-worker-basic: Complete delegation example
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from soorma_common.events import EventEnvelope

from .context import PlatformContext


@dataclass
class SubTaskInfo:
    """
    Tracking metadata for a delegated sub-task.
    
    Attributes:
        sub_task_id: Unique identifier for the sub-task (used as correlation_id)
        event_type: Event type of the delegation request
        response_event: Expected result event type
        status: Current status ("pending" or "completed")
        parallel_group_id: Optional group ID for parallel fan-out/fan-in
        result: Result data when status is "completed"
    """
    sub_task_id: str
    event_type: str
    response_event: str
    status: str
    parallel_group_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize SubTaskInfo to dictionary for persistence.
        
        Returns:
            Dictionary representation with all fields
        """
        return {
            "sub_task_id": self.sub_task_id,
            "event_type": self.event_type,
            "response_event": self.response_event,
            "status": self.status,
            "parallel_group_id": self.parallel_group_id,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTaskInfo":
        """
        Deserialize SubTaskInfo from persisted dictionary.
        
        Args:
            data: Dictionary with SubTaskInfo fields
            
        Returns:
            SubTaskInfo instance
        """
        return cls(
            sub_task_id=data["sub_task_id"],
            event_type=data["event_type"],
            response_event=data["response_event"],
            status=data.get("status", "pending"),
            parallel_group_id=data.get("parallel_group_id"),
            result=data.get("result"),
        )


@dataclass
class DelegationSpec:
    """
    Specification for a parallel delegation task.
    
    Used with TaskContext.delegate_parallel() to fan-out multiple sub-tasks
    and aggregate results when all complete.
    
    Attributes:
        event_type: Event type to publish for this sub-task
        data: Request data payload
        response_event: Expected result event type
        response_topic: Topic for result event (default: "action-results")
    
    Example:
        specs = [
            DelegationSpec(
                event_type="validate_inventory",
                data={"product_id": "P123"},
                response_event="inventory_validated"
            ),
            DelegationSpec(
                event_type="check_pricing",
                data={"product_id": "P123"},
                response_event="pricing_checked"
            ),
        ]
        group_id = await task.delegate_parallel(specs)
    """
    event_type: str
    data: Dict[str, Any]
    response_event: str
    response_topic: str = "action-results"


@dataclass
class TaskContext:
    """
    Execution context for async Worker tasks with persistence and delegation.
    
    TaskContext enables Workers to:
    - Persist state across delegations
    - Delegate sequential or parallel sub-tasks
    - Resume execution when results arrive
    - Explicitly complete with response event
    
    Attributes:
        task_id: Unique task identifier
        event_type: Event type that triggered this task
        plan_id: Optional plan ID for coordinated multi-task workflows
        data: Request data payload from triggering event
        response_event: Event type to publish when task completes
        response_topic: Topic for response event (default: "action-results")
        sub_tasks: Map of sub-task IDs to tracking metadata
        state: Worker-specific state (persisted across delegations)
        tenant_id: Tenant context from event
        user_id: User context from event
        agent_id: Worker's agent ID
        task_name: Human-readable task name
        correlation_id: Correlation ID for tracing
        session_id: Session ID for user context
        goal_id: Goal ID for plan coordination
        timeout: Optional task timeout in seconds
        priority: Task priority (higher = more urgent)
    
    Lifecycle:
        1. Worker receives action request event
        2. TaskContext created from event via from_event()
        3. Worker delegates sub-tasks via delegate() or delegate_parallel()
        4. Worker calls save() to persist state
        5. Sub-task workers publish results to action-results topic
        6. Original worker receives results via on_result() handler
        7. ResultContext.restore_task() retrieves parent TaskContext
        8. Worker aggregates results and calls complete()
    
    Example (Sequential):
        @worker.on_task("book_appointment")
        async def book(task: TaskContext, context: PlatformContext):
            task.state["appointment"] = task.data["appointment"]
            await task.save()
            
            # Check availability first
            await task.delegate(
                event_type="check_availability",
                data={"calendar_id": task.data["calendar_id"]},
                response_event="availability_checked"
            )
        
        @worker.on_result("availability_checked")
        async def handle_availability(result: ResultContext, context: PlatformContext):
            task = await result.restore_task()
            
            if result.success:
                # Now reserve the slot
                await task.delegate(
                    event_type="reserve_slot",
                    data={"slot_id": result.data["available_slot"]},
                    response_event="slot_reserved"
                )
            else:
                await task.complete({"status": "no_availability"})
        
        @worker.on_result("slot_reserved")
        async def handle_reservation(result: ResultContext, context: PlatformContext):
            task = await result.restore_task()
            await task.complete({"status": "booked", "slot": result.data["slot"]})
    
    Example (Parallel):
        @worker.on_task("process_order")
        async def process(task: TaskContext, context: PlatformContext):
            # Fan-out to multiple workers
            group_id = await task.delegate_parallel([
                DelegationSpec("validate_inventory", {"sku": "P123"}, "inventory_validated"),
                DelegationSpec("check_pricing", {"sku": "P123"}, "pricing_checked"),
                DelegationSpec("verify_address", {"address": "..."}, "address_verified"),
            ])
            task.state["parallel_group"] = group_id
            await task.save()
        
        @worker.on_result("inventory_validated")
        @worker.on_result("pricing_checked")
        @worker.on_result("address_verified")
        async def handle_result(result: ResultContext, context: PlatformContext):
            task = await result.restore_task()
            task.update_sub_task_result(result.correlation_id, result.data)
            
            # Check if all parallel tasks complete
            group_id = task.state["parallel_group"]
            aggregated = task.aggregate_parallel_results(group_id)
            
            if aggregated:
                # All parallel tasks done - complete order
                await task.complete({"status": "completed", "validations": aggregated})
    """
    task_id: str
    event_type: str
    plan_id: Optional[str]
    data: Dict[str, Any]
    response_event: Optional[str]
    response_topic: str = "action-results"
    sub_tasks: Dict[str, SubTaskInfo] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_name: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    goal_id: Optional[str] = None
    timeout: Optional[float] = None
    priority: int = 0

    # Internal fields (not persisted)
    _context: Optional[PlatformContext] = field(default=None, repr=False)
    _register_produced_event: Optional[Callable[[str], None]] = field(default=None, repr=False)

    @classmethod
    def from_event(
        cls,
        event: EventEnvelope,
        context: PlatformContext,
        agent_id: Optional[str] = None,
        register_produced_event: Optional[Callable[[str], None]] = None,
    ) -> "TaskContext":
        """
        Create TaskContext from incoming action request event.
        
        Called by Worker when processing on_task() handler.
        
        Args:
            event: Action request event envelope
            context: Platform service clients
            agent_id: Worker's agent ID
            register_produced_event: Callback to register produced event types
            
        Returns:
            TaskContext initialized from event data
        """
        data = event.data or {}
        return cls(
            task_id=data.get("task_id", str(uuid4())),
            event_type=event.type,
            plan_id=data.get("plan_id"),
            data=data,
            response_event=event.response_event or data.get("response_event"),
            response_topic=event.response_topic or data.get("response_topic", "action-results"),
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            agent_id=agent_id,
            task_name=data.get("task_name"),
            correlation_id=event.correlation_id,
            session_id=event.session_id,
            goal_id=data.get("goal_id"),
            timeout=data.get("timeout"),
            priority=data.get("priority", 0),
            _context=context,
            _register_produced_event=register_produced_event,
        )

    @classmethod
    def from_memory(
        cls,
        task_data: Any,
        context: PlatformContext,
        agent_id: Optional[str] = None,
        register_produced_event: Optional[Callable[[str], None]] = None,
    ) -> "TaskContext":
        """
        Reconstruct TaskContext from persisted memory.
        
        Called by restore() or restore_task() to resume a paused task.
        Sub-task tracking metadata is extracted from state._sub_tasks.
        
        Args:
            task_data: TaskContextDTO from Memory Service
            context: Platform service clients
            agent_id: Worker's agent ID
            register_produced_event: Callback to register produced event types
            
        Returns:
            TaskContext with restored state and sub-task tracking
        """
        state = dict(task_data.state or {})
        raw_sub_tasks = state.pop("_sub_tasks", None) or {}
        sub_tasks = {
            sub_task_id: SubTaskInfo.from_dict(info)
            for sub_task_id, info in raw_sub_tasks.items()
        }
        return cls(
            task_id=task_data.task_id,
            event_type=task_data.event_type,
            plan_id=task_data.plan_id,
            data=task_data.data or {},
            response_event=task_data.response_event,
            response_topic=task_data.response_topic or "action-results",
            sub_tasks=sub_tasks,
            state=state,
            tenant_id=task_data.tenant_id,
            user_id=task_data.user_id,
            agent_id=agent_id,
            _context=context,
            _register_produced_event=register_produced_event,
        )

    async def report_progress(self, progress: float, message: Optional[str] = None) -> None:
        """
        Emit progress update for task tracking.
        
        Args:
            progress: Progress percentage (0.0 to 1.0)
            message: Optional progress message
        """
        if self._context:
            await self._context.tracker.emit_progress(
                plan_id=self.plan_id or "",
                task_id=self.task_id,
                status="running",
                progress=progress,
                message=message,
            )

    async def save(self) -> None:
        """
        Persist task state to Memory Service.
        
        Saves:
        - Task metadata (task_id, event_type, response_event, etc.)
        - Worker state dict
        - Sub-task tracking metadata
        
        Required before delegating sub-tasks so ResultContext.restore_task()
        can retrieve the parent task.
        
        Raises:
            RuntimeError: If PlatformContext not available (internal error)
        
        Example:
            task.state["order_details"] = task.data["order"]
            await task.save()
            await task.delegate(...)
        """
        if not self._context:
            raise RuntimeError("TaskContext.save() requires a PlatformContext")
        # Serialize sub-task metadata into state for persistence
        serialized_state = dict(self.state)
        serialized_state["_sub_tasks"] = {
            sub_task_id: info.to_dict() for sub_task_id, info in self.sub_tasks.items()
        }
        await self._context.memory.store_task_context(
            task_id=self.task_id,
            plan_id=self.plan_id,
            event_type=self.event_type,
            response_event=self.response_event,
            response_topic=self.response_topic,
            data=self.data,
            sub_tasks=list(self.sub_tasks.keys()),
            state=serialized_state,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

    @classmethod
    async def restore(
        cls,
        task_id: str,
        context: PlatformContext,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        register_produced_event: Optional[Callable[[str], None]] = None,
    ) -> Optional["TaskContext"]:
        """
        Restore a previously saved task by task_id.
        
        For most use cases, prefer ResultContext.restore_task() which
        looks up the parent task from a sub-task correlation_id.
        
        Args:
            task_id: Task identifier to restore
            context: Platform service clients
            tenant_id: Tenant ID from event context (REQUIRED)
            user_id: User ID from event context (REQUIRED)
            agent_id: Worker's agent ID
            register_produced_event: Callback to register produced event types
            
        Returns:
            TaskContext if found, None otherwise
        """
        task_data = await context.memory.get_task_context(
            task_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        if not task_data:
            return None
        return cls.from_memory(task_data, context, agent_id=agent_id, register_produced_event=register_produced_event)

    async def delegate(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
        response_topic: str = "action-results",
    ) -> str:
        """
        Delegate a sub-task to another Worker (sequential pattern).
        
        Creates a SubTaskInfo to track the delegation, persists state via save(),
        and publishes an action request event. The worker waits for the result
        event to arrive at an on_result() handler.
        
        Args:
            event_type: Action request event type (e.g., "process_payment")
            data: Request payload for sub-task worker
            response_event: Expected result event type (e.g., "payment_completed")
            response_topic: Topic for result event (default: "action-results")
            
        Returns:
            sub_task_id: Unique sub-task identifier (used as correlation_id)
            
        Raises:
            RuntimeError: If PlatformContext not available (internal error)
        
        Example:
            @worker.on_task("schedule_appointment")
            async def schedule(task: TaskContext, context: PlatformContext):
                # Check availability first
                availability_id = await task.delegate(
                    event_type="check_availability",
                    data={"calendar_id": task.data["calendar_id"]},
                    response_event="availability_checked"
                )
                # Handler pauses until result arrives
            
            @worker.on_result("availability_checked")
            async def handle_availability(result: ResultContext, context: PlatformContext):
                task = await result.restore_task()
                if result.success:
                    # Availability confirmed - reserve slot
                    await task.delegate(
                        event_type="reserve_slot",
                        data={"slot_id": result.data["slot_id"]},
                        response_event="slot_reserved"
                    )
        """
        if not self._context:
            raise RuntimeError("TaskContext.delegate() requires a PlatformContext")
        sub_task_id = str(uuid4())
        self.sub_tasks[sub_task_id] = SubTaskInfo(
            sub_task_id=sub_task_id,
            event_type=event_type,
            response_event=response_event,
            status="pending",
        )
        await self.save()
        request_data = dict(data)
        request_data.setdefault("task_id", sub_task_id)
        if self.plan_id:
            request_data.setdefault("plan_id", self.plan_id)
        await self._context.bus.request(
            event_type=event_type,
            data=request_data,
            response_event=response_event,
            correlation_id=sub_task_id,
            response_topic=response_topic,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
        return sub_task_id

    async def delegate_parallel(self, sub_tasks: List[DelegationSpec]) -> str:
        """
        Delegate multiple sub-tasks in parallel (fan-out/fan-in pattern).
        
        Creates SubTaskInfo for each spec with a shared parallel_group_id,
        persists state, and publishes all action requests. Use aggregate_parallel_results()
        to detect when all sub-tasks complete.
        
        Args:
            sub_tasks: List of delegation specifications
            
        Returns:
            parallel_group_id: Shared group identifier for all sub-tasks
            
        Raises:
            RuntimeError: If PlatformContext not available (internal error)
        
        Example:
            @worker.on_task("validate_order")
            async def validate(task: TaskContext, context: PlatformContext):
                # Fan-out to multiple validation workers
                group_id = await task.delegate_parallel([
                    DelegationSpec(
                        event_type="check_inventory",
                        data={"sku": task.data["sku"]},
                        response_event="inventory_checked"
                    ),
                    DelegationSpec(
                        event_type="verify_payment",
                        data={"amount": task.data["amount"]},
                        response_event="payment_verified"
                    ),
                    DelegationSpec(
                        event_type="validate_address",
                        data={"address": task.data["shipping_address"]},
                        response_event="address_validated"
                    ),
                ])
                task.state["validation_group"] = group_id
                await task.save()
            
            @worker.on_result("inventory_checked")
            @worker.on_result("payment_verified")
            @worker.on_result("address_validated")
            async def handle_validation_result(result: ResultContext, context: PlatformContext):
                task = await result.restore_task()
                
                # Record this result
                task.update_sub_task_result(result.correlation_id, result.data)
                await task.save()
                
                # Check if all validations complete
                group_id = task.state["validation_group"]
                aggregated = task.aggregate_parallel_results(group_id)
                
                if aggregated:
                    # All validations done - fan-in
                    all_valid = all(
                        r.get("valid") for r in aggregated.values()
                    )
                    await task.complete({
                        "valid": all_valid,
                        "validations": aggregated
                    })
        """
        if not self._context:
            raise RuntimeError("TaskContext.delegate_parallel() requires a PlatformContext")
        parallel_group_id = str(uuid4())
        # Create SubTaskInfo for each spec with shared group ID
        for spec in sub_tasks:
            sub_task_id = str(uuid4())
            self.sub_tasks[sub_task_id] = SubTaskInfo(
                sub_task_id=sub_task_id,
                event_type=spec.event_type,
                response_event=spec.response_event,
                status="pending",
                parallel_group_id=parallel_group_id,
            )
        await self.save()
        # Publish all action requests
        for sub_task_id, info in self.sub_tasks.items():
            if info.parallel_group_id != parallel_group_id:
                continue
            spec = next(s for s in sub_tasks if s.event_type == info.event_type)
            request_data = dict(spec.data)
            request_data.setdefault("task_id", sub_task_id)
            if self.plan_id:
                request_data.setdefault("plan_id", self.plan_id)
            await self._context.bus.request(
                event_type=info.event_type,
                data=request_data,
                response_event=info.response_event,
                correlation_id=sub_task_id,
                response_topic=spec.response_topic,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
        return parallel_group_id

    def aggregate_parallel_results(self, parallel_group_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if all parallel sub-tasks in a group have completed.
        
        Args:
            parallel_group_id: Group identifier from delegate_parallel()
            
        Returns:
            Map of sub_task_id to result data if all complete, None otherwise
        
        Example:
            aggregated = task.aggregate_parallel_results(group_id)
            if aggregated:
                # All sub-tasks done - process results
                for sub_task_id, result in aggregated.items():
                    print(f"{sub_task_id}: {result}")
        """
        group_tasks = [
            info for info in self.sub_tasks.values() if info.parallel_group_id == parallel_group_id
        ]
        if group_tasks and all(info.status == "completed" for info in group_tasks):
            return {info.sub_task_id: info.result for info in group_tasks}
        return None

    def update_sub_task_result(self, sub_task_id: str, result: Dict[str, Any]) -> None:
        """
        Update sub-task tracking with result data.
        
        Called in on_result() handler after restoring parent task.
        
        Args:
            sub_task_id: Sub-task identifier (from result.correlation_id)
            result: Result data from sub-task worker
        
        Example:
            @worker.on_result("payment_completed")
            async def handle_payment(result: ResultContext, context: PlatformContext):
                task = await result.restore_task()
                task.update_sub_task_result(result.correlation_id, result.data)
                await task.save()
        """
        info = self.sub_tasks.get(sub_task_id)
        if not info:
            return
        info.status = "completed"
        info.result = result

    def is_complete(self) -> bool:
        """
        Check if all sub-tasks have completed.
        
        Returns:
            True if no sub-tasks or all sub-tasks status=="completed"
        """
        if not self.sub_tasks:
            return True
        return all(info.status == "completed" for info in self.sub_tasks.values())

    async def complete(self, result: Dict[str, Any]) -> None:
        """
        Complete the task by publishing response event and cleaning up state.
        
        Publishes the response_event that was specified in the original action request,
        registers the produced event type with Worker, and deletes task context from memory.
        
        Args:
            result: Result data to include in response event
            
        Raises:
            RuntimeError: If PlatformContext not available (internal error)
            ValueError: If response_event not set (configuration error)
        
        Example:
            @worker.on_task("process_order")
            async def process(task: TaskContext, context: PlatformContext):
                # ... process order ...
                await task.complete({
                    "order_id": task.data["order_id"],
                    "status": "completed",
                    "total": 99.99
                })
        """
        if not self._context:
            raise RuntimeError("TaskContext.complete() requires a PlatformContext")
        if not self.response_event:
            raise ValueError("TaskContext.complete() requires response_event")
        # Register produced event for Worker metadata
        if self._register_produced_event:
            self._register_produced_event(self.response_event)
        # Publish result event
        await self._context.bus.respond(
            event_type=self.response_event,
            data={
                "task_id": self.task_id,
                "status": "completed",
                "result": result,
            },
            correlation_id=self.task_id,
            topic=self.response_topic,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
        # Clean up persisted state
        await self._context.memory.delete_task_context(
            self.task_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )


@dataclass
class ResultContext:
    """
    Context for handling sub-task results in on_result() handlers.
    
    When a sub-task completes, the result event arrives at the parent worker's
    on_result() handler with a ResultContext. Use restore_task() to retrieve
    the parent TaskContext and continue execution.
    
    Attributes:
        event_type: Result event type (e.g., "payment_completed")
        correlation_id: Sub-task identifier (matches SubTaskInfo.sub_task_id)
        data: Result payload from sub-task worker
        success: True if sub-task succeeded, False if failed
        error: Error message if success=False
    
    Example:
        @worker.on_task("book_appointment")
        async def book(task: TaskContext, context: PlatformContext):
            await task.delegate(
                event_type="check_availability",
                data={"calendar_id": "cal123"},
                response_event="availability_checked"
            )
        
        @worker.on_result("availability_checked")
        async def handle_availability(result: ResultContext, context: PlatformContext):
            # Restore parent task from correlation_id
            task = await result.restore_task()
            
            if result.success:
                available_slot = result.data["slot_id"]
                task.state["selected_slot"] = available_slot
                await task.complete({"status": "booked", "slot": available_slot})
            else:
                await task.complete({"status": "failed", "error": result.error})
    """
    event_type: str
    correlation_id: str
    data: Dict[str, Any]
    success: bool
    error: Optional[str]
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None

    # Internal fields (not persisted)
    _context: Optional[PlatformContext] = field(default=None, repr=False)
    _register_produced_event: Optional[Callable[[str], None]] = field(default=None, repr=False)

    @classmethod
    def from_event(
        cls,
        event: EventEnvelope,
        context: PlatformContext,
        register_produced_event: Optional[Callable[[str], None]] = None,
    ) -> "ResultContext":
        """
        Create ResultContext from incoming result event.
        
        Called by Worker when processing on_result() handler.
        
        Args:
            event: Result event envelope
            context: Platform service clients
            register_produced_event: Callback to register produced event types
            
        Returns:
            ResultContext initialized from event data
        """
        data = event.data or {}
        # Detect success from status or explicit success field
        if "success" in data:
            success = bool(data.get("success"))
        else:
            status = data.get("status")
            success = status != "failed" if status else True
        return cls(
            event_type=event.type,
            correlation_id=event.correlation_id,
            data=data,
            success=success,
            error=data.get("error"),
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            _context=context,
            _register_produced_event=register_produced_event,
        )

    async def restore_task(self) -> TaskContext:
        """
        Restore parent TaskContext from sub-task correlation_id.
        
        Queries Memory Service to find the parent task that delegated
        the sub-task identified by correlation_id.
        
        Returns:
            TaskContext: Parent task with restored state and sub-task tracking
            
        Raises:
            RuntimeError: If PlatformContext not available (internal error)
            ValueError: If no parent task found for correlation_id
        
        Example:
            @worker.on_result("payment_completed")
            async def handle_payment(result: ResultContext, context: PlatformContext):
                # Restore parent task
                task = await result.restore_task()
                
                # Update sub-task tracking
                task.update_sub_task_result(result.correlation_id, result.data)
                
                # Continue or complete task
                if result.success:
                    await task.complete({"status": "paid"})
                else:
                    await task.complete({"status": "payment_failed"})
        """
        if not self._context:
            raise RuntimeError("ResultContext.restore_task() requires a PlatformContext")
        task_data = await self._context.memory.get_task_by_subtask(
            self.correlation_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )
        if not task_data:
            raise ValueError(f"No task context found for sub-task {self.correlation_id}")
        return TaskContext.from_memory(
            task_data,
            self._context,
            register_produced_event=self._register_produced_event,
        )
