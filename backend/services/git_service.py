"""
Git Service
Phase 7: Git operations for code changes
"""
import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GitChange:
    """Represents a file change"""
    file_path: str
    change_type: str  # ADD, MODIFY, DELETE
    diff: str = ""


@dataclass
class CommitResult:
    """Result of a git commit"""
    success: bool
    branch: str
    commit_hash: str = ""
    message: str = ""
    files: list[str] = field(default_factory=list)


@dataclass
class PRResult:
    """Result of PR creation"""
    success: bool
    pr_url: str = ""
    pr_number: int = 0


@dataclass
class GitChangeLog:
    """Changelog entry"""
    timestamp: str
    task_id: str
    message: str
    author: str
    branch: str
    changes: list[GitChange]
    status: str = "pending_review"  # pending_review, approved, rejected, merged


class GitService:
    """
    Git operations service.
    Handles commit, changelog, branch management, PR creation.
    """

    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = Path(workspace_path)

    def _run_git(self, cwd: str | Path, *args) -> tuple[int, str, str]:
        """Run git command, return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Git command timeout"
        except Exception as e:
            return -1, "", str(e)

    def init_repo(self, project_path: Path) -> bool:
        """Initialize git repo if not exists"""
        git_dir = project_path / ".git"
        if git_dir.exists():
            return True

        code, _, err = self._run_git(project_path, "init")
        if code != 0:
            logger.error(f"Git init failed: {err}")
            return False

        # Create initial commit
        self._run_git(project_path, "add", ".")
        self._run_git(project_path, "commit", "-m", "Initial commit")
        return True

    def create_branch(self, project_path: Path, branch_name: str) -> bool:
        """Create new branch"""
        code, _, err = self._run_git(project_path, "checkout", "-b", branch_name)
        if code != 0:
            logger.error(f"Branch creation failed: {err}")
            return False
        return True

    def get_branch_name(self, project_path: Path) -> str:
        """Get current branch name"""
        code, stdout, _ = self._run_git(project_path, "rev-parse", "--abbrev-ref", "HEAD")
        return stdout.strip() if code == 0 else "main"

    def stage_files(self, project_path: Path, files: list[str]) -> bool:
        """Stage files for commit"""
        for f in files:
            code, _, err = self._run_git(project_path, "add", f)
            if code != 0:
                logger.error(f"Git add {f} failed: {err}")
                return False
        return True

    def commit(
        self,
        project_path: Path,
        message: str,
        author: str = "Coding-CLI Agent",
    ) -> CommitResult:
        """Create commit with message"""
        # Configure user if needed
        self._run_git(project_path, "config", "user.name", author)
        self._run_git(project_path, "config", "user.email", "agent@coding-cli.local")

        # Commit
        code, stdout, stderr = self._run_git(
            project_path, "commit", "-m", message
        )

        if code != 0:
            return CommitResult(success=False, branch=self.get_branch_name(project_path), message=stderr)

        # Get commit hash
        code, commit_hash, _ = self._run_git(project_path, "rev-parse", "HEAD")
        hash_value = commit_hash.strip()[:8] if code == 0 else ""

        # Get staged files
        _, files_output, _ = self._run_git(project_path, "diff", "--cached", "--name-only")
        staged_files = [f.strip() for f in files_output.split("\n") if f.strip()]

        return CommitResult(
            success=True,
            branch=self.get_branch_name(project_path),
            commit_hash=hash_value,
            message=message,
            files=staged_files,
        )

    def get_diff(self, project_path: Path, file_path: str = "") -> str:
        """Get diff for file or all changes"""
        if file_path:
            code, diff, _ = self._run_git(project_path, "diff", file_path)
        else:
            code, diff, _ = self._run_git(project_path, "diff", "HEAD")
        return diff if code == 0 else ""

    def push_branch(self, project_path: Path, remote: str = "origin") -> tuple[bool, str]:
        """Push branch to remote"""
        branch = self.get_branch_name(project_path)
        code, _, err = self._run_git(project_path, "push", "-u", remote, branch)
        if code != 0 and "rejected" in err.lower():
            # Try force push for new branches
            code, _, err = self._run_git(project_path, "push", "-f", remote, branch)
        return code == 0, err or "Success"

    def get_status(self, project_path: Path) -> dict:
        """Get git status"""
        code, stdout, _ = self._run_git(project_path, "status", "--porcelain")
        lines = stdout.strip().split("\n") if code == 0 else []
        return {"clean": len(lines) == 0, "files": lines}

    def get_log(self, project_path: Path, limit: int = 10) -> list[dict]:
        """Get commit history"""
        code, stdout, _ = self._run_git(
            project_path, "log", f"--max-count={limit}", "--format=%H|%s|%an|%ad", "--date=iso")
        if code != 0:
            return []

        commits = []
        for line in stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    })
        return commits
