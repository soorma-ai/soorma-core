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
        assert "action.request" in planner.config.events_produced
    
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
        assert "action.request" in worker.config.events_consumed
        assert "action.result" in worker.config.events_produced
    
    def test_on_task_decorator(self):
        """Test task handler registration."""
        from soorma import Worker
        from soorma.agents.worker import TaskContext
        
        worker = Worker(name="test-worker")
        
        @worker.on_task("process_data")
        async def handle_task(task: TaskContext, context):
            return {"processed": True}
        
        assert "process_data" in worker._task_handlers
        assert "process_data" in worker.capabilities
    
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
        assert "tool.request" in tool.config.events_consumed
        assert "tool.response" in tool.config.events_produced
    
    def test_on_invoke_decorator(self):
        """Test operation handler registration."""
        from soorma import Tool
        from soorma.agents.tool import ToolRequest
        
        tool = Tool(name="test-tool")
        
        @tool.on_invoke("calculate")
        async def calculate(request: ToolRequest, context):
            return {"result": 42}
        
        assert "calculate" in tool._operation_handlers
        assert "calculate" in tool.capabilities
    
    def test_should_handle_request_by_name(self):
        """Test request matching by tool name."""
        from soorma import Tool
        
        tool = Tool(name="my-tool", capabilities=["op_a"])
        
        assert tool._should_handle_request("my-tool") is True
        assert tool._should_handle_request("other-tool") is False
    
    def test_should_handle_request_by_capability(self):
        """Test request matching by capability."""
        from soorma import Tool
        
        tool = Tool(name="my-tool", capabilities=["op_a", "op_b"])
        
        assert tool._should_handle_request("op_a") is True
        assert tool._should_handle_request("op_b") is True
        assert tool._should_handle_request("op_c") is False


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
            task_name="process_data",
            plan_id="plan-456",
            goal_id="goal-789",
            data={"input": "test"},
        )
        
        assert task.task_id == "task-123"
        assert task.task_name == "process_data"
        assert task.data["input"] == "test"
    
    def test_tool_request_creation(self):
        """Test creating a ToolRequest."""
        from soorma import ToolRequest
        
        request = ToolRequest(
            operation="calculate",
            data={"expression": "2 + 2"},
        )
        
        assert request.operation == "calculate"
        assert request.data["expression"] == "2 + 2"
        assert request.request_id is not None
