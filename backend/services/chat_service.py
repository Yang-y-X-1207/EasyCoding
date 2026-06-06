"""
Chat Service
Phase 3: Agent logic with AI integration
"""
from datetime import datetime
from uuid import uuid4

from domain.models.session import Session
from infrastructure.storage.session_file_store import SessionFileStore


class ChatService:
    """Service for handling chat with AI Agent"""

    def __init__(self, session_store: SessionFileStore | None = None):
        self.session_store = session_store or SessionFileStore()

    async def chat(
        self,
        session: Session,
        message: str,
    ) -> tuple[str, bool]:
        """
        Process chat message and return (response, needs_clarification).

        For Phase 3:
        - If message is vague, return clarification questions
        - Otherwise, return AI response (mocked for now)

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

        # Process the request (mocked AI response for Phase 3)
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
        Process message with AI Agent.
        For Phase 3, this is a mock implementation.
        """
        # Mock response for Phase 3
        # Phase 4+ will integrate real LLM

        responses = [
            f"我收到了您的请求：{message[:50]}...",
            "正在分析需求...",
            "根据您的描述，我理解您需要：",
            f"我已经记录了您的请求。完整响应将在 Phase 4 实现。",
        ]

        return responses[len(session.messages) % len(responses)]
