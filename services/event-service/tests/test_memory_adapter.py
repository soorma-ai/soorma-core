"""
Tests for the Memory Adapter.
"""
import pytest
from src.adapters.memory_adapter import MemoryAdapter


@pytest.fixture
async def adapter():
    """Create and connect a memory adapter for testing."""
    adapter = MemoryAdapter()
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


class TestMemoryAdapter:
    """Tests for MemoryAdapter."""
    
    async def test_connect_disconnect(self):
        """Test basic connect/disconnect lifecycle."""
        adapter = MemoryAdapter()
        
        assert not adapter.is_connected
        
        await adapter.connect()
        assert adapter.is_connected
        
        await adapter.disconnect()
        assert not adapter.is_connected
    
    async def test_publish_without_subscribers(self, adapter):
        """Test publishing to a topic with no subscribers."""
        # Should not raise an error
        await adapter.publish("test-topic", {"key": "value"})
    
    async def test_subscribe_and_receive(self, adapter):
        """Test subscribing to a topic and receiving messages."""
        received = []
        
        async def handler(topic, message):
            received.append({"topic": topic, "message": message})
        
        sub_id = await adapter.subscribe(["test-topic"], handler)
        assert sub_id is not None
        
        # Publish a message
        await adapter.publish("test-topic", {"key": "value"})
        
        # Check message was received
        assert len(received) == 1
        assert received[0]["topic"] == "test-topic"
        assert received[0]["message"] == {"key": "value"}
    
    async def test_unsubscribe(self, adapter):
        """Test unsubscribing stops message delivery."""
        received = []
        
        async def handler(topic, message):
            received.append(message)
        
        sub_id = await adapter.subscribe(["test-topic"], handler)
        
        # Publish before unsubscribe
        await adapter.publish("test-topic", {"msg": 1})
        assert len(received) == 1
        
        # Unsubscribe
        await adapter.unsubscribe(sub_id)
        
        # Publish after unsubscribe
        await adapter.publish("test-topic", {"msg": 2})
        
        # Should not receive second message
        assert len(received) == 1
    
    async def test_wildcard_star_matching(self, adapter):
        """Test single-segment wildcard (*) matching."""
        received = []
        
        async def handler(topic, message):
            received.append(topic)
        
        await adapter.subscribe(["research.*"], handler)
        
        # Should match
        await adapter.publish("research.requested", {"test": 1})
        await adapter.publish("research.completed", {"test": 2})
        
        # Should NOT match
        await adapter.publish("billing.event", {"test": 3})
        await adapter.publish("research.sub.topic", {"test": 4})  # Too many segments
        
        assert len(received) == 2
        assert "research.requested" in received
        assert "research.completed" in received
    
    async def test_wildcard_gt_matching(self, adapter):
        """Test multi-segment wildcard (>) matching."""
        received = []
        
        async def handler(topic, message):
            received.append(topic)
        
        await adapter.subscribe(["events.>"], handler)
        
        # Should match - any depth
        await adapter.publish("events.a", {"test": 1})
        await adapter.publish("events.a.b", {"test": 2})
        await adapter.publish("events.a.b.c", {"test": 3})
        
        # Should NOT match
        await adapter.publish("other.topic", {"test": 4})
        
        assert len(received) == 3
    
    async def test_exact_match(self, adapter):
        """Test exact topic matching."""
        received = []
        
        async def handler(topic, message):
            received.append(topic)
        
        await adapter.subscribe(["exact.topic.name"], handler)
        
        # Should match only exact topic
        await adapter.publish("exact.topic.name", {"test": 1})
        await adapter.publish("exact.topic", {"test": 2})
        await adapter.publish("exact.topic.name.extra", {"test": 3})
        
        assert len(received) == 1
        assert received[0] == "exact.topic.name"
    
    async def test_multiple_topics(self, adapter):
        """Test subscribing to multiple topics."""
        received = []
        
        async def handler(topic, message):
            received.append(topic)
        
        await adapter.subscribe(["topic.a", "topic.b"], handler)
        
        await adapter.publish("topic.a", {"test": 1})
        await adapter.publish("topic.b", {"test": 2})
        await adapter.publish("topic.c", {"test": 3})
        
        assert len(received) == 2
        assert "topic.a" in received
        assert "topic.b" in received
    
    async def test_multiple_subscribers(self, adapter):
        """Test multiple subscribers to the same topic."""
        received_a = []
        received_b = []
        
        async def handler_a(topic, message):
            received_a.append(message)
        
        async def handler_b(topic, message):
            received_b.append(message)
        
        await adapter.subscribe(["test-topic"], handler_a)
        await adapter.subscribe(["test-topic"], handler_b)
        
        await adapter.publish("test-topic", {"key": "value"})
        
        # Both handlers should receive the message
        assert len(received_a) == 1
        assert len(received_b) == 1
    
    async def test_handler_error_isolation(self, adapter):
        """Test that handler errors don't affect other handlers."""
        received = []
        
        async def failing_handler(topic, message):
            raise ValueError("Handler error")
        
        async def working_handler(topic, message):
            received.append(message)
        
        await adapter.subscribe(["test-topic"], failing_handler, "failing")
        await adapter.subscribe(["test-topic"], working_handler, "working")
        
        # Should not raise, working handler should still receive
        await adapter.publish("test-topic", {"test": 1})
        
        assert len(received) == 1
