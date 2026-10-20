"""
Sovereign AI Workbench — Request Router

Lightweight Python-based request classifier. NO LLM is used here.
The purpose is to prevent unnecessary reasoning-model calls.

Routing logic:
    - Casual (greetings, thanks) → Qwen3.5:4B (fast path, skip agent)
    - Coding requests → LangGraph agent with coding skill
    - Vision requests (when images attached) → LangGraph agent with vision
    - Document requests → LangGraph agent with document skill
    - Complex / default → LangGraph agent with full planning
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.models.capabilities import TaskCategory

logger = get_logger(__name__)

# --- Pattern sets for classification ---

CASUAL_PATTERNS: set[str] = {
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "good night", "thanks", "thank you", "thankyou", "bye", "goodbye",
    "ok", "okay", "sure", "yes", "no", "alright", "cool", "great",
    "nice", "awesome", "got it", "understood", "hmm", "hm",
    "what's up", "how are you", "how's it going", "sup",
}

CASUAL_REGEX = re.compile(
    r"^(hi+|hey+|hello+|thanks?|thank\s*you|bye|ok(ay)?|good\s*(morning|afternoon|evening|night)|yo+)\s*[!.?]*$",
    re.IGNORECASE,
)

CODING_KEYWORDS: set[str] = {
    "code", "coding", "program", "programming", "python", "javascript",
    "typescript", "function", "class", "algorithm", "debug", "fix bug",
    "compile", "syntax", "error", "test", "unit test", "pytest",
    "script", "execute", "run code", "implement", "refactor",
    "api", "endpoint", "database query", "sql", "regex",
    "git", "docker", "dockerfile", "yaml", "json",
    "html", "css", "react", "fastapi", "flask", "django",
    "website", "webpage", "web page", "web app", "webapp", "site",
    "next.js", "nextjs", "hero section", "landing page",
    "frontend", "backend", "fullstack", "tailwind", "component",
    "ui component", "navbar", "footer", "vue", "angular", "node", "nodejs",
}

CODING_REGEX = re.compile(
    r"\b(write|create|build|generate|fix|debug|implement|refactor|make|ake|develop|design)\b.*?\b(python|code|script|function|class|program|utility|module|test|website|webpage|web\s*page|site|web\s*app|app|hero\s*section|component|landing\s*page|frontend|backend|ui|api|next\.?js|react|html|css|javascript|typescript|tailwind)\b",
    re.IGNORECASE,
)

UNAMBIGUOUS_DEV_REGEX = re.compile(
    r"\b(hero\s*section|landing\s*page|next\.?js|nextjs|html\s*(and|&)?\s*css|tailwind|frontend\s*code|backend\s*code)\b",
    re.IGNORECASE,
)

VISION_KEYWORDS: set[str] = {
    "image", "photo", "photograph", "picture", "drawing", "diagram",
    "p&id", "pid", "scanned", "scan", "ocr", "handwritten",
    "blueprint", "schematic", "floor plan", "engineering drawing",
    "inspection photo", "visual", "look at", "see this",
}

DOCUMENT_KEYWORDS: set[str] = {
    "report", "document", "pdf", "docx", "word", "excel", "spreadsheet",
    "pptx", "powerpoint", "presentation", "approval note", "memo",
    "inspection report", "audit report", "manual",
    "analyze document", "summarize report", "extract", "findings",
    "generate report", "create document", "draft",
    "word file", "word document", "excel file", "excel sheet",
    "ppt file", "powerpoint presentation", "slides", "pdf report",
    "pdf file", "bana de", "banao", "banade",
}

DOCUMENT_ACTION_REGEX = re.compile(
    r"\b(write|create|build|generate|draft|make|prepare|bana|banao|banade)\b.*?\b(word|doc|docx|excel|sheet|spreadsheet|xlsx|csv|ppt|pptx|presentation|powerpoint|slides|pdf|approval\s*note|report|memo)\b",
    re.IGNORECASE,
)

CAD_EXPLICIT_KEYWORDS: set[str] = {
    "cad", "freecad", "fcstd", "dxf", "techdraw", "3d model", "cad model",
    "cad drawing", "technical drawing", "cad drawing bana", "cad model bana",
    "cad bana", "cad banade", "drawing generate", "pipe spool", "piping spool",
}

CAD_ACTION_REGEX = re.compile(
    r"\b(generate|create|make|build|bana|banao|banade|draw|design)\b.*?\b(cad|drawing|dxf|fcstd|techdraw|flange|valve|pipe|spool|3d model|engineering drawing|blueprint)\b",
    re.IGNORECASE,
)

DIAGRAM_KEYWORDS: set[str] = {
    "flowchart", "flow chart", "schematic", "process flow", "pfd",
    "telemetry chart", "flow diagram", "block diagram", "loop diagram", "system diagram",
    "image generate", "image bana", "diagram bana", "diagram banade",
}

DIAGRAM_ACTION_REGEX = re.compile(
    r"\b(generate|create|make|build|bana|banao|banade|draw)\b.*?\b(diagram|flowchart|flow\s*chart|schematic|chart|pfd|process\s*flow|flow\s*diagram|block\s*diagram|loop\s*diagram|image)\b",
    re.IGNORECASE,
)

KNOWLEDGE_KEYWORDS: set[str] = {
    "search", "find", "lookup", "knowledge base", "sop",
    "what does the sop say", "according to", "reference",
    "standard operating procedure", "guideline", "policy",
    "best practice", "compliance", "regulation",
}


class RequestRouter:
    """Classifies user requests into task categories WITHOUT using an LLM.

    Uses keyword matching, regex patterns, and simple heuristics.
    """

    def classify(
        self,
        message: str,
        has_image: bool = False,
        has_document: bool = False,
    ) -> TaskCategory:
        """Classify a user message into a task category.

        Args:
            message: The user's text message.
            has_image: Whether the request includes an image attachment.
            has_document: Whether the request includes a document attachment.

        Returns:
            TaskCategory indicating the type of request.
        """
        normalized = message.strip().lower()

        # 1. Check for casual/greeting messages first (fast path)
        if self._is_casual(normalized):
            logger.info("request_routed", category="casual", message_preview=normalized[:50])
            return TaskCategory.CASUAL

        # 2. Reverse Loop: If image is attached and user asks for CAD/drawing
        if has_image and (CAD_ACTION_REGEX.search(normalized) or self._has_keywords(normalized, CAD_EXPLICIT_KEYWORDS)):
            logger.info("request_routed", category="cad", reason="image_attached_with_cad_query")
            return TaskCategory.CAD

        # 2b. If image is attached, it's a vision task
        if has_image:
            logger.info("request_routed", category="vision", reason="image_attached")
            return TaskCategory.VISION

        # 2c. Check for P&ID / PID drawings or scanned inspection queries
        if any(w in normalized for w in ("p&id", "pid", "inspection photo", "scanned", "blueprint")):
            logger.info("request_routed", category="vision", reason="pid_or_scanned_inspection")
            return TaskCategory.VISION

        # 3. Direct CAD / Technical drawing generation without image
        if CAD_ACTION_REGEX.search(normalized) or self._has_keywords(normalized, CAD_EXPLICIT_KEYWORDS):
            logger.info("request_routed", category="cad")
            return TaskCategory.CAD

        # 3b. Diagram / Flowchart / Visual schematic generation
        if DIAGRAM_ACTION_REGEX.search(normalized) or self._has_keywords(normalized, DIAGRAM_KEYWORDS):
            logger.info("request_routed", category="diagram")
            return TaskCategory.DIAGRAM

        # 4. If document is attached, check what kind of task
        if has_document:
            if self._has_keywords(normalized, CODING_KEYWORDS):
                logger.info("request_routed", category="coding", reason="doc_with_code_keywords")
                return TaskCategory.CODING
            logger.info("request_routed", category="document", reason="document_attached")
            return TaskCategory.DOCUMENT

        # 5. Check for coding patterns
        if self._is_coding(normalized):
            logger.info("request_routed", category="coding")
            return TaskCategory.CODING

        # 5. Check for vision-related keywords (even without image)
        if self._has_keywords(normalized, VISION_KEYWORDS):
            logger.info("request_routed", category="vision")
            return TaskCategory.VISION

        # 6. Check for document/report keywords and creation commands
        if DOCUMENT_ACTION_REGEX.search(normalized) or self._has_keywords(normalized, DOCUMENT_KEYWORDS):
            logger.info("request_routed", category="document")
            return TaskCategory.DOCUMENT

        # 7. Check for knowledge search keywords
        if self._has_keywords(normalized, KNOWLEDGE_KEYWORDS):
            logger.info("request_routed", category="knowledge")
            return TaskCategory.KNOWLEDGE

        # 8. Messages without special keywords → conversation (fast path)
        # Raised threshold to 20 words — only truly complex multi-step tasks
        # should go through the heavy LangGraph agent pipeline.
        if len(normalized.split()) <= 10:
            logger.info("request_routed", category="conversation", reason="general_question")
            return TaskCategory.CONVERSATION

        # 9. Default to complex (will go through full agent pipeline)
        logger.info("request_routed", category="complex", reason="long_complex_message")
        return TaskCategory.COMPLEX

    def _is_casual(self, text: str) -> bool:
        """Check if the message is a casual greeting or acknowledgment."""
        # Exact match against known casual phrases
        if text.rstrip("!?.") in CASUAL_PATTERNS:
            return True
        # Regex match for variations
        if CASUAL_REGEX.match(text):
            return True
        # Very short, no question content
        if len(text.split()) <= 2 and "?" not in text:
            words = set(text.rstrip("!?.").split())
            if words.issubset(CASUAL_PATTERNS | {"", "i", "am", "a", "the"}):
                return True
        return False

    def _is_coding(self, text: str) -> bool:
        """Check if the message is a coding-related request."""
        if CODING_REGEX.search(text):
            return True
        if UNAMBIGUOUS_DEV_REGEX.search(text):
            return True
        return self._has_keywords(text, CODING_KEYWORDS, threshold=2)

    def _has_keywords(
        self,
        text: str,
        keywords: set[str],
        threshold: int = 1,
    ) -> bool:
        """Check if text contains enough keywords from a set.

        Uses word-boundary regex for single words to avoid partial matches
        (e.g., 'find' matching 'findings').
        """
        count = 0
        for keyword in keywords:
            if " " in keyword:
                if keyword in text:
                    count += 1
            else:
                if re.search(rf"\b{re.escape(keyword)}\b", text):
                    count += 1
            if count >= threshold:
                return True
        return False

    def requires_agent(self, category: TaskCategory) -> bool:
        """Check if a task category requires the full LangGraph agent.

        Args:
            category: The classified task category.

        Returns:
            True if the request should go through the agent pipeline.
        """
        return category not in (TaskCategory.CASUAL, TaskCategory.CONVERSATION)
