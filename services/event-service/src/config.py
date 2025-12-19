"""
Configuration settings for the Event Service.
"""
from typing import Literal
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Event Service configuration loaded from environment variables.
    """
    model_config = ConfigDict(
        env_prefix="",
        env_file=".env",
        case_sensitive=False,
    )
    
    # Service settings
    service_name: str = "event-service"
    service_port: int = 8082
    debug: bool = False
    
    # Adapter configuration
    event_adapter: Literal["nats", "memory", "pubsub", "kafka"] = "nats"
    
    # NATS settings
    nats_url: str = "nats://localhost:4222"
    nats_reconnect_time_wait: int = 2  # seconds
    nats_max_reconnect_attempts: int = -1  # -1 = infinite
    
    # Google Pub/Sub settings (for pubsub adapter)
    gcp_project_id: str | None = None
    
    # Kafka settings (for kafka adapter)
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Redis settings (for distributed subscription state)
    redis_url: str | None = None
    
    # Stream settings
    stream_heartbeat_interval: int = 15  # seconds
    stream_max_queue_size: int = 1000


# Global settings instance
settings = Settings()
