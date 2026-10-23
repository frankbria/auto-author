"""Provider transport: retry with backoff, the request itself, output budgets (#922)."""
import html
import openai
import logging
import re
import asyncio
from contextvars import ContextVar
import uuid
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.reporting import report_failure
from app.schemas.ai_input import MAX_PROMPT_CHARS
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIProviderAuthError,
    AIProviderQuotaError,
    AIInvalidRequestError
)

# The logger keeps the name it had before the split (#922), so log routing
# and filters keyed on it still match.
logger = logging.getLogger("app.services.ai_service")

# A list item's leading "1." / "2)" / "-" / "•" / "*" marker.
LIST_MARKER = re.compile(r"^(?:\d+[.)](?!\d)\s*|[-•*]\s+)")
# A full stop that ends a sentence: followed by space or the end, and not after
# a title or "e.g." (#850).
SENTENCE_END = re.compile(r"(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bMrs)(?<!\bSt)(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)\.(?:\s+|$)")

# Drafts and TOCs run on the long-output model class (settings.AI_MODEL_LONG_OUTPUT,
# default gpt-4o: 128k context / 16k output) so the UI's top length options stay
# serviceable (#232): gpt-4's 8192-token shared context capped completions at
# ~4000 tokens. Every other flow uses settings.AI_MODEL_DEFAULT (#917).
# Draft-generation token budget (#181): ~1.6 tokens per English word, clamped by
# AI_MAX_OUTPUT_TOKENS_LONG (default 8000 covers 5,000 words).
DRAFT_WORDS_TO_TOKENS_FACTOR = 1.6

# A TOC (6-12 chapters x 2-4 subchapters as pretty JSON) measures ~2k tokens at
# 8x3 and ~3.7k at 12x4; 1500 truncated every typical one (#774). 6000 leaves
# headroom over the largest shape the prompt asks for. Runs on the long-output
# model because gpt-4's 8192-token context is shared with the prompt.
TOC_MAX_COMPLETION_TOKENS = 6000


# Transform, enhance and transcription cleanup return a text about as long as
# the one they were given, so their completion budget follows its length (#801).
# A third of the characters is well over the measured rate for English (4.9
# characters a token for prose, 4.4 for technical text); the floor is the
# budget these flows always had, which
# keeps room for scripts that take a token or more per character. The request
# method clamps the result to AI_MAX_OUTPUT_TOKENS_LONG.
REWRITE_MIN_COMPLETION_TOKENS = 4000


def rewrite_max_tokens(content: str) -> int:
    return max(REWRITE_MIN_COMPLETION_TOKENS, len(content) // 3)


# A model can condense a long text and still report a normal finish, and the
# page would offer the result as the finished rewrite (#983). A rewrite that
# keeps under this percentage of its source's text is refused. Against a real
# model a faithful transform kept 94% to 112% of the words and a condensed one
# 28% to 54%; cleaning up a dictation that was a quarter filler kept 58% to 66%,
# so cleanup may lose more. Under 1,000 characters (about 200 English words)
# the share says little: tightening a paragraph can halve it.
REWRITE_MIN_PERCENT_KEPT = 60
CLEANUP_MIN_PERCENT_KEPT = 40
REWRITE_SHARE_CHECKED_FROM_CHARS = 1000

MARKUP = re.compile(r"<[^>]+>")


def visible_text(text: str) -> str:
    """The text a reader sees: tags become spaces and entities the characters
    they stand for. The editor stores paragraphs side by side with nothing
    between them, and pasted rich text is full of ``&nbsp;``."""
    return html.unescape(MARKUP.sub(" ", text))


def text_length(text: str) -> int:
    """Characters of visible text, without whitespace.

    Not words: Chinese, Japanese and Thai are written without spaces, and the
    same text marked up or spaced differently must measure the same.
    """
    return len("".join(visible_text(text).split()))


def word_count(text: str) -> int:
    """Words of visible text, for the counts the preview shows."""
    return len(visible_text(text).split())


def shortened_rewrite_error(source: str, rewrite: str, min_percent: int) -> Optional[str]:
    """What to tell the author when ``rewrite`` lost too much of ``source``, else None."""
    before, after = text_length(source), text_length(rewrite)
    if before < REWRITE_SHARE_CHECKED_FROM_CHARS or after * 100 >= min_percent * before:
        return None
    return (
        f"The result came back at {after * 100 // before}% of the length of the text "
        "it was given, so it was not used. Try a shorter section."
    )


# True once this request has been handed to the provider. The AI quota reads
# it to tell a request refused beforehand, which costs nothing, from one the
# provider may have billed (#798). A ContextVar, so each request has its own.
model_call_attempted: ContextVar[bool] = ContextVar("model_call_attempted", default=False)

# True once this request's AI failure has gone to report_failure, so the 5xx
# the route answers with is not a second report of it (#994).
ai_failure_reported: ContextVar[bool] = ContextVar("ai_failure_reported", default=False)


class TransportMixin:
    """Retry, request and response checks shared by every AIService flow."""

    async def _retry_with_backoff(
        self,
        func,
        *args,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Execute a function with exponential backoff retry mechanism.

        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            correlation_id: Optional correlation ID for tracking
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution

        Raises:
            AIServiceError: Structured error with retry information
        """
        last_exception = None
        correlation_id = correlation_id or str(uuid.uuid4())

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Attempting API call (attempt {attempt + 1}/{self.max_retries}) "
                    f"[correlation_id={correlation_id}]"
                )
                return await func(*args, **kwargs)

            except openai.RateLimitError as e:
                if e.code == "insufficient_quota":
                    # CRITICAL: every AI feature is down until someone adds
                    # credit, and no retry will change that (#775, #799).
                    logger.critical(
                        f"OpenAI refused for billing (insufficient_quota) [correlation_id={correlation_id}]"
                    )
                    raise AIProviderQuotaError(
                        original_exception=e, correlation_id=correlation_id
                    )
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries}) "
                    f"[correlation_id={correlation_id}]"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Max retries reached for rate limit error [correlation_id={correlation_id}]"
                    )
                    raise AIRateLimitError(
                        retry_after=int(delay),
                        original_exception=e,
                        correlation_id=correlation_id
                    )

            except (openai.AuthenticationError, openai.PermissionDeniedError) as e:
                # The key is wrong or may not use this model. Retrying sends the
                # same key again; an operator has to act (#799).
                logger.critical(
                    f"AI provider rejected our credential ({e.status_code}) "
                    f"[correlation_id={correlation_id}]"
                )
                raise AIProviderAuthError(
                    original_exception=e, correlation_id=correlation_id
                )

            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"API timeout/connection error, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.max_retries}) [correlation_id={correlation_id}]"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Max retries reached for network error [correlation_id={correlation_id}]"
                    )
                    raise AINetworkError(
                        retry_after=int(delay),
                        original_exception=e,
                        correlation_id=correlation_id
                    )

            except openai.InternalServerError as e:
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"OpenAI server error, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.max_retries}) [correlation_id={correlation_id}]"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Max retries reached for server error [correlation_id={correlation_id}]"
                    )
                    raise AIServiceUnavailableError(
                        retry_after=int(delay),
                        original_exception=e,
                        correlation_id=correlation_id
                    )

            except openai.BadRequestError as e:
                logger.error(
                    f"Invalid request to AI service: {str(e)} [correlation_id={correlation_id}]"
                )
                # The provider's text stays in the log line above (#802).
                raise AIInvalidRequestError(
                    original_exception=e,
                    correlation_id=correlation_id
                )

            except AIServiceError:
                # Re-raise our custom errors without wrapping
                raise

            except Exception as e:
                # 402 is how OpenAI-compatible providers (Ollama cloud,
                # OpenRouter) refuse for billing; same meaning as #775's 429 (#917).
                if isinstance(e, openai.APIStatusError) and e.status_code == 402:
                    logger.critical(
                        f"AI provider refused for billing (402) [correlation_id={correlation_id}]"
                    )
                    raise AIProviderQuotaError(
                        original_exception=e, correlation_id=correlation_id
                    )
                logger.error(
                    f"Unexpected error in AI service: {str(e)} [correlation_id={correlation_id}]"
                )
                raise AIServiceError(
                    message="The AI service failed unexpectedly",
                    error_code="AI_UNEXPECTED_ERROR",
                    original_exception=e,
                    correlation_id=correlation_id
                )

        # If we've exhausted all retries, raise the last exception as structured error
        if last_exception:
            raise AIServiceError(
                message=f"AI service failed after {self.max_retries} retries",
                error_code="AI_MAX_RETRIES_EXCEEDED",
                original_exception=last_exception,
                correlation_id=correlation_id
            )

    async def _make_openai_request(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 1000,
        correlation_id: Optional[str] = None,
        long_output: bool = False,
    ):
        """
        Make an OpenAI API request with retry logic.

        Retry lives HERE and only here — callers must not wrap this in
        _retry_with_backoff again, or a persistent failure makes up to
        AI_MAX_RETRIES**2 real API calls (#188).

        Args:
            messages: List of message dictionaries for the chat completion
            temperature: Temperature for response generation
            max_tokens: Maximum tokens for the response
            correlation_id: Optional correlation ID so retry logs stay
                correlated with the calling request
            long_output: Use the long-output model class (drafts, TOC) and
                its token cap instead of the default class (#232, #917)

        Returns:
            OpenAI response object
        """

        if long_output:
            model, cap = self.long_output_model, settings.AI_MAX_OUTPUT_TOKENS_LONG
        else:
            model, cap = self.model, settings.AI_MAX_OUTPUT_TOKENS_DEFAULT

        def _sync_request():
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                # Headroom for hidden reasoning, still under the class cap (#925).
                max_tokens=min(max_tokens + settings.AI_REASONING_HEADROOM_TOKENS, cap),
            )

        async def _async_wrapper():
            # Offload the blocking OpenAI HTTP call to a worker thread so it
            # doesn't freeze the event loop (#175). A single in-flight
            # generation must not stall health checks or other users' requests.
            return await asyncio.to_thread(_sync_request)

        # The routes cap what they accept; this bounds whatever reaches a call by
        # another road, such as text stored before the caps existed (#800).
        prompt_chars = sum(len(message.get("content") or "") for message in messages)
        if prompt_chars > MAX_PROMPT_CHARS:
            raise AIInvalidRequestError(
                f"The text for this AI request is {prompt_chars} characters; "
                f"the limit is {MAX_PROMPT_CHARS}",
                correlation_id=correlation_id,
            )

        model_call_attempted.set(True)
        try:
            return await self._retry_with_backoff(_async_wrapper, correlation_id=correlation_id)
        except AIServiceError as error:
            # Once, after the retries. Some flows answer this with fallback
            # content, so the route's response cannot be the report (#994).
            ai_failure_reported.set(True)
            report_failure(f"ai-{error.error_code}", error)
            raise

    def _untruncated_text(self, response, correlation_id: Optional[str] = None) -> str:
        """The completion's text, refusing one that hit max_tokens.

        A reasoning model can spend the whole budget thinking and return empty
        content (Nemotron did on analysis, 4 of 4 runs). Parsed anyway, that
        reads as a real "not ready" verdict or a parse failure (#917).
        """
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise AIServiceError(
                message="The AI response was cut off before it finished. Please try again.",
                error_code="AI_RESPONSE_TRUNCATED",
                retryable=False,
                correlation_id=correlation_id,
            )
        return choice.message.content
