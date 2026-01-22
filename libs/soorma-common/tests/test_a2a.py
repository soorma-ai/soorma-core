"""Tests for A2A protocol DTOs."""

import pytest
from soorma_common.a2a import (
    A2AAuthType,
    A2AAuthentication,
    A2ASkill,
    A2AAgentCard,
    A2APart,
    A2AMessage,
    A2ATask,
    A2ATaskStatus,
    A2ATaskResponse,
)


def test_a2a_auth_type():
    """Test A2AAuthType enum."""
    assert A2AAuthType.API_KEY == "apiKey"
    assert A2AAuthType.OAUTH2 == "oauth2"
    assert A2AAuthType.NONE == "none"


def test_a2a_authentication():
    """Test A2AAuthentication validation."""
    auth = A2AAuthentication(
        schemes=[A2AAuthType.API_KEY, A2AAuthType.OAUTH2],
        credentials="https://auth.example.com",
    )
    
    assert len(auth.schemes) == 2
    assert A2AAuthType.API_KEY in auth.schemes
    assert auth.credentials == "https://auth.example.com"


def test_a2a_skill():
    """Test A2ASkill validation."""
    skill = A2ASkill(
        id="search",
        name="Web Search",
        description="Search the web",
        tags=["search", "web"],
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}}},
        outputSchema={"type": "array"},
    )
    
    assert skill.id == "search"
    assert skill.name == "Web Search"
    assert len(skill.tags) == 2
    assert skill.inputSchema["type"] == "object"


def test_a2a_agent_card():
    """Test A2AAgentCard validation."""
    card = A2AAgentCard(
        name="Research Agent",
        description="AI research assistant",
        url="https://agent.example.com",
        version="1.0.0",
        provider={"name": "Soorma", "url": "https://soorma.ai"},
        capabilities={"inference": True},
        skills=[
            A2ASkill(
                id="search",
                name="Search",
                description="Search capability",
            )
        ],
        authentication=A2AAuthentication(schemes=[A2AAuthType.API_KEY]),
    )
    
    assert card.name == "Research Agent"
    assert card.url == "https://agent.example.com"
    assert len(card.skills) == 1
    assert card.skills[0].id == "search"


def test_a2a_part_text():
    """Test A2APart with text."""
    part = A2APart(type="text", text="Hello, world!")
    
    assert part.type == "text"
    assert part.text == "Hello, world!"
    assert part.data is None


def test_a2a_part_data():
    """Test A2APart with data."""
    part = A2APart(
        type="data",
        data={"key": "value"},
        mimeType="application/json",
    )
    
    assert part.type == "data"
    assert part.data == {"key": "value"}
    assert part.mimeType == "application/json"


def test_a2a_message():
    """Test A2AMessage validation."""
    message = A2AMessage(
        role="user",
        parts=[
            A2APart(type="text", text="Search for AI trends"),
        ],
    )
    
    assert message.role == "user"
    assert len(message.parts) == 1
    assert message.parts[0].text == "Search for AI trends"


def test_a2a_task():
    """Test A2ATask validation."""
    task = A2ATask(
        id="task-123",
        sessionId="sess-456",
        message=A2AMessage(
            role="user",
            parts=[A2APart(type="text", text="Do something")],
        ),
        metadata={"source": "web"},
    )
    
    assert task.id == "task-123"
    assert task.sessionId == "sess-456"
    assert task.message.role == "user"
    assert task.metadata == {"source": "web"}


def test_a2a_task_status():
    """Test A2ATaskStatus enum."""
    assert A2ATaskStatus.SUBMITTED == "submitted"
    assert A2ATaskStatus.WORKING == "working"
    assert A2ATaskStatus.COMPLETED == "completed"
    assert A2ATaskStatus.FAILED == "failed"


def test_a2a_task_response():
    """Test A2ATaskResponse validation."""
    response = A2ATaskResponse(
        id="task-123",
        sessionId="sess-456",
        status=A2ATaskStatus.COMPLETED,
        message=A2AMessage(
            role="agent",
            parts=[A2APart(type="text", text="Task completed")],
        ),
    )
    
    assert response.id == "task-123"
    assert response.status == A2ATaskStatus.COMPLETED
    assert response.message.role == "agent"
    assert response.error is None


def test_a2a_task_response_error():
    """Test A2ATaskResponse with error."""
    response = A2ATaskResponse(
        id="task-123",
        status=A2ATaskStatus.FAILED,
        error="Something went wrong",
    )
    
    assert response.status == A2ATaskStatus.FAILED
    assert response.error == "Something went wrong"
    assert response.message is None
