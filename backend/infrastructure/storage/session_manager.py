"""
Session Manager (Phase 2)
Memory cache + async write-back + per-session lock
"""
import asyncio
import logging
from typing import Optional

from backend.domain.models.session import Session
from backend.infrastructure.storage.session_file_store import SessionFileStore

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session management with:
    - In-memory cache
    - Async write-back (fire-and-forget save)
    - Per-session locks for serial access
    """

    def __init__(self, store: SessionFileStore | None = None):
        self._store = store or SessionFileStore()
        self._cache: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._save_tasks: set[asyncio.Task] = set()

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create lock for session"""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def get_or_create(
        self,
        session_id: str,
        account_id: str,
        channel: str = "http",
        agent_id: str = "default",
    ) -> Session:
        """Get existing session or create new one"""
        lock = self._get_lock(session_id)

        async with lock:
            if session_id in self._cache:
                session = self._cache[session_id]
                session.updated_at = asyncio.get_event_loop().time()
                return session

            # Try load from store
            session = self._store.load(session_id)
            if session is None:
                session = Session(
                    session_id=session_id,
                    account_id=account_id,
                    channel=channel,
                    agent_id=agent_id,
                )
                logger.info(f"Created new session: {session_id}")

            self._cache[session_id] = session
            return session

    async def get(self, session_id: str) -> Optional[Session]:
        """Get session from cache or store"""
        if session_id in self._cache:
            return self._cache[session_id]
        return self._store.load(session_id)

    async def save(self, session: Session) -> None:
        """Save session asynchronously (fire-and-forget)"""
        self._cache[session.session_id] = session

        task = asyncio.create_task(self._save_task(session))
        self._save_tasks.add(task)
        task.add_done_callback(self._save_tasks.discard)

    async def _save_task(self, session: Session) -> None:
        """Background save task"""
        try:
            self._store.save(session)
            logger.debug(f"Session saved: {session.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    async def save_sync(self, session: Session) -> None:
        """Synchronous save (for critical updates)"""
        lock = self._get_lock(session.session_id)
        async with lock:
            self._cache[session.session_id] = session
            self._store.save(session)

    async def delete(self, session_id: str) -> bool:
        """Delete session from cache and store"""
        lock = self._get_lock(session_id)
        async with lock:
            if session_id in self._cache:
                del self._cache[session_id]
            if session_id in self._locks:
                del self._locks[session_id]
            return self._store.delete(session_id)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        account_id: str = "unknown",
    ) -> Session:
        """Add message to session and return updated session"""
        session = await self.get_or_create(session_id, account_id)
        session.add_message(role, content)
        await self.save(session)
        return session

    def list_sessions(self, account_id: str | None = None) -> list[Session]:
        """List sessions from cache"""
        if account_id is None:
            return list(self._cache.values())
        return [s for s in self._cache.values() if s.account_id == account_id]

    async def close(self) -> None:
        """Wait for all save tasks to complete"""
        if self._save_tasks:
            await asyncio.gather(*self._save_tasks, return_exceptions=True)
        logger.info("SessionManager closed")