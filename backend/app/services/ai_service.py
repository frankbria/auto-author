"""AIService: the provider client plus the flows composed from app.services.ai (#922)."""
from openai import OpenAI
from app.core.config import settings
from app.services.ai.draft_flows import DraftFlowsMixin
from app.services.ai.editor_flows import EditorFlowsMixin
from app.services.ai.toc_flows import TocFlowsMixin
from app.services.ai.toc_generation import TocGenerationMixin
from app.services.ai.transport import TransportMixin, model_call_attempted

__all__ = ["AIService", "ai_service", "model_call_attempted"]


class AIService(TransportMixin, TocFlowsMixin, TocGenerationMixin, DraftFlowsMixin, EditorFlowsMixin):
    """
    AI Service for handling OpenAI API interactions for summary analysis and TOC generation.
    Includes retry mechanism for failed requests and response caching.
    """

    def __init__(self):
        """Initialize the AI service with OpenAI client."""
        # max_retries=0: the SDK silently retries each request (default 2) on
        # top of _retry_with_backoff, multiplying real API calls per failure
        # (observed 3x3=9 on the wire). Retry ownership lives in
        # _retry_with_backoff only (#188).
        self.client = OpenAI(
            # Never "" or None: the SDK raises on "" (the backend would not
            # boot) and falls back to the OPENAI_API_KEY env var on None, which
            # would send the OpenAI key to another AI_BASE_URL (#917). /health
            # reports the missing key instead.
            api_key=settings.openai_api_key or "missing-ai-api-key",
            # Explicit, so the SDK's OPENAI_BASE_URL env fallback can't route the
            # OpenAI key elsewhere: AI_BASE_URL is the only switch (#917).
            base_url=settings.AI_BASE_URL or "https://api.openai.com/v1",
            max_retries=0,
            # Per attempt; without it the SDK waits ten minutes (#799).
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.model = settings.AI_MODEL_DEFAULT
        self.long_output_model = settings.AI_MODEL_LONG_OUTPUT
        self.max_retries = settings.AI_MAX_RETRIES
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.max_delay = 60.0  # Maximum delay between retries


# Singleton instance
ai_service = AIService()
