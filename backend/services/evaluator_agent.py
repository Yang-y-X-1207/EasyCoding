"""
Evaluator Agent
Phase 3: Requirement completeness evaluation
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    """Result of requirement evaluation"""
    is_complete: bool
    missing_fields: list[str]
    questions: list[str]
    suggestion: str | None = None


class EvaluatorAgent:
    """
    Evaluates requirement completeness.
    Asks clarifying questions when requirements are vague.
    """

    # Checklist for requirement completeness
    CHECKLIST = [
        ("goal", "目标", "您想实现什么功能/修复什么问题？"),
        ("scope", "范围", "涉及哪些文件/模块/接口？"),
        ("tech_stack", "技术栈", "使用什么语言/框架/版本？"),
        ("acceptance", "验收标准", "如何判断任务完成？有哪些预期结果？"),
        ("constraints", "约束条件", "有性能、安全、兼容性要求吗？"),
    ]

    def evaluate(self, message: str, context: dict[str, Any] | None = None) -> EvaluationResult:
        """
        Evaluate if a requirement message is complete.

        Returns:
            EvaluationResult with is_complete, missing_fields, questions
        """
        missing_fields = []
        questions = []
        context = context or {}

        # Check message length
        if len(message.strip()) < 10:
            missing_fields.append("message_too_short")
            questions.append("请详细描述您的需求（至少10个字）")
            return EvaluationResult(
                is_complete=False,
                missing_fields=missing_fields,
                questions=questions,
            )

        # Check for vague references
        vague_patterns = [
            ("那个", "这个", "它"),
            ("改一下", "看一下", "帮个忙"),
            ("类似的", "差不多", "和之前一样"),
        ]

        for patterns in vague_patterns:
            for pattern in patterns:
                if pattern in message:
                    missing_fields.append(f"vague_reference:{pattern}")
                    questions.append(
                        f"检测到模糊描述 '{pattern}'，请具体说明是哪个文件/接口/功能？"
                    )
                    break

        # Check for missing context
        if not context.get("project_path") and ("项目" in message or "代码" in message):
            questions.append("请指定项目路径或工作目录")

        # Check for incomplete actions
        incomplete_actions = ["修改", "优化", "改进", "完善"]
        action_found = any(action in message for action in incomplete_actions)

        if action_found and len(message) < 50:
            missing_fields.append("action_too_vague")
            questions.append("请说明具体要修改/优化什么内容？")

        if questions:
            return EvaluationResult(
                is_complete=False,
                missing_fields=missing_fields,
                questions=questions,
            )

        return EvaluationResult(
            is_complete=True,
            missing_fields=[],
            questions=[],
            suggestion="需求描述清晰，可以进入任务队列",
        )

    def generate_signature(self, message: str, context: dict[str, Any] | None = None) -> str:
        """
        Generate a task signature for deduplication.
        Hash of (project_path, file_path, action_type, key_params)
        """
        import hashlib

        ctx = context or {}
        project = ctx.get("project_path", "default")
        files = ctx.get("files", [])
        action = ctx.get("action", "chat")

        # Create signature from context
        sig_parts = [project, action, message[:100]]

        for f in sorted(files)[:5]:  # Max 5 files
            sig_parts.append(str(f))

        sig_str = "|".join(sig_parts)
        return hashlib.md5(sig_str.encode()).hexdigest()[:16]
