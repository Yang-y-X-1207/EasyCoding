"""
Discord Adapter
Phase 5: Discord Bot Gateway integration
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from backend.domain.ports.ichannel import IChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


@dataclass
class DiscordMessage:
    """Discord message structure"""
    channel_id: str
    guild_id: str
    author_id: str
    author_name: str
    content: str
    message_id: str
    timestamp: str


class DiscordAdapter(IChannelAdapter):
    """
    Discord adapter using Gateway API.
    Requires DISCORD_BOT_TOKEN.
    """

    def __init__(self, bot_token: str, intents: int = 513):  # GUILD_MESSAGES + MESSAGE_CONTENT
        self._bot_token = bot_token
        self._intents = intents
        self._handler = None
        self._ws = None
        self._session_id = None
        self._sequence = None
        self._running = False

    @property
    def channel_type(self) -> str:
        return "discord"

    async def start(self) -> None:
        """Start Discord Gateway connection"""
        self._running = True
        asyncio.create_task(self._gateway_loop())
        logger.info("Discord adapter started")

    async def stop(self) -> None:
        """Stop Discord connection"""
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info("Discord adapter stopped")

    async def _gateway_loop(self) -> None:
        """Main gateway event loop"""
        import aiohttp
        import json

        gateway_url = "wss://gateway.discord.gg"
        version = 10

        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        f"{gateway_url}/?v={version}&encoding=json"
                    ) as ws:
                        self._ws = ws

                        # Receive HELLO
                        msg = await ws.receive_json()
                        if msg.get("op") != 10:
                            continue

                        # Send IDENTIFY
                        heartbeat_interval = msg["d"]["heartbeat_interval"] / 1000
                        await ws.send_json({
                            "op": 2,
                            "d": {
                                "token": self._bot_token,
                                "intents": self._intents,
                                "d": {
                                    "properties": {
                                        "os": "windows",
                                        "browser": "coding-cli",
                                        "device": "coding-cli",
                                    }
                                },
                            },
                        })

                        # Send HEARTBEAT
                        await ws.send_json({"op": 6, "d": self._sequence})

                        # Message loop
                        asyncio.create_task(self._heartbeat(heartbeat_interval))

                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.PING:
                                await ws.ping()
                            elif msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.json()
                                self._handle_dispatch(data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Discord gateway error: {e}")
                await asyncio.sleep(5)

    async def _heartbeat(self, interval: float) -> None:
        """Send heartbeats to maintain connection"""
        while self._running:
            await asyncio.sleep(interval)
            if self._ws and self._running:
                try:
                    await self._ws.send_json({"op": 1, "d": self._sequence or 0})
                except Exception:
                    break

    def _handle_dispatch(self, data: dict) -> None:
        """Handle Discord gateway events"""
        op = data.get("op")

        if op == 0:  # DISPATCH
            t = data.get("t")
            self._sequence = data.get("s")

            if t == "MESSAGE_CREATE":
                msg_data = data["d"]
                # Ignore bot messages
                if msg_data.get("author", {}).get("bot"):
                    return

                channel_id = msg_data["channel_id"]
                guild_id = msg_data.get("guild_id", "")
                author = msg_data["author"]
                content = msg_data.get("content", "")

                if not content.strip():
                    return

                message = InboundMessage(
                    channel_type="discord",
                    channel_id=channel_id,
                    account_id=author["id"],
                    message=content,
                    timestamp=msg_data["timestamp"],
                    metadata={
                        "guild_id": guild_id,
                        "author_name": author.get("username"),
                        "message_id": msg_data["id"],
                    },
                )

                if self._handler:
                    self._handler(message)

    async def send(self, outbound: OutboundMessage) -> bool:
        """Send message to Discord channel"""
        import aiohttp

        try:
            # Get Discord webhook or use API
            # For simplicity, use channel_id to get channel info
            async with aiohttp.ClientSession() as session:
                # Create message via Discord API
                url = f"https://discord.com/api/v10/channels/{outbound.channel_id}/messages"
                headers = {
                    "Authorization": f"Bot {self._bot_token}",
                    "Content-Type": "application/json",
                }
                data = {"content": outbound.message}
                if outbound.reply_to:
                    data["message_reference"] = {"message_id": outbound.reply_to}

                async with session.post(url, json=data, headers=headers) as resp:
                    return resp.status == 200

        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False

    def on_message(self, handler) -> None:
        """Set message handler"""
        self._handler = handler
