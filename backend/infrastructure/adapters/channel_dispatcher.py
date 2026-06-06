"""
Channel Dispatcher
Phase 5: Routes messages from channels to appropriate handlers
"""
from typing import Callable

from backend.domain.ports.ichannel import IChannelAdapter, InboundMessage, OutboundMessage


class ChannelDispatcher:
    """
    Central dispatcher for all channel adapters.
    Routes inbound messages to the message handler.
    """

    def __init__(self):
        self._adapters: dict[str, IChannelAdapter] = {}
        self._handler: Callable[[InboundMessage], None] | None = None

    def register_adapter(self, adapter: IChannelAdapter) -> None:
        """Register a channel adapter"""
        self._adapters[adapter.channel_type] = adapter

        # Set up message handler on the adapter
        adapter.on_message(self._handle_inbound)

    def set_handler(self, handler: Callable[[InboundMessage], None]) -> None:
        """Set the message handler for all channels"""
        self._handler = handler

    def _handle_inbound(self, message: InboundMessage) -> None:
        """Internal handler that routes messages to the main handler"""
        if self._handler:
            self._handler(message)

    async def send_to_channel(
        self,
        channel_type: str,
        channel_id: str,
        message: str,
        reply_to: str | None = None,
    ) -> bool:
        """Send message to a specific channel"""
        adapter = self._adapters.get(channel_type)
        if not adapter:
            return False

        outbound = OutboundMessage(
            channel_id=channel_id,
            message=message,
            reply_to=reply_to,
        )
        return await adapter.send(outbound)

    async def start_all(self) -> None:
        """Start all registered adapters"""
        for adapter in self._adapters.values():
            await adapter.start()

    async def stop_all(self) -> None:
        """Stop all registered adapters"""
        for adapter in self._adapters.values():
            await adapter.stop()

    def list_channels(self) -> list[str]:
        """List all registered channel types"""
        return list(self._adapters.keys())
