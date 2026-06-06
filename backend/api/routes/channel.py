"""
Channel Management API
Phase 5: Configure and control channel adapters
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()

# Global dispatcher instance (will be set by main.py)
_dispatcher = None


def set_dispatcher(dispatcher):
    """Set the global dispatcher"""
    global _dispatcher
    _dispatcher = dispatcher


@router.get("/channels")
async def list_channels():
    """List all registered channels"""
    if not _dispatcher:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dispatcher not initialized",
        )
    return {"channels": _dispatcher.list_channels()}


@router.post("/channels/{channel_type}/start")
async def start_channel(channel_type: str):
    """Start a specific channel"""
    if not _dispatcher:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dispatcher not initialized",
        )

    if channel_type not in _dispatcher.list_channels():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel {channel_type} not registered",
        )

    # Channels auto-start via dispatcher.start_all()
    return {"status": "started", "channel": channel_type}


@router.post("/channels/{channel_type}/send")
async def send_to_channel(
    channel_type: str,
    channel_id: str,
    message: str,
    reply_to: str | None = None,
):
    """Send message to a channel"""
    if not _dispatcher:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dispatcher not initialized",
        )

    success = await _dispatcher.send_to_channel(
        channel_type=channel_type,
        channel_id=channel_id,
        message=message,
        reply_to=reply_to,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send to {channel_type}",
        )

    return {"success": True, "channel": channel_type, "channel_id": channel_id}
