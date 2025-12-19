"""
Event Service Adapters

This package provides the adapter pattern implementation for different
message bus backends (NATS, Google Pub/Sub, Kafka, In-Memory).
"""
from .base import EventAdapter
from .nats_adapter import NatsAdapter
from .memory_adapter import MemoryAdapter

__all__ = [
    "EventAdapter",
    "NatsAdapter",
    "MemoryAdapter",
]
