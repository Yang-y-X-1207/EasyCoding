"""
Session Storage - File-based implementation
Phase 2: JSON file storage for sessions
"""
import json
from datetime import datetime
from pathlib import Path

from backend.domain.models.session import Session


class SessionFileStore:
    """File-based session storage"""

    def __init__(self, storage_dir: str = "memory/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> Path:
        """Get file path for session"""
        return self.storage_dir / f"{session_id}.json"

    def _get_summary_path(self, session_id: str) -> Path:
        """Get summary file path for session"""
        return self.storage_dir / f"{session_id}.md"

    def save(self, session: Session) -> None:
        """Save session to file"""
        file_path = self._get_file_path(session.session_id)

        # Save JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        # Save markdown summary
        summary_path = self._get_summary_path(session.session_id)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(session.to_summary())

    def load(self, session_id: str) -> Session | None:
        """Load session from file"""
        file_path = self._get_file_path(session_id)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Session(**data)

    def delete(self, session_id: str) -> bool:
        """Delete session files"""
        json_path = self._get_file_path(session_id)
        md_path = self._get_summary_path(session_id)

        deleted = False
        if json_path.exists():
            json_path.unlink()
            deleted = True
        if md_path.exists():
            md_path.unlink()
            deleted = True

        return deleted

    def list_sessions(self, account_id: str | None = None) -> list[Session]:
        """List all sessions, optionally filtered by account"""
        sessions = []

        for file_path in self.storage_dir.glob("*.json"):
            if file_path.name.endswith(".json"):
                session = self.load(file_path.stem)
                if session and (account_id is None or session.account_id == account_id):
                    sessions.append(session)

        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
