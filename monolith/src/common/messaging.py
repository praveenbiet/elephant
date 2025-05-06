import json
import logging
import asyncio
from typing import Dict, Any, List, Callable, Awaitable, Optional, Union
from datetime import datetime
import uuid

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
from pydantic import BaseModel, ValidationError

from src.common.config import get_settings
from src.common.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class EventBase(BaseModel):
    """Base class for all events."""
    event_id: str = ""
    event_type: str
    event_version: str = "1.0"
    event_time: str = ""
    producer: str
    data: Dict[str, Any]

    def __init__(self, **data: Any):
        if "event_id" not in data:
            data["event_id"] = str(uuid.uuid4())
        if "event_time" not in data:
            data["event_time"] = datetime.utcnow().isoformat()
        super().__init__(**data)

class EventPublisher:
    """
    Publishes events to Kafka topics.
    """
    def __init__(self):
        self._producer = None
        self._is_ready = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the Kafka producer."""
        if self._is_ready:
            return
            
        async with self._init_lock:
            if self._is_ready:
                return
                
            try:
                logger.info("Initializing Kafka producer")
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await self._producer.start()
                self._is_ready = True
                logger.info("Kafka producer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {str(e)}", exc_info=True)
                raise

    async def publish_event(
        self, 
        topic: str, 
        event: Union[EventBase, Dict[str, Any]],
        key: Optional[str] = None
    ) -> None:
        """
        Publish an event to a Kafka topic.
        
        Args:
            topic: The Kafka topic to publish to
            event: The event to publish, either as EventBase or dict
            key: Optional key for the message
        """
        if not self._is_ready:
            await self.initialize()
            
        try:
            # Convert EventBase to dict if needed
            if isinstance(event, EventBase):
                event_data = event.dict()
            else:
                event_data = event
                
            # Encode key if provided
            encoded_key = key.encode('utf-8') if key else None
            
            # Send message
            logger.debug(
                f"Publishing event to topic: {topic}",
                extra={"props": {"topic": topic, "event_type": event_data.get("event_type")}}
            )
            
            await self._producer.send_and_wait(
                topic=topic,
                value=event_data,
                key=encoded_key
            )
            
            logger.debug(
                f"Event published successfully to topic: {topic}",
                extra={"props": {"topic": topic, "event_id": event_data.get("event_id")}}
            )
        except KafkaError as e:
            logger.error(
                f"Failed to publish event to Kafka topic {topic}: {str(e)}",
                extra={"props": {"topic": topic}},
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error publishing event to topic {topic}: {str(e)}",
                extra={"props": {"topic": topic}},
                exc_info=True
            )
            raise

    async def close(self) -> None:
        """Close the Kafka producer."""
        if self._producer and self._is_ready:
            try:
                await self._producer.stop()
                self._is_ready = False
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {str(e)}", exc_info=True)

# Singleton instance
event_publisher = EventPublisher()

class EventConsumer:
    """
    Consumes events from Kafka topics.
    """
    def __init__(
        self, 
        topics: List[str],
        group_id: str,
        event_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]],
        auto_offset_reset: str = "earliest"
    ):
        self.topics = topics
        self.group_id = group_id
        self.event_handlers = event_handlers
        self.auto_offset_reset = auto_offset_reset
        self._consumer = None
        self._is_running = False
        self._consumer_task = None

    async def initialize(self) -> None:
        """Initialize the Kafka consumer."""
        try:
            logger.info(
                f"Initializing Kafka consumer for topics: {', '.join(self.topics)}",
                extra={"props": {"topics": self.topics, "group_id": self.group_id}}
            )
            
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            await self._consumer.start()
            logger.info("Kafka consumer initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize Kafka consumer: {str(e)}",
                extra={"props": {"topics": self.topics, "group_id": self.group_id}},
                exc_info=True
            )
            raise

    async def start_consuming(self) -> None:
        """Start consuming events from Kafka."""
        if self._is_running:
            return
            
        await self.initialize()
        self._is_running = True
        self._consumer_task = asyncio.create_task(self._consume_events())
        
        logger.info("Event consumer started")

    async def _consume_events(self) -> None:
        """Consume events from Kafka and process them."""
        try:
            async for message in self._consumer:
                try:
                    event_data = message.value
                    event_type = event_data.get("event_type")
                    
                    if event_type in self.event_handlers:
                        handler = self.event_handlers[event_type]
                        
                        logger.debug(
                            f"Processing event: {event_type}",
                            extra={
                                "props": {
                                    "event_id": event_data.get("event_id"),
                                    "event_type": event_type,
                                    "topic": message.topic,
                                    "partition": message.partition,
                                    "offset": message.offset
                                }
                            }
                        )
                        
                        # Process event
                        await handler(event_data)
                        
                        logger.debug(
                            f"Event processed successfully: {event_type}",
                            extra={"props": {"event_id": event_data.get("event_id")}}
                        )
                    else:
                        logger.warning(
                            f"No handler registered for event type: {event_type}",
                            extra={
                                "props": {
                                    "event_id": event_data.get("event_id"),
                                    "event_type": event_type,
                                    "available_handlers": list(self.event_handlers.keys())
                                }
                            }
                        )
                        
                except ValidationError as e:
                    logger.error(
                        f"Invalid event data format: {str(e)}",
                        extra={"props": {"topic": message.topic, "error": str(e)}},
                        exc_info=True
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing event: {str(e)}",
                        extra={"props": {"topic": message.topic}},
                        exc_info=True
                    )
        except KafkaError as e:
            logger.error(
                f"Kafka consumer error: {str(e)}",
                extra={"props": {"topics": self.topics}},
                exc_info=True
            )
            self._is_running = False
            raise
        except asyncio.CancelledError:
            logger.info("Event consumer task cancelled")
            self._is_running = False
        except Exception as e:
            logger.error(
                f"Unexpected error in event consumer: {str(e)}",
                extra={"props": {"topics": self.topics}},
                exc_info=True
            )
            self._is_running = False
            raise

    async def stop(self) -> None:
        """Stop consuming events and close the consumer."""
        if not self._is_running:
            return
            
        try:
            self._is_running = False
            if self._consumer_task:
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass
                
            if self._consumer:
                await self._consumer.stop()
                
            logger.info("Event consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping event consumer: {str(e)}", exc_info=True)
