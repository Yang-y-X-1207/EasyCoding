"""
Chat Service
Phase 3: Agent logic with AI integration (Real LLM)
"""
import os
from datetime import datetime
from uuid import uuid4

from domain.models.session import Session
from infrastructure.storage.session_file_store import SessionFileStore
from services.llm_service import LLMService


class ChatService:
    """Service for handling chat with AI Agent"""

    def __init__(self, session_store: SessionFileStore | None = None):
        self.session_store = session_store or SessionFileStore()
        self.llm = LLMService()

    async def chat(
        self,
        session: Session,
        message: str,
    ) -> tuple[str, bool]:
        """
        Process chat message and return (response, needs_clarification).

        Returns:
            tuple: (response_message, needs_clarification)
        """
        # Add user message
        session.add_message("user", message)

        # Simple evaluation (Phase 3 uses basic logic)
        clarification_needed, questions = self._evaluate_message(message)

        if clarification_needed:
            # Return clarification questions
            response = self._build_clarification_response(questions)
            session.add_message("assistant", response)
            self.session_store.save(session)
            return response, True

        # Process with real LLM
        response = await self._process_with_agent(session, message)
        session.add_message("assistant", response)
        self.session_store.save(session)
        return response, False

    def _evaluate_message(self, message: str) -> tuple[bool, list[str]]:
        """
        Evaluate if message needs clarification.
        Returns: (needs_clarification, list_of_questions)
        """
        questions = []

        # Very short messages likely need clarification
        if len(message) < 20:
            questions.append("您的需求比较简略，请提供更多信息：")
            questions.append("1. 具体要实现什么功能？")
            questions.append("2. 涉及哪些文件或模块？")
            return True, questions

        # Check for vague words
        vague_words = ["那个", "这个", "它", "改一下", "帮我", "看一下"]
        for word in vague_words:
            if word in message:
                questions.append("您的描述比较模糊，请明确：")
                questions.append("1. 具体是指哪个文件/接口/功能？")
                questions.append("2. 具体需要做什么修改？")
                break

        if questions:
            return True, questions

        return False, []

    def _build_clarification_response(self, questions: list[str]) -> str:
        """Build clarification response from questions"""
        return "\n".join(questions) + "\n\n请回复您的具体需求。"

    async def _process_with_agent(self, session: Session, message: str) -> str:
        """
        Process message with real AI Agent (Claude API).
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not api_key:
            # Fallback to mock response if no API key
            return self._mock_response(session, message)

        # Build messages for Claude
        claude_messages = []
        for msg in session.messages:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # System prompt
        system = """你是一个专业的编程助手，擅长 DDD 领域驱动设计。
请用中文回答。帮助用户完成代码编写、修改、分析等任务。
如果用户要求你执行操作（如创建文件、运行命令），请先确认再执行。"""

        # Call LLM
        result = await self.llm.chat(
            messages=claude_messages,
            system=system,
        )

        return result.get("content", "⚠️ 无法获取响应")

    def _mock_response(self, session: Session, message: str) -> str:
        """
        Mock response when no API key is configured.
        Simulates AI behavior for testing.
        """
        # Check for common intents
        msg_lower = message.lower()

        if "创建" in message or "新建" in message:
            if "文件" in message or "接口" in message:
                return """好的，我来帮您创建。

我将执行以下操作：
1. 分析项目结构
2. 创建相应的代码文件
3. 编写功能实现

请确认是否继续？"""

        if "修改" in message or "改" in message:
            if "bug" in msg_lower or "错误" in message:
                return """好的，我来分析并修复这个问题。

请提供：
1. 出错的文件路径
2. 错误信息或症状描述"""

        if "查看" in message or "看看" in message:
            return """好的，我来查看项目情况。

请告诉我您想了解哪方面的信息？"""

        # Default mock responses
        responses = [
            "我收到了您的请求，正在分析...",
            "根据您的描述，我理解您需要帮助完成编程任务。",
            "好的，让我来处理这个请求。",
            "明白了。我会尽力帮助您完成这个任务。",
        ]

        return responses[len(session.messages) % len(responses)]