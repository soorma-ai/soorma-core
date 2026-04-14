"""
Tests for the Agent base classes (Planner, Worker, Tool).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentBase:
    """Tests for the base Agent class."""
    
    def test_agent_creation(self):
        """Test creating a basic agent."""
        from soorma import Agent
        
        agent = Agent(
            name="test-agent",
            description="A test agent",
            version="1.0.0",
            capabilities=["test_capability"],
        )
        
        assert agent.name == "test-agent"
        assert agent.description == "A test agent"
        assert agent.version == "1.0.0"
        assert "test_capability" in agent.capabilities
    
    def test_agent_id_auto_generated(self):
        """Test that agent ID is auto-generated."""
        from soorma import Agent
        
        agent = Agent(name="test-agent")
        
        assert agent.agent_id.startswith("test-agent-")
        assert len(agent.agent_id) > len("test-agent-")
    
    def test_agent_id_custom(self):
        """Test setting a custom agent ID."""
        from soorma import Agent
        
        agent = Agent(name="test-agent", agent_id="my-custom-id")
        
        assert agent.agent_id == "my-custom-id"
    
    def test_on_event_decorator(self):
        """Test event handler registration."""
        from soorma import Agent
        from soorma_common.events import EventTopic
        
        agent = Agent(name="test-agent")
        
        @agent.on_event("test.event", topic=EventTopic.BUSINESS_FACTS)
        async def handler(event, context):
            pass
        
        assert "business-facts:test.event" in agent._event_handlers
        assert "test.event" in agent.config.events_consumed
    
    def test_on_startup_decorator(self):
        """Test startup handler registration."""
        from soorma import Agent
        
        agent = Agent(name="test-agent")
        
        @agent.on_startup
        async def startup():
            pass
        
        assert startup in agent._startup_handlers
    
    def test_on_shutdown_decorator(self):
        """Test shutdown handler registration."""
        from soorma import Agent
        
        agent = Agent(name="test-agent")
        
        @agent.on_shutdown
        async def shutdown():
            pass
        
        assert shutdown in agent._shutdown_handlers


class TestPlanner:
    """Tests for the Planner class."""
    
    def test_planner_creation(self):
        """Test creating a planner."""
        from soorma import Planner
        
        planner = Planner(
            name="test-planner",
            description="A test planner",
            capabilities=["planning", "decomposition"],
        )
        
        assert planner.name == "test-planner"
        assert planner.config.agent_type == "planner"
        assert "planning" in planner.capabilities
        assert "action.request" not in planner.config.events_produced
    
    def test_on_goal_decorator(self):
        """Test goal handler registration."""
        from soorma import Planner
        from soorma.agents.planner import Goal, Plan, Task
        
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal: Goal, context):
            return Plan(
                goal=goal,
                tasks=[
                    Task(name="search", assigned_to="researcher"),
                ],
            )
        
        assert "research.goal" in planner._goal_handlers
        # Goal type should be registered as consumed event
        assert "research.goal" in planner.config.events_consumed


class TestWorker:
    """Tests for the Worker class."""
    
    def test_worker_creation(self):
        """Test creating a worker."""
        from soorma import Worker
        
        worker = Worker(
            name="test-worker",
            description="A test worker",
            capabilities=["data_processing"],
        )
        
        assert worker.name == "test-worker"
        assert worker.config.agent_type == "worker"
        assert "data_processing" in worker.capabilities
        assert "action.request" not in worker.config.events_consumed
        assert "action.result" not in worker.config.events_produced
    
    def test_on_task_decorator(self):
        """Test task handler registration."""
        from soorma import Worker, TaskContext
        
        worker = Worker(name="test-worker")
        
        @worker.on_task("process.data.requested")
        async def handle_task(task: TaskContext, context):
            return {"processed": True}
        
        assert "process.data.requested" in worker._task_handlers
        assert "process.data.requested" in worker.capabilities
    
    def test_should_handle_task_by_name(self):
        """Test task matching by worker name."""
        from soorma import Worker
        
        worker = Worker(name="my-worker", capabilities=["task_a"])
        
        assert worker._should_handle_task("my-worker") is True
        assert worker._should_handle_task("other-worker") is False
    
    def test_should_handle_task_by_capability(self):
        """Test task matching by capability."""
        from soorma import Worker
        
        worker = Worker(name="my-worker", capabilities=["task_a", "task_b"])
        
        assert worker._should_handle_task("task_a") is True
        assert worker._should_handle_task("task_b") is True
        assert worker._should_handle_task("task_c") is False


class TestTool:
    """Tests for the Tool class."""
    
    def test_tool_creation(self):
        """Test creating a tool."""
        from soorma import Tool
        
        tool = Tool(
            name="calculator-tool",
            description="Performs calculations",
            capabilities=["arithmetic", "conversion"],
        )
        
        assert tool.name == "calculator-tool"
        assert tool.config.agent_type == "tool"
        assert "arithmetic" in tool.capabilities
        # Tools do NOT have topic names in events lists (only actual event types)
        assert "action-requests" not in tool.config.events_consumed
        assert "action-results" not in tool.config.events_produced
    
    def test_on_invoke_decorator(self):
        """Test operation handler registration."""
        from soorma import Tool
        from soorma.agents.tool import InvocationContext
        
        tool = Tool(name="test-tool")
        
        @tool.on_invoke("calculate")
        async def calculate(request: InvocationContext, context):
            return {"result": 42}
        
        assert "calculate" in tool._operation_handlers
        assert "calculate" in tool.capabilities
    
    def test_should_handle_request_by_name(self):
        """Test request matching by name."""
        from soorma import Tool
        
        tool = Tool(name="my-tool", capabilities=["op_a"])
        
        # Tool now uses on_invoke() for handler registration
        @tool.on_invoke("op_a")
        async def handle_op_a(request, context):
            return {}
        
        # Verify handler is registered
        assert "op_a" in tool._operation_handlers
    
    def test_should_handle_request_by_capability(self):
        """Test request matching by capability."""
        from soorma import Tool
        
        tool = Tool(name="my-tool", capabilities=["op_a", "op_b"])
        
        @tool.on_invoke("op_a")
        async def handle_a(request, context):
            return {}
        
        @tool.on_invoke("op_b")
        async def handle_b(request, context):
            return {}
        
        # Verify both handlers are registered
        assert "op_a" in tool._operation_handlers
        assert "op_b" in tool._operation_handlers


class TestPlatformContext:
    """Tests for the PlatformContext class."""
    
    def test_context_creation(self):
        """Test creating a platform context."""
        from soorma import PlatformContext
        
        context = PlatformContext()
        
        assert context.registry is not None
        assert context.memory is not None
        assert context.bus is not None
        assert context.tracker is not None
    
    def test_context_from_env(self):
        """Test creating context from environment variables."""
        from soorma import PlatformContext
        import os
        
        with patch.dict(os.environ, {
            "SOORMA_REGISTRY_URL": "http://registry:8081",
            "SOORMA_EVENT_SERVICE_URL": "http://events:8082",
            "SOORMA_MEMORY_URL": "http://memory:8083",
            "SOORMA_TRACKER_URL": "http://tracker:8084",
        }):
            context = PlatformContext.from_env()
            
            assert context.registry.base_url == "http://registry:8081"
            assert context.memory.base_url == "http://memory:8083"
            assert context.tracker.base_url == "http://tracker:8084"

    def test_set_auth_token_propagates_to_wrappers(self):
        """Injected bearer token should be available to memory/tracker wrappers."""
        from soorma import PlatformContext

        context = PlatformContext()
        context.set_auth_token("jwt-token-value")

        assert context.memory.auth_token == "jwt-token-value"
        assert context.tracker.auth_token == "jwt-token-value"


class TestDataClasses:
    """Tests for data classes (Goal, Plan, Task, etc.)."""
    
    def test_goal_creation(self):
        """Test creating a Goal."""
        from soorma import Goal
        
        goal = Goal(
            goal_type="research.goal",
            data={"topic": "AI safety"},
        )
        
        assert goal.goal_type == "research.goal"
        assert goal.data["topic"] == "AI safety"
        assert goal.goal_id is not None
    
    def test_task_creation(self):
        """Test creating a Task."""
        from soorma import Task
        
        task = Task(
            name="search_papers",
            assigned_to="research-worker",
            data={"query": "transformer architectures"},
            depends_on=["fetch_references"],
        )
        
        assert task.name == "search_papers"
        assert task.assigned_to == "research-worker"
        assert task.task_id is not None
        assert "fetch_references" in task.depends_on
    
    def test_plan_creation(self):
        """Test creating a Plan."""
        from soorma import Goal, Plan, Task
        
        goal = Goal(goal_type="test.goal", data={})
        tasks = [
            Task(name="task1", assigned_to="worker1"),
            Task(name="task2", assigned_to="worker2", depends_on=["task1"]),
        ]
        
        plan = Plan(goal=goal, tasks=tasks)
        
        assert plan.goal == goal
        assert len(plan.tasks) == 2
        assert plan.plan_id is not None
        assert plan.status == "pending"
    
    def test_task_context_creation(self):
        """Test creating a TaskContext."""
        from soorma import TaskContext
        
        task = TaskContext(
            task_id="task-123",
            event_type="process.data.requested",
            plan_id="plan-456",
            data={"input": "test"},
            response_event="process.data.completed",
            response_topic="action-results",
        )

        assert task.task_id == "task-123"
        assert task.event_type == "process.data.requested"
        assert task.data["input"] == "test"
    
    def test_tool_request_creation(self):
        """Test creating an InvocationContext."""
        from soorma import InvocationContext
        
        request = InvocationContext(
            request_id="req-123",
            event_type="calculate",
            correlation_id="corr-456",
            data={"expression": "2 + 2"},
            response_event="calculate.result",
            response_topic="action-results",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        assert request.event_type == "calculate"
        assert request.data["expression"] == "2 + 2"
        assert request.request_id == "req-123"


class TestAutoSchemaRegistration:
    """Tests for automatic schema registration in _register_with_registry().

    T0 (Phase 5): When an AgentCapability's consumed_event or produced_events
    carry both payload_schema_name AND an inline payload_schema body, the SDK
    must call register_schema() automatically during agent startup — the agent
    code must NOT have to call ctx.registry.register_schema() explicitly.
    """

    def _make_mock_context(self):
        """Create a MagicMock PlatformContext with async registry methods."""
        ctx = MagicMock()
        ctx.registry = AsyncMock()
        ctx.registry.register_schema = AsyncMock()
        ctx.registry.register_agent = AsyncMock()
        ctx.registry.register_event = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_inline_schema_on_consumed_event_is_auto_registered(self):
        """Worker with inline payload_schema body triggers register_schema() at startup."""
        from soorma import Worker
        from soorma_common import AgentCapability, EventDefinition

        worker = Worker(
            name="schema-test-worker",
            agent_id="schema-test-worker-001",
            capabilities=[
                AgentCapability(
                    task_name="web_research",
                    description="Performs web research",
                    consumed_event=EventDefinition(
                        event_name="research.requested",
                        topic="action-requests",
                        description="Research request",
                        payload_schema_name="research_request_v1",
                        payload_schema={
                            "type": "object",
                            "properties": {"topic": {"type": "string"}},
                            "required": ["topic"],
                        },
                    ),
                    produced_events=[],
                )
            ],
        )
        worker._context = self._make_mock_context()

        await worker._register_with_registry()

        # register_schema MUST be called with the inline schema body
        worker._context.registry.register_schema.assert_called_once()
        registered_schema = worker._context.registry.register_schema.call_args.args[0]
        assert registered_schema.schema_name == "research_request_v1"
        assert registered_schema.json_schema["type"] == "object"

    @pytest.mark.asyncio
    async def test_inline_schema_on_produced_event_is_auto_registered(self):
        """Worker with inline schema on a produced_event triggers register_schema()."""
        from soorma import Worker
        from soorma_common import AgentCapability, EventDefinition

        consumed_event = EventDefinition(
            event_name="research.requested",
            topic="action-requests",
            description="Input",
            payload_schema_name="research_request_v1",
        )
        produced_event = EventDefinition(
            event_name="research.completed",
            topic="action-results",
            description="Output",
            payload_schema_name="research_result_v1",
            payload_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        )
        worker = Worker(
            name="schema-test-worker-2",
            agent_id="schema-test-worker-002",
            capabilities=[
                AgentCapability(
                    task_name="web_research",
                    description="Performs web research",
                    consumed_event=consumed_event,
                    produced_events=[produced_event],
                )
            ],
        )
        worker._context = self._make_mock_context()

        await worker._register_with_registry()

        # register_schema called once for the produced_event inline schema
        worker._context.registry.register_schema.assert_called_once()
        registered_schema = worker._context.registry.register_schema.call_args.args[0]
        assert registered_schema.schema_name == "research_result_v1"

    @pytest.mark.asyncio
    async def test_multiple_inline_schemas_all_registered(self):
        """Multiple capabilities with inline schemas each get registered."""
        from soorma import Worker
        from soorma_common import AgentCapability, EventDefinition

        def _cap(task_name: str, event_name: str, schema_name: str) -> AgentCapability:
            return AgentCapability(
                task_name=task_name,
                description=task_name,
                consumed_event=EventDefinition(
                    event_name=event_name,
                    topic="action-requests",
                    description=event_name,
                    payload_schema_name=schema_name,
                    payload_schema={"type": "object", "properties": {}},
                ),
                produced_events=[],
            )

        worker = Worker(
            name="multi-schema-worker",
            agent_id="multi-schema-worker-001",
            capabilities=[
                _cap("task_a", "task_a.requested", "task_a_schema_v1"),
                _cap("task_b", "task_b.requested", "task_b_schema_v1"),
            ],
        )
        worker._context = self._make_mock_context()

        await worker._register_with_registry()

        assert worker._context.registry.register_schema.call_count == 2
        registered_names = {
            call.args[0].schema_name
            for call in worker._context.registry.register_schema.call_args_list
        }
        assert registered_names == {"task_a_schema_v1", "task_b_schema_v1"}

    @pytest.mark.asyncio
    async def test_no_inline_schema_skips_register_schema(self):
        """Capability with only payload_schema_name (no body) does NOT call register_schema."""
        from soorma import Worker
        from soorma_common import AgentCapability, EventDefinition

        worker = Worker(
            name="ref-only-worker",
            agent_id="ref-only-worker-001",
            capabilities=[
                AgentCapability(
                    task_name="ref_task",
                    description="Reference only",
                    consumed_event=EventDefinition(
                        event_name="ref.requested",
                        topic="action-requests",
                        description="Reference only — schema already registered",
                        payload_schema_name="already_registered_schema_v1",
                        # No payload_schema body — schema is pre-registered, reference only
                    ),
                    produced_events=[],
                )
            ],
        )
        worker._context = self._make_mock_context()

        await worker._register_with_registry()

        worker._context.registry.register_schema.assert_not_called()

    @pytest.mark.asyncio
    async def test_schema_registration_failure_does_not_abort_agent_registration(self):
        """A register_schema failure is logged as a warning; agent still registers."""
        from soorma import Worker
        from soorma_common import AgentCapability, EventDefinition

        worker = Worker(
            name="fault-tolerant-worker",
            agent_id="fault-tolerant-worker-001",
            capabilities=[
                AgentCapability(
                    task_name="fault_task",
                    description="Fault test",
                    consumed_event=EventDefinition(
                        event_name="fault.requested",
                        topic="action-requests",
                        description="Fault test",
                        payload_schema_name="fault_schema_v1",
                        payload_schema={"type": "object", "properties": {}},
                    ),
                    produced_events=[],
                )
            ],
        )
        ctx = self._make_mock_context()
        ctx.registry.register_schema = AsyncMock(side_effect=Exception("Registry unavailable"))
        worker._context = ctx

        # Must not raise — failure is non-fatal (same as event/agent registration)
        result = await worker._register_with_registry()

        # Agent registration still proceeds despite schema failure
        worker._context.registry.register_agent.assert_called_once()
        assert result is True
