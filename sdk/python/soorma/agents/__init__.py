"""
Soorma Agents Module.

This module provides the base Agent class and the DisCo "Trinity":
- Planner: Strategic reasoning engine that breaks goals into tasks
- Worker: Domain-specific cognitive node that executes tasks
- Tool: Atomic, stateless capability for specific operations

All three extend the base Agent class but provide specialized interfaces
for their respective roles in the DisCo architecture.
"""
from .base import Agent
from .planner import Planner
from .worker import Worker
from .tool import Tool

__all__ = ["Agent", "Planner", "Worker", "Tool"]
