"""
Channel Adapter Interface
Phase 5: Multi-channel support
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class InboundMessage:
    """Message received from a channel"""
    channel_type: str  # slack, telegram, discord
    channel_id: str
    account_id: str
    message: str
    timestamp: str
    metadata: dict[str, Any]


@dataclass
class OutboundMessage:
    """Message to send to a channel"""
    channel_id: str
    message: str
    reply_to: str | None = None  # Message ID to reply to


class IChannelAdapter(ABC):
    """Interface for channel adapters"""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return channel type: slack, telegram, discord"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter"""
        pass

    @abstractmethod
    async def send(self, outbound: OutboundMessage) -> bool:
        """Send message to channel"""
        pass

    @abstractmethod
    def on_message(self, handler) -> None:
        """Set message handler callback"""
        pass
