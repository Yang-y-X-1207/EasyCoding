"""
Slack Adapter
Phase 5: Slack Socket Mode integration
"""
import asyncio
import json
import logging
from datetime import datetime

from backend.domain.ports.ichannel import IChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class SlackAdapter(IChannelAdapter):
    """
    Slack adapter using Socket Mode.
    Requires SLACK_BOT_TOKEN and SLACK_APP_TOKEN.
    """

    def __init__(
        self,
        bot_token: str,
        app_token: str,
    ):
        self._bot_token = bot_token
        self._app_token = app_token
        self._handler = None
        self._websocket = None
        self._session = None
        self._running = False

    @property
    def channel_type(self) -> str:
        return "slack"

    async def start(self) -> None:
        """Start Slack Socket Mode connection"""
        try:
            from slack_sdk.socket_mode import SocketModeClient
            from slack_sdk.web import WebClient

            # Create WebClient for API calls
            self._session = WebClient(token=self._bot_token)

            # Create SocketModeClient
            self._websocket = SocketModeClient(
                app_token=self._app_token,
                web_client=self._session,
                message_handler=self._handle_slack_event,
            )

            # Connect
            await asyncio.to_thread(self._websocket.connect)
            self._running = True
            logger.info("Slack adapter started")
        except ImportError:
            logger.warning("slack-sdk not installed, Slack adapter disabled")
        except Exception as e:
            logger.error(f"Failed to start Slack adapter: {e}")

    async def stop(self) -> None:
        """Stop Slack connection"""
        self._running = False
        if self._websocket:
            try:
                await asyncio.to_thread(self._websocket.disconnect)
            except Exception as e:
                logger.error(f"Error stopping Slack: {e}")

    def _handle_slack_event(self, client, event, web_client):
        """Handle incoming Slack events"""
        if not event or event.get("type") != "event_callback":
            return

        event_data = event.get("event", {})
        if event_data.get("type") == "app_mention":
            channel_id = event_data.get("channel")
            user_id = event_data.get("user")
            text = event_data.get("text", "")

            # Remove mention Bot ID from text
            if hasattr(self, "_session") and self._session:
                bot_user_id = self._session.auth_test()["user_id"]
                text = text.replace(f"<@{bot_user_id}>", "").strip()

            message = InboundMessage(
                channel_type="slack",
                channel_id=channel_id,
                account_id=user_id,
                message=text,
                timestamp=datetime.utcnow().isoformat() + "Z",
                metadata={"event": event},
            )

            if self._handler:
                self._handler(message)

    async def send(self, outbound: OutboundMessage) -> bool:
        """Send message to Slack channel"""
        if not self._session:
            return False

        try:
            await asyncio.to_thread(
                self._session.chat_postMessage,
                channel=outbound.channel_id,
                text=outbound.message,
                thread_ts=outbound.reply_to,
            )
            return True
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False

    def on_message(self, handler) -> None:
        """Set message handler"""
        self._handler = handler
