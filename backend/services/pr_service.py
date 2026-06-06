"""
PR Service
Phase 8: GitHub PR and GitLab MR creation
"""
import httpx
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PRResult:
    """Result of PR creation"""
    success: bool
    pr_url: str
    pr_number: int
    message: str


@dataclass
class ReviewRequest:
    """Code review request"""
    workspace_id: str
    branch: str
    base_branch: str
    title: str
    description: str
    changed_files: list[str]
    commit_hash: str
    task_id: str


class PRService:
    """
    Service for creating Pull Requests on GitHub and Merge Requests on GitLab.
    Handles authentication, PR creation, and status tracking.
    """

    def __init__(self):
        self.github_token = ""
        self.gitlab_token = ""
        self.github_api = "https://api.github.com"
        self.gitlab_api = "https://gitlab.com/api/v4"

    def configure_github(self, token: str) -> None:
        """Configure GitHub token"""
        self.github_token = token

    def configure_gitlab(self, token: str) -> None:
        """Configure GitLab token"""
        self.gitlab_token = token

    async def create_github_pr(
        self,
        owner: str,
        repo: str,
        branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> PRResult:
        """
        Create GitHub Pull Request.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Source branch name
            base_branch: Target branch name
            title: PR title
            body: PR description

        Returns:
            PRResult with success, url, number, message
        """
        if not self.github_token:
            return PRResult(
                success=False,
                pr_url="",
                pr_number=0,
                message="GitHub token not configured",
            )

        url = f"{self.github_api}/repos/{owner}/{repo}/pulls"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        payload = {
            "title": title,
            "head": branch,
            "base": base_branch,
            "body": body,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 201:
                    data = response.json()
                    return PRResult(
                        success=True,
                        pr_url=data["html_url"],
                        pr_number=data["number"],
                        message="PR created successfully",
                    )
                else:
                    error = response.json().get("message", "Unknown error")
                    return PRResult(
                        success=False,
                        pr_url="",
                        pr_number=0,
                        message=f"GitHub API error: {error}",
                    )

        except Exception as e:
            logger.error(f"GitHub PR creation failed: {e}")
            return PRResult(
                success=False,
                pr_url="",
                pr_number=0,
                message=str(e),
            )

    async def create_gitlab_mr(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
    ) -> PRResult:
        """
        Create GitLab Merge Request.

        Args:
            project_id: GitLab project ID or path-encoded path
            source_branch: Source branch name
            target_branch: Target branch name
            title: MR title
            description: MR description

        Returns:
            PRResult with success, url, number, message
        """
        if not self.gitlab_token:
            return PRResult(
                success=False,
                pr_url="",
                pr_number=0,
                message="GitLab token not configured",
            )

        url = f"{self.gitlab_api}/projects/{project_id}/merge_requests"

        headers = {
            "PRIVATE-TOKEN": self.gitlab_token,
            "Content-Type": "application/json",
        }

        payload = {
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "description": description,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 201:
                    data = response.json()
                    return PRResult(
                        success=True,
                        pr_url=data["web_url"],
                        pr_number=data["iid"],
                        message="MR created successfully",
                    )
                else:
                    error = response.json().get("message", "Unknown error")
                    return PRResult(
                        success=False,
                        pr_url="",
                        pr_number=0,
                        message=f"GitLab API error: {error}",
                    )

        except Exception as e:
            logger.error(f"GitLab MR creation failed: {e}")
            return PRResult(
                success=False,
                pr_url="",
                pr_number=0,
                message=str(e),
            )

    async def get_github_pr_status(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict:
        """
        Get GitHub PR status and review info.

        Returns:
            dict with state, reviews, etc.
        """
        if not self.github_token:
            return {"error": "GitHub token not configured"}

        url = f"{self.github_api}/repos/{owner}/{repo}/pulls/{pr_number}"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "state": data["state"],
                        "title": data["title"],
                        "mergeable": data["mergeable"],
                        "reviews": data.get("review_comments", 0),
                    }
                else:
                    return {"error": f"Status code: {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    def format_pr_description(self, review_request: ReviewRequest) -> str:
        """
        Format PR description from review request.

        Args:
            review_request: ReviewRequest with all details

        Returns:
            Formatted markdown description
        """
        files_md = "\n".join(f"- `{f}`" for f in review_request.changed_files)

        description = f"""## 代码审核请求

### 任务信息
- **Task ID**: {review_request.task_id}
- **Commit**: `{review_request.commit_hash}`
- **分支**: `{review_request.branch}` → `{review_request.base_branch}`

### 变更文件
{files_md}

### 描述
{review_request.description}

---
*Generated by Coding-CLI Agent*
"""

        return description

    def generate_commit_message(self, task_id: str, action: str, scope: str = "") -> str:
        """
        Generate conventional commit message.

        Format: <type>(<scope>): <subject>
        """
        types_map = {
            "add": "feat",
            "modify": "feat",
            "fix": "fix",
            "refactor": "refactor",
            "docs": "docs",
        }

        commit_type = types_map.get(action, "feat")
        scope_part = f"({scope})" if scope else ""

        return f"{commit_type}{scope_part}: {task_id}"