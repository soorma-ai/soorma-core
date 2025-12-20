import pytest
import asyncio
from src.adapters.memory_adapter import MemoryAdapter

@pytest.mark.asyncio
async def test_queue_group_distribution():
    """Test that messages are distributed round-robin within a queue group."""
    adapter = MemoryAdapter()
    await adapter.connect()
    
    received_a = []
    received_b = []
    received_c = []
    
    async def handler_a(topic, msg):
        received_a.append(msg)
        
    async def handler_b(topic, msg):
        received_b.append(msg)
        
    async def handler_c(topic, msg):
        received_c.append(msg)
        
    # Subscribe 3 handlers to the same topic with the same queue group
    await adapter.subscribe(["test.topic"], handler_a, queue_group="group1")
    await adapter.subscribe(["test.topic"], handler_b, queue_group="group1")
    await adapter.subscribe(["test.topic"], handler_c, queue_group="group1")
    
    # Publish 3 messages
    await adapter.publish("test.topic", {"id": 1})
    await adapter.publish("test.topic", {"id": 2})
    await adapter.publish("test.topic", {"id": 3})
    
    # Each handler should have received exactly one message (ideal round-robin)
    # Note: The implementation uses modulo on matching subs.
    # Since all 3 match, it should be perfect round robin.
    
    assert len(received_a) + len(received_b) + len(received_c) == 3
    
    # Verify distribution (each gets 1)
    assert len(received_a) == 1
    assert len(received_b) == 1
    assert len(received_c) == 1
    
    await adapter.disconnect()

@pytest.mark.asyncio
async def test_mixed_broadcast_and_queue_group():
    """Test mixing broadcast subscribers and queue groups."""
    adapter = MemoryAdapter()
    await adapter.connect()
    
    broadcast_msgs = []
    group_msgs_1 = []
    group_msgs_2 = []
    
    async def handler_broadcast(topic, msg):
        broadcast_msgs.append(msg)
        
    async def handler_group_1(topic, msg):
        group_msgs_1.append(msg)
        
    async def handler_group_2(topic, msg):
        group_msgs_2.append(msg)
        
    # 1. Broadcast subscriber (no queue group)
    await adapter.subscribe(["test.topic"], handler_broadcast)
    
    # 2. Queue group subscribers
    await adapter.subscribe(["test.topic"], handler_group_1, queue_group="workers")
    await adapter.subscribe(["test.topic"], handler_group_2, queue_group="workers")
    
    # Publish 2 messages
    await adapter.publish("test.topic", {"msg": 1})
    await adapter.publish("test.topic", {"msg": 2})
    
    # Broadcast subscriber gets ALL messages
    assert len(broadcast_msgs) == 2
    
    # Queue group subscribers share messages (total 2 distributed among them)
    assert len(group_msgs_1) + len(group_msgs_2) == 2
    assert len(group_msgs_1) == 1
    assert len(group_msgs_2) == 1
    
    await adapter.disconnect()
