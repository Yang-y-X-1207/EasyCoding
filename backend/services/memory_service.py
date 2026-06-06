"""
Memory Service
Phase 8: CLAUDE.md read/write and project context injection
"""
from pathlib import Path
from typing import Optional


class MemoryService:
    """
    Handles CLAUDE.md file operations and project context injection.
    Provides long-term memory for project knowledge persistence.
    """

    CLAUDE_MD = "CLAUDE.md"
    CONTEXT_MD = "context.md"

    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = Path(workspace_path)

    def get_claude_md_path(self, workspace_id: str) -> Path:
        """Get CLAUDE.md path for workspace project"""
        return self.workspace_path / workspace_id / "project" / self.CLAUDE_MD

    def get_context_md_path(self, workspace_id: str) -> Path:
        """Get context.md path for workspace"""
        return self.workspace_path / workspace_id / "memory" / "context.md"

    def read_claude_md(self, workspace_id: str) -> str:
        """
        Read CLAUDE.md content from workspace project.

        Returns:
            CLAUDE.md content or empty string if not exists
        """
        claude_md = self.get_claude_md_path(workspace_id)
        if not claude_md.exists():
            return ""
        return claude_md.read_text(encoding="utf-8")

    def write_claude_md(self, workspace_id: str, content: str) -> Path:
        """
        Write content to CLAUDE.md in workspace project.

        Returns:
            Path to the written file
        """
        claude_md = self.get_claude_md_path(workspace_id)
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(content, encoding="utf-8")
        return claude_md

    def read_context_md(self, workspace_id: str) -> str:
        """Read project context.md"""
        context_md = self.get_context_md_path(workspace_id)
        if not context_md.exists():
            return ""
        return context_md.read_text(encoding="utf-8")

    def write_context_md(self, workspace_id: str, content: str) -> Path:
        """Write project context.md"""
        context_md = self.get_context_md_path(workspace_id)
        context_md.parent.mkdir(parents=True, exist_ok=True)
        context_md.write_text(content, encoding="utf-8")
        return context_md

    def inject_context(self, workspace_id: str, session_messages: list[dict]) -> list[dict]:
        """
        Inject CLAUDE.md content into session messages as system context.

        This prepends project knowledge to the conversation so the Agent
        has awareness of project conventions and patterns.

        Args:
            workspace_id: Workspace identifier
            session_messages: Current conversation messages

        Returns:
            Updated messages with project context prepended
        """
        claude_md = self.read_claude_md(workspace_id)
        context_md = self.read_context_md(workspace_id)

        if not claude_md and not context_md:
            return session_messages

        # Build system context
        context_parts = ["# 项目上下文 (Project Context)"]

        if claude_md:
            context_parts.append("\n## CLAUDE.md 内容")
            context_parts.append(claude_md)

        if context_md:
            context_parts.append("\n## 项目特定上下文")
            context_parts.append(context_md)

        context_content = "\n".join(context_parts)

        # Find or create system message
        if session_messages and session_messages[0].get("role") == "system":
            # Append to existing system message
            session_messages[0]["content"] += "\n\n" + context_content
        else:
            # Prepend system message
            session_messages.insert(0, {
                "role": "system",
                "content": context_content
            })

        return session_messages

    def get_project_knowledge(self, workspace_id: str) -> dict:
        """
        Get all project knowledge as a structured dict.

        Returns:
            dict with claude_md and context_md content
        """
        return {
            "claemd": self.read_claude_md(workspace_id),
            "context": self.read_context_md(workspace_id),
        }

    def update_project_knowledge(
        self,
        workspace_id: str,
        claude_md: Optional[str] = None,
        context_md: Optional[str] = None,
    ) -> dict:
        """
        Update project knowledge files.

        Args:
            workspace_id: Workspace identifier
            claude_md: New CLAUDE.md content (optional)
            context_md: New context.md content (optional)

        Returns:
            Updated knowledge dict
        """
        result = {}

        if claude_md is not None:
            self.write_claude_md(workspace_id, claude_md)
            result["claemd"] = claude_md

        if context_md is not None:
            self.write_context_md(workspace_id, context_md)
            result["context"] = context_md

        return result

    def ensure_claude_md_exists(self, workspace_id: str, template: str = "") -> bool:
        """
        Ensure CLAUDE.md exists, creating from template if needed.

        Args:
            workspace_id: Workspace identifier
            template: Optional template content

        Returns:
            True if file exists or was created
        """
        claude_md = self.get_claude_md_path(workspace_id)
        if claude_md.exists():
            return True

        if not template:
            template = self._default_claude_md_template()

        self.write_claude_md(workspace_id, template)
        return True

    def _default_claude_md_template(self) -> str:
        """Generate default CLAUDE.md template"""
        return """# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

项目名称：
项目描述：
技术栈：

## 开发规范

### 代码规范
- Python: snake_case
- TypeScript: camelCase
- 配置文件: kebab-case.yaml

### Git 规范
- Commit Message: feat(module): description
- Branch: task/{name}-{date}

## 项目结构

```
src/
├── api/          # HTTP 入口
├── app/          # 应用服务
├── domain/       # 领域模型
├── infrastructure/# 基础设施
└── trigger/      # 触发器
```

## 常用命令

```bash
# 构建
mvn clean package -DskipTests

# 测试
pytest
```
"""