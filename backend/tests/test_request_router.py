"""
Tests for the Request Router.

Verifies that the lightweight Python-based classifier correctly routes
different message types without using an LLM.
"""

from __future__ import annotations

import pytest

from app.models.capabilities import TaskCategory
from app.routing.request_router import RequestRouter


@pytest.fixture
def router() -> RequestRouter:
    """Create a fresh RequestRouter instance."""
    return RequestRouter()


class TestCasualRouting:
    """Test that casual/greeting messages are classified correctly."""

    @pytest.mark.parametrize(
        "message",
        [
            "Hi",
            "hello",
            "Hey",
            "Good morning",
            "Thanks",
            "Thank you",
            "Bye",
            "Ok",
            "Sure",
            "Hi!",
            "hello!",
            "Hey!",
            "good evening",
            "Good night!",
        ],
    )
    def test_casual_messages(self, router: RequestRouter, message: str) -> None:
        result = router.classify(message)
        assert result == TaskCategory.CASUAL, f"'{message}' should be CASUAL, got {result}"

    def test_casual_does_not_require_agent(self, router: RequestRouter) -> None:
        assert not router.requires_agent(TaskCategory.CASUAL)

    def test_conversation_does_not_require_agent(self, router: RequestRouter) -> None:
        assert not router.requires_agent(TaskCategory.CONVERSATION)


class TestCodingRouting:
    """Test that coding requests are classified correctly."""

    @pytest.mark.parametrize(
        "message",
        [
            "Write a Python function to sort a list",
            "Create a script that reads a CSV file",
            "Debug this code for me",
            "Implement a binary search algorithm",
            "Write a Python utility and test it",
            "Generate a function to calculate fibonacci numbers",
            "Fix the bug in my Python code",
            "Build a REST API endpoint",
            "Now make a website in Next.js",
            "make hero section in this",
            "make a website",
            "write a code in html and css and js of a website",
            "any thing you can make in hero section",
            "ake a website",
        ],
    )
    def test_coding_messages(self, router: RequestRouter, message: str) -> None:
        result = router.classify(message)
        assert result == TaskCategory.CODING, f"'{message}' should be CODING, got {result}"

    def test_coding_requires_agent(self, router: RequestRouter) -> None:
        assert router.requires_agent(TaskCategory.CODING)


class TestVisionRouting:
    """Test that vision/multimodal requests are classified correctly."""

    def test_image_attachment_routes_to_vision(self, router: RequestRouter) -> None:
        result = router.classify("What is in this?", has_image=True)
        assert result == TaskCategory.VISION

    def test_vision_keywords(self, router: RequestRouter) -> None:
        result = router.classify("Analyze this P&ID diagram for me")
        assert result == TaskCategory.VISION

    def test_scanned_document_keyword(self, router: RequestRouter) -> None:
        result = router.classify("Process this scanned inspection photo")
        assert result == TaskCategory.VISION

    def test_vision_requires_agent(self, router: RequestRouter) -> None:
        assert router.requires_agent(TaskCategory.VISION)


class TestDocumentRouting:
    """Test that document analysis requests are classified correctly."""

    @pytest.mark.parametrize(
        "message",
        [
            "Analyze this inspection report and extract findings",
            "Summarize this report for me",
            "Generate an approval note based on this document",
            "Create a Word document with these details",
            "Draft an approval note for the inspection findings",
        ],
    )
    def test_document_messages(self, router: RequestRouter, message: str) -> None:
        result = router.classify(message)
        assert result == TaskCategory.DOCUMENT, f"'{message}' should be DOCUMENT, got {result}"

    def test_document_attachment_routes_to_document(self, router: RequestRouter) -> None:
        result = router.classify("Please review this", has_document=True)
        assert result == TaskCategory.DOCUMENT

    def test_document_requires_agent(self, router: RequestRouter) -> None:
        assert router.requires_agent(TaskCategory.DOCUMENT)


class TestKnowledgeRouting:
    """Test that knowledge base queries are classified correctly."""

    @pytest.mark.parametrize(
        "message",
        [
            "Search the knowledge base for safety procedures",
            "What does the SOP say about valve inspection?",
            "Find the standard operating procedure for boiler maintenance",
        ],
    )
    def test_knowledge_messages(self, router: RequestRouter, message: str) -> None:
        result = router.classify(message)
        assert result == TaskCategory.KNOWLEDGE, f"'{message}' should be KNOWLEDGE, got {result}"


class TestComplexRouting:
    """Test that complex multi-step requests default to COMPLEX."""

    def test_complex_long_message(self, router: RequestRouter) -> None:
        msg = (
            "I need you to read the attached inspection report, "
            "compare the findings with our internal safety SOP, "
            "and then generate a detailed approval note as a Word document"
        )
        # This has document keywords — should match document
        result = router.classify(msg)
        assert result in (TaskCategory.DOCUMENT, TaskCategory.COMPLEX)

    def test_ambiguous_defaults_to_complex(self, router: RequestRouter) -> None:
        msg = "Help me plan the quarterly maintenance schedule with cost estimates and resource allocation"
        result = router.classify(msg)
        assert result == TaskCategory.COMPLEX


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string(self, router: RequestRouter) -> None:
        result = router.classify("")
        # Empty should be casual (very short)
        assert result in (TaskCategory.CASUAL, TaskCategory.CONVERSATION)

    def test_single_word_question(self, router: RequestRouter) -> None:
        result = router.classify("What?")
        assert result in (TaskCategory.CONVERSATION, TaskCategory.CASUAL)

    def test_image_overrides_text_classification(self, router: RequestRouter) -> None:
        """Image attachment should force VISION regardless of text content."""
        result = router.classify("Hello how are you", has_image=True)
        assert result == TaskCategory.VISION
