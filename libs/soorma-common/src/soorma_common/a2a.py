"""
A2A (Agent-to-Agent) protocol DTOs for external agent compatibility.

Ref: https://google.github.io/agent-to-agent/
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum


class A2AAuthType(str, Enum):
    """A2A authentication types."""
    
    API_KEY = "apiKey"
    OAUTH2 = "oauth2"
    NONE = "none"


class A2AAuthentication(BaseModel):
    """A2A authentication configuration."""
    
    schemes: List[A2AAuthType]
    credentials: Optional[str] = None  # URL for OAuth discovery


class A2ASkill(BaseModel):
    """A2A Skill - maps to our AgentCapability."""
    
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    inputSchema: Optional[Dict[str, Any]] = None  # JSON Schema
    outputSchema: Optional[Dict[str, Any]] = None  # JSON Schema


class A2AAgentCard(BaseModel):
    """
    A2A Agent Card - industry standard for agent discovery.
    
    Ref: https://google.github.io/agent-to-agent/
    """
    
    name: str
    description: str
    url: str  # Gateway URL for this agent
    version: str = "1.0.0"
    provider: Dict[str, str] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    skills: List[A2ASkill] = Field(default_factory=list)
    authentication: A2AAuthentication


class A2APart(BaseModel):
    """Part of an A2A message."""
    
    type: Literal["text", "data", "file"]
    text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    mimeType: Optional[str] = None


class A2AMessage(BaseModel):
    """A2A Message in a task."""
    
    role: Literal["user", "agent"]
    parts: List[A2APart]


class A2ATask(BaseModel):
    """A2A Task - standard task format for external requests."""
    
    id: str
    sessionId: Optional[str] = None
    message: A2AMessage
    metadata: Optional[Dict[str, Any]] = None


class A2ATaskStatus(str, Enum):
    """A2A task status."""
    
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class A2ATaskResponse(BaseModel):
    """A2A Task Response."""
    
    id: str
    sessionId: Optional[str] = None
    status: A2ATaskStatus
    message: Optional[A2AMessage] = None
    error: Optional[str] = None
