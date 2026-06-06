"""
Coding-CLI Backend - FastAPI Entry Point
Phase 5: Multi-channel support
"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers
from api.routes import chat, health, session, task, channel
from infrastructure.adapters import (
    ChannelDispatcher,
    DiscordAdapter,
    SlackAdapter,
    TelegramAdapter,
)

# Global dispatcher
_dispatcher = ChannelDispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Initialize channel adapters based on environment
    await _init_channels()
    yield
    # Shutdown
    await _dispatcher.stop_all()


def _init_channels():
    """Initialize enabled channel adapters"""
    # Slack
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    if slack_bot_token and slack_app_token:
        try:
            adapter = SlackAdapter(bot_token=slack_bot_token, app_token=slack_app_token)
            _dispatcher.register_adapter(adapter)
            logger.info("Slack adapter registered")
        except Exception as e:
            logger.error(f"Failed to register Slack: {e}")

    # Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        try:
            adapter = TelegramAdapter(bot_token=telegram_token)
            _dispatcher.register_adapter(adapter)
            logger.info("Telegram adapter registered")
        except Exception as e:
            logger.error(f"Failed to register Telegram: {e}")

    # Discord
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        try:
            adapter = DiscordAdapter(bot_token=discord_token)
            _dispatcher.register_adapter(adapter)
            logger.info("Discord adapter registered")
        except Exception as e:
            logger.error(f"Failed to register Discord: {e}")

    # Set dispatcher for channel routes
    channel.set_dispatcher(_dispatcher)

    # Start all adapters
    if _dispatcher.list_channels():
        import asyncio
        asyncio.create_task(_dispatcher.start_all())


app = FastAPI(
    title="Coding-CLI Backend",
    description="AI Coding Assistant CLI Backend with Multi-Channel Support",
    version="0.5.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(task.router, prefix="/api/v1", tags=["task"])
app.include_router(channel.router, prefix="/api/v1", tags=["channel"])
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    return {
        "message": "Coding-CLI Backend",
        "version": "0.5.0",
        "channels": _dispatcher.list_channels(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
