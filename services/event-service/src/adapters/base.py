"""
Base adapter interface for event bus backends.

All adapters must implement this interface to ensure consistent behavior
across different message bus implementations (NATS, Kafka, Google Pub/Sub, etc.).
"""
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List

# Type alias for message handlers
MessageHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]


class EventAdapter(ABC):
    """
    Abstract base class for event bus adapters.
    
    This interface defines the contract that all message bus implementations
    must follow. It enables the Event Service to be backend-agnostic.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the message bus.
        
        This method should handle:
        - Initial connection
        - Auto-reconnection logic
        - Connection state management
        
        Raises:
            ConnectionError: If unable to connect to the message bus
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Gracefully disconnect from the message bus.
        
        This method should:
        - Complete any pending operations
        - Unsubscribe from all topics
        - Close the connection cleanly
        """
        pass
    
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic/subject to publish to (e.g., "action-requests")
            message: The message payload (will be JSON serialized)
        
        Raises:
            PublishError: If the message could not be published
            ConnectionError: If not connected to the message bus
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        topics: List[str],
        handler: MessageHandler,
        subscription_id: str | None = None,
    ) -> str:
        """
        Subscribe to one or more topics.
        
        Args:
            topics: List of topics/subjects to subscribe to.
                    Supports wildcards (e.g., "research.*", "events.>")
            handler: Async callback function that receives (topic, message)
            subscription_id: Optional identifier for this subscription
        
        Returns:
            Subscription ID that can be used to unsubscribe
        
        Raises:
            SubscriptionError: If subscription could not be created
            ConnectionError: If not connected to the message bus
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic subscription.
        
        Args:
            subscription_id: The ID returned from subscribe()
        
        Raises:
            ValueError: If subscription_id is not found
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the adapter is connected to the message bus.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @property
    def name(self) -> str:
        """Return the adapter name for logging."""
        return self.__class__.__name__


class AdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class PublishError(AdapterError):
    """Raised when a message could not be published."""
    pass


class SubscriptionError(AdapterError):
    """Raised when a subscription could not be created."""
    pass
