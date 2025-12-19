"""
Database models for registry service.
"""

from .base import Base
from .event import EventTable
from .agent import AgentTable, AgentCapabilityTable

__all__ = [
    "Base",
    "EventTable",
    "AgentTable",
    "AgentCapabilityTable",
]
