import logging
from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from ...models.schemas import PublishRequest, PublishResponse
from ...services.event_manager import event_manager

router = APIRouter(tags=["Events"])
logger = logging.getLogger(__name__)

@router.post("/publish", response_model=PublishResponse)
async def publish_event(request: PublishRequest) -> PublishResponse:
    """
    Publish an event to the message bus.
    
    The event is validated and forwarded to the configured adapter (NATS, etc.).
    """
    event = request.event
    
    try:
        # Build the message payload
        # Use model_dump to preserve field names (e.g. correlation_id) for SDK compatibility
        # to_cloudevents_dict() converts to strict CloudEvents (lowercase keys) which breaks SDK
        message = event.model_dump(mode='json', exclude_none=True)
        
        # Publish via event manager
        # Ensure we pass the string value of the topic, not the Enum object
        # This prevents "EventTopic.BUSINESS_FACTS" from being used in the subject
        topic_str = event.topic.value if hasattr(event.topic, "value") else str(event.topic)
        await event_manager.publish(topic_str, message)
        
        logger.info(f"Published event {event.id} to topic {topic_str}")
        
        return PublishResponse(
            success=True,
            event_id=event.id,
            message=f"Event published to {topic_str}",
        )
    except RuntimeError as e:
        # Adapter not initialized/connected
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish event: {str(e)}",
        )


@router.get("/stream")
async def stream_events(
    request: Request,
    topics: str = Query(
        ...,
        description="Comma-separated list of topics to subscribe to (supports wildcards)"
    ),
    agent_id: str = Query(
        ...,
        description="ID of the subscribing agent"
    ),
    agent_name: str = Query(
        None,
        description="Name of the agent (used for load balancing queue groups)"
    ),
) -> EventSourceResponse:
    """
    Subscribe to events via Server-Sent Events (SSE).
    """
    # Parse topics
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        raise HTTPException(status_code=400, detail="At least one topic is required")
    
    try:
        return EventSourceResponse(
            event_manager.create_stream(
                topics=topic_list, 
                agent_id=agent_id,
                agent_name=agent_name,
                check_disconnected=request.is_disconnected
            )
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
