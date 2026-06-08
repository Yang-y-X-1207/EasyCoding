"""
MessageBus
Asyncio-based message bus for decoupling channel adapters and agents
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class InboundMessage:
    """Inbound message from channel to agent"""
    id: str
    channel: str           # slack, telegram, discord, http
    sender_id: str         # User ID
    content: str           # Message content
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.NORMAL

    def __post_init__(self):
        if not self.id:
            from uuid import uuid4
            self.id = str(uuid4())


@dataclass
class OutboundMessage:
    """Outbound message from agent to channel"""
    id: str
    channel: str           # Target channel
    recipient_id: str      # User ID
    content: str           # Message content
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.NORMAL

    def __post_init__(self):
        if not self.id:
            from uuid import uuid4
            self.id = str(uuid4())


@dataclass
class ToolMessage:
    """Tool execution message"""
    id: str
    tool_name: str
    params: dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MessageBus:
    """
    Async message bus with separate inbound/outbound queues.
    Decouples channel adapters from agent processing.
    """

    def __init__(self):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._tools: asyncio.Queue[ToolMessage] = asyncio.Queue()

        # Subscribers for pub/sub pattern
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

        # Metrics
        self._messages_processed = 0
        self._start_time = datetime.utcnow()

    def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish an inbound message"""
        self._inbound.put_nowait(msg)
        self._messages_processed += 1
        logger.debug(f"Inbound message: {msg.id} from {msg.channel}:{msg.sender_id}")

    async def consume_inbound(self, timeout: float = 1.0) -> Optional[InboundMessage]:
        """
        Consume an inbound message with timeout.
        Returns None if timeout expires (allows periodic checks).
        """
        try:
            msg = await asyncio.wait_for(self._inbound.get(), timeout=timeout)
            return msg
        except asyncio.TimeoutError:
            return None

    def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish an outbound message"""
        self._outbound.put_nowait(msg)
        logger.debug(f"Outbound message: {msg.id} to {msg.channel}:{msg.recipient_id}")

    async def consume_outbound(self, timeout: float = 1.0) -> Optional[OutboundMessage]:
        """Consume an outbound message with timeout"""
        try:
            msg = await asyncio.wait_for(self._outbound.get(), timeout=timeout)
            return msg
        except asyncio.TimeoutError:
            return None

    def publish_tool(self, msg: ToolMessage) -> None:
        """Publish a tool execution message"""
        self._tools.put_nowait(msg)
        logger.debug(f"Tool message: {msg.id} {msg.tool_name}")

    async def consume_tool(self, timeout: float = 1.0) -> Optional[ToolMessage]:
        """Consume a tool message with timeout"""
        try:
            msg = await asyncio.wait_for(self._tools.get(), timeout=timeout)
            return msg
        except asyncio.TimeoutError:
            return None

    def subscribe(self, topic: str) -> asyncio.Queue:
        """
        Subscribe to a topic and receive a queue for messages.
        Used for pub/sub pattern (e.g., workspace events).
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        queue = asyncio.Queue()
        self._subscribers[topic].append(queue)
        return queue

    def unsubscribe(self, topic: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from a topic"""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(queue)
            except ValueError:
                pass

    async def publish_event(self, topic: str, data: Any) -> None:
        """Publish an event to all subscribers of a topic"""
        if topic in self._subscribers:
            for queue in self._subscribers[topic]:
                await queue.put(data)

    def get_stats(self) -> dict:
        """Get bus statistics"""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        return {
            "messages_processed": self._messages_processed,
            "inbound_queue_size": self._inbound.qsize(),
            "outbound_queue_size": self._outbound.qsize(),
            "tool_queue_size": self._tools.qsize(),
            "uptime_seconds": uptime,
        }

    async def drain_inbound(self) -> list[InboundMessage]:
        """Drain all pending inbound messages (for shutdown)"""
        messages = []
        while not self._inbound.empty():
            try:
                msg = self._inbound.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break
        return messages