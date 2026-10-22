"""Editor rewrites: style transform, enhancement, transcription cleanup (#922)."""
import time
from typing import Dict, Any
from app.services.ai_errors import AIServiceError
from app.services.style_templates import (
    STYLE_LABELS,
    get_style_transformation_prompt,
)
from app.services.content_enhancement import (
    ENHANCEMENT_LABELS,
    get_enhancement_prompt,
)
from app.services.transcription_enhancement import (
    TRANSCRIPTION_ENHANCEMENT_LABEL,
    get_transcription_enhancement_prompt,
)
from app.services.ai.transport import (
    CLEANUP_MIN_PERCENT_KEPT,
    REWRITE_MIN_PERCENT_KEPT,
    logger,
    rewrite_max_tokens,
    shortened_rewrite_error,
    word_count,
)


class EditorFlowsMixin:
    """Rewrites the author's text in place."""

    async def transform_text_style(
        self, content: str, target_style: str
    ) -> Dict[str, Any]:
        """
        Rewrite existing chapter text into a target writing style (issue #58).

        Preview-only: returns the transformed text and metadata without
        persisting. Facts and meaning are preserved; only tone/phrasing change.

        Args:
            content: The existing text to transform.
            target_style: One of the supported style values (see style_templates).

        Returns:
            Dict with success flag, transformed text, and metadata.
        """
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content is required for style transformation.",
                "transformed": "",
                "metadata": {},
            }

        try:
            prompt = get_style_transformation_prompt(content, target_style)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "transformed": "",
                "metadata": {},
            }

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert editor. Rewrite text into a requested "
                        "style while preserving all facts and meaning exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._make_openai_request(
                messages,
                temperature=0.7,
                max_tokens=rewrite_max_tokens(content),
                long_output=True,
            )

            choice = response.choices[0]
            # Refuse to return a truncated rewrite: the caller would overwrite the
            # whole chapter with shortened text, silently losing content (#58).
            if getattr(choice, "finish_reason", None) == "length":
                return {
                    "success": False,
                    # Tagged so the route answers 413, not 503: a retry would be
                    # cut off at the same place (#801).
                    "error_code": "REWRITE_TRUNCATED",
                    "error": (
                        "This chapter is too long to transform in one pass. "
                        "Try transforming a shorter section."
                    ),
                    "transformed": "",
                    "metadata": {},
                }

            transformed = choice.message.content
            shortened = shortened_rewrite_error(content, transformed, REWRITE_MIN_PERCENT_KEPT)
            if shortened:
                return {
                    "success": False,
                    "error_code": "REWRITE_SHORTENED",
                    "error": shortened,
                    "transformed": "",
                    "metadata": {},
                }
            original_words = word_count(content)
            transformed_words = word_count(transformed)

            return {
                "success": True,
                "transformed": transformed,
                "metadata": {
                    "target_style": target_style,
                    "style_label": STYLE_LABELS.get(target_style, target_style),
                    "original_word_count": original_words,
                    "transformed_word_count": transformed_words,
                    "model_used": self.long_output_model,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

        except AIServiceError:
            # The route turns it into its status: a 429 stays a 429 (#802).
            raise
        except Exception:
            logger.error("Failed to transform text style", exc_info=True)
            return {
                "success": False,
                "error": "The request could not be completed.",
                "transformed": "",
                "metadata": {},
            }

    async def enhance_text(
        self, content: str, enhancement_type: str
    ) -> Dict[str, Any]:
        """
        Improve existing chapter text along one dimension (issue #57).

        Preview-only: returns the enhanced text and metadata without persisting.
        Facts and meaning are preserved; only quality (clarity / grammar / tone /
        vocabulary) improves. Mirrors transform_text_style (#58).

        Args:
            content: The existing text to enhance.
            enhancement_type: One of the supported values (see content_enhancement).

        Returns:
            Dict with success flag, enhanced text, and metadata.
        """
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content is required for enhancement.",
                "enhanced": "",
                "metadata": {},
            }

        try:
            prompt = get_enhancement_prompt(content, enhancement_type)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "enhanced": "",
                "metadata": {},
            }

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert editor. Improve the quality of text "
                        "while preserving all facts and meaning exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            # Lower temperature than style transform: enhancement should be a
            # consistent, conservative improvement rather than a creative rewrite.
            response = await self._make_openai_request(
                messages,
                temperature=0.3,
                max_tokens=rewrite_max_tokens(content),
                long_output=True,
            )

            choice = response.choices[0]
            # Refuse to return a truncated result: the caller would overwrite the
            # whole chapter with shortened text, silently losing content (#57).
            if getattr(choice, "finish_reason", None) == "length":
                return {
                    "success": False,
                    # Tagged so the route answers 413, not 503: a retry would be
                    # cut off at the same place (#801).
                    "error_code": "REWRITE_TRUNCATED",
                    "error": (
                        "This chapter is too long to enhance in one pass. "
                        "Try enhancing a shorter section."
                    ),
                    "enhanced": "",
                    "metadata": {},
                }

            enhanced = choice.message.content
            shortened = shortened_rewrite_error(content, enhanced, REWRITE_MIN_PERCENT_KEPT)
            if shortened:
                return {
                    "success": False,
                    "error_code": "REWRITE_SHORTENED",
                    "error": shortened,
                    "enhanced": "",
                    "metadata": {},
                }
            original_words = word_count(content)
            enhanced_words = word_count(enhanced)

            return {
                "success": True,
                "enhanced": enhanced,
                "metadata": {
                    "enhancement_type": enhancement_type,
                    "enhancement_label": ENHANCEMENT_LABELS.get(
                        enhancement_type, enhancement_type
                    ),
                    "original_word_count": original_words,
                    "enhanced_word_count": enhanced_words,
                    "model_used": self.long_output_model,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

        except AIServiceError:
            # The route turns it into its status: a 429 stays a 429 (#802).
            raise
        except Exception:
            logger.error("Failed to enhance text", exc_info=True)
            return {
                "success": False,
                "error": "The request could not be completed.",
                "enhanced": "",
                "metadata": {},
            }

    async def enhance_transcription(self, content: str) -> Dict[str, Any]:
        """
        Clean up a raw voice transcription into readable prose (issue #56).

        Preview-only: returns the cleaned-up text and metadata without
        persisting. A single conservative pass removes filler words, breaks
        paragraphs at natural pauses, and fixes grammar/punctuation while
        preserving what was said. Mirrors enhance_text (#57) with temp 0.3.

        Args:
            content: The raw voice transcription to clean up.

        Returns:
            Dict with success flag, enhanced text, and metadata.
        """
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Transcription is required for cleanup.",
                "enhanced": "",
                "metadata": {},
            }

        try:
            prompt = get_transcription_enhancement_prompt(content)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert editor cleaning up dictated speech. "
                        "Turn raw transcriptions into readable prose while "
                        "preserving the speaker's words and meaning exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            # Conservative, like enhance_text: cleanup must not invent content.
            response = await self._make_openai_request(
                messages,
                temperature=0.3,
                max_tokens=rewrite_max_tokens(content),
                long_output=True,
            )

            choice = response.choices[0]
            # Refuse a truncated result: the caller would overwrite the chapter
            # with shortened text, silently losing content (mirrors #57).
            if getattr(choice, "finish_reason", None) == "length":
                return {
                    "success": False,
                    # Tagged so the route answers 413, not 503: a retry would be
                    # cut off at the same place (#801).
                    "error_code": "REWRITE_TRUNCATED",
                    "error": (
                        "This transcription is too long to clean up in one pass. "
                        "Try cleaning up a shorter section."
                    ),
                    "enhanced": "",
                    "metadata": {},
                }

            enhanced = choice.message.content
            shortened = shortened_rewrite_error(content, enhanced, CLEANUP_MIN_PERCENT_KEPT)
            if shortened:
                return {
                    "success": False,
                    "error_code": "REWRITE_SHORTENED",
                    "error": shortened,
                    "enhanced": "",
                    "metadata": {},
                }
            return {
                "success": True,
                "enhanced": enhanced,
                "metadata": {
                    "enhancement_type": "transcription",
                    "enhancement_label": TRANSCRIPTION_ENHANCEMENT_LABEL,
                    "original_word_count": word_count(content),
                    "enhanced_word_count": word_count(enhanced),
                    "model_used": self.long_output_model,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

        except AIServiceError:
            # The route turns it into its status: a 429 stays a 429 (#802).
            raise
        except Exception:
            logger.error("Failed to enhance transcription", exc_info=True)
            return {
                "success": False,
                "error": "The request could not be completed.",
                "enhanced": "",
                "metadata": {},
            }
