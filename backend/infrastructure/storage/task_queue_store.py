"""
Task Queue Store
Phase 4: File-based task queue with deduplication
"""
import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from backend.domain.models.task import Task, TaskSignature, TaskStatus


class TaskQueueStore:
    """
    File-based task queue with deduplication.
    Uses signature hash to detect duplicate tasks.
    """

    def __init__(
        self,
        storage_dir: str = "memory/tasks",
        dedup_window_minutes: int = 5,
        completed_ttl_minutes: int = 30,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.queue_file = self.storage_dir / "queue.json"
        self.signatures_file = self.storage_dir / "signatures.json"
        self.completed_file = self.storage_dir / "completed.json"

        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.completed_ttl = timedelta(minutes=completed_ttl_minutes)

        # In-memory cache
        self._queue: list[Task] = []
        self._signatures: dict[str, TaskSignature] = {}
        self._completed: list[Task] = []
        self._processing: Task | None = None

        self._load()

    def _load(self) -> None:
        """Load queue from disk"""
        # Load queue
        if self.queue_file.exists():
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._queue = [Task(**t) for t in data]

        # Load signatures
        if self.signatures_file.exists():
            with open(self.signatures_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._signatures = {k: TaskSignature(**v) for k, v in data.items()}

        # Load completed
        if self.completed_file.exists():
            with open(self.completed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._completed = [Task(**t) for t in data]

        # Clean expired signatures
        self._clean_expired()

    def _save(self) -> None:
        """Save queue to disk"""
        # Save queue
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump([t.__dict__ for t in self._queue], f, indent=2, ensure_ascii=False)

        # Save signatures
        with open(self.signatures_file, "w", encoding="utf-8") as f:
            json.dump({k: v.__dict__ for k, v in self._signatures.items()}, f, indent=2, ensure_ascii=False)

        # Save completed (limit to 100)
        with open(self.completed_file, "w", encoding="utf-8") as f:
            json.dump([t.__dict__ for t in self._completed[-100:]], f, indent=2, ensure_ascii=False)

    def _clean_expired(self) -> None:
        """Clean expired signatures and completed tasks"""
        now = datetime.utcnow()

        # Clean expired signatures
        expired_keys = []
        for sig_key, sig in self._signatures.items():
            if sig.status == TaskStatus.COMPLETED:
                if sig.completed_at and now - sig.completed_at > self.completed_ttl:
                    expired_keys.append(sig_key)
            elif now - sig.created_at > self.dedup_window:
                expired_keys.append(sig_key)

        for key in expired_keys:
            del self._signatures[key]

        # Clean old completed tasks
        cutoff = now - self.completed_ttl
        self._completed = [t for t in self._completed if t.completed_at and t.completed_at > cutoff]

    def check_duplicate(self, signature: str) -> tuple[bool, str | None]:
        """
        Check if task with this signature already exists.
        Returns: (is_duplicate, existing_task_id)
        """
        if signature in self._signatures:
            sig = self._signatures[signature]
            if sig.status != TaskStatus.COMPLETED:
                return True, sig.task_id
            if sig.completed_at and datetime.utcnow() - sig.completed_at < self.completed_ttl:
                return True, sig.task_id

        return False, None

    def enqueue(self, task: Task) -> tuple[bool, str]:
        """
        Add task to queue.
        Returns: (success, message)
        """
        # Check duplicate
        is_dup, existing_id = self.check_duplicate(task.signature)
        if is_dup:
            return False, f"Duplicate task: {existing_id}"

        # Add to queue
        task.status = TaskStatus.PENDING
        self._queue.append(task)

        # Register signature
        self._signatures[task.signature] = TaskSignature(
            signature=task.signature,
            task_id=task.task_id,
            account_id=task.account_id,
        )

        self._save()
        return True, f"Task {task.task_id} added to queue"

    def dequeue(self) -> Task | None:
        """Get next task from queue (FIFO)"""
        if not self._queue:
            return None

        # Sort by priority, then by created_at
        self._queue.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)

        task = self._queue.pop(0)
        task.mark_processing()
        self._processing = task

        self._save()
        return task

    def complete(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        """Mark task as completed"""
        if self._processing and self._processing.task_id == task_id:
            self._processing.mark_completed(result)
            self._completed.append(self._processing)

            # Update signature status
            if self._processing.signature in self._signatures:
                self._signatures[self._processing.signature].status = TaskStatus.COMPLETED
                self._signatures[self._processing.signature].completed_at = datetime.utcnow()

            self._processing = None
            self._save()
            return True

        # Find in queue
        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                task.mark_completed(result)
                self._completed.append(task)
                self._queue.pop(i)

                if task.signature in self._signatures:
                    self._signatures[task.signature].status = TaskStatus.COMPLETED
                    self._signatures[task.signature].completed_at = datetime.utcnow()

                self._save()
                return True

        return False

    def fail(self, task_id: str, error: str) -> bool:
        """Mark task as failed"""
        if self._processing and self._processing.task_id == task_id:
            self._processing.mark_failed(error)
            self._completed.append(self._processing)
            self._processing = None
            self._save()
            return True

        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                task.mark_failed(error)
                self._completed.append(task)
                self._queue.pop(i)
                self._save()
                return True

        return False

    def cancel(self, task_id: str, account_id: str) -> tuple[bool, str]:
        """Cancel a task (only by owner)"""
        # Check processing
        if self._processing and self._processing.task_id == task_id:
            if self._processing.account_id != account_id:
                return False, "Not owner"
            self._processing.mark_cancelled()
            self._completed.append(self._processing)
            self._processing = None
            self._save()
            return True, "Task cancelled"

        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                if task.account_id != account_id:
                    return False, "Not owner"
                task.mark_cancelled()
                self._completed.append(task)
                self._queue.pop(i)
                self._save()
                return True, "Task cancelled"

        return False, "Task not found"

    def get_status(self) -> dict:
        """Get queue status"""
        self._clean_expired()
        return {
            "queue_length": len(self._queue),
            "processing": self._processing.to_summary() if self._processing else None,
            "completed_recent": len(self._completed[-10:]),
            "signatures_active": len(self._signatures),
        }

    def list_completed(self, limit: int = 10) -> list[Task]:
        """List recent completed tasks"""
        return self._completed[-limit:]
