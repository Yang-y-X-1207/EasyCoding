"""
Telegram Adapter
Phase 5: Telegram Bot API integration
"""
import asyncio
import logging
from datetime import datetime

from backend.domain.ports.ichannel import IChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class TelegramAdapter(IChannelAdapter):
    """
    Telegram adapter using Bot API Long Polling.
    Requires TELEGRAM_BOT_TOKEN.
    """

    def __init__(self, bot_token: str):
        self._bot_token = bot_token
        self._handler = None
        self._polling_task = None
        self._running = False
        self._offset = 0

    @property
    def channel_type(self) -> str:
        return "telegram"

    async def start(self) -> None:
        """Start Telegram polling"""
        self._running = True
        self._polling_task = asyncio.create_task(self._poll())
        logger.info("Telegram adapter started")

    async def stop(self) -> None:
        """Stop Telegram polling"""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram adapter stopped")

    async def _poll(self) -> None:
        """Long polling for Telegram updates"""
        import aiohttp

        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.telegram.org/bot{self._bot_token}/getUpdates"
                    params = {
                        "offset": self._offset,
                        "timeout": 60,
                    }

                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            updates = data.get("result", [])

                            for update in updates:
                                await self._process_update(update)
                                self._offset = update["update_id"] + 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)

    async def _process_update(self, update: dict) -> None:
        """Process a Telegram update"""
        if "message" not in update:
            return

        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        user_id = str(msg["from"]["id"])
        text = msg.get("text", "")
        timestamp = datetime.fromtimestamp(msg["date"]).isoformat() + "Z"

        message = InboundMessage(
            channel_type="telegram",
            channel_id=chat_id,
            account_id=user_id,
            message=text,
            timestamp=timestamp,
            metadata={"update": update},
        )

        if self._handler:
            self._handler(message)

    async def send(self, outbound: OutboundMessage) -> bool:
        """Send message to Telegram chat"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
                data = {
                    "chat_id": outbound.channel_id,
                    "text": outbound.message,
                }
                if outbound.reply_to:
                    data["reply_to_message_id"] = outbound.reply_to

                async with session.post(url, json=data) as resp:
                    return resp.status == 200

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def on_message(self, handler) -> None:
        """Set message handler"""
        self._handler = handler
