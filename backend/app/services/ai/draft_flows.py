"""Chapter draft generation and its prompt (#922)."""
import time
from typing import Dict, List, Optional, Any
from app.schemas.ai_input import (
    MAX_CHAPTER_DESCRIPTION_CHARS,
    MAX_CHAPTER_TITLE_CHARS,
)
from app.services.ai_errors import AIServiceError
from app.services.ai.transport import (
    DRAFT_WORDS_TO_TOKENS_FACTOR,
    logger,
)


class DraftFlowsMixin:
    """Generates chapter drafts from interview answers."""

    async def generate_chapter_draft(
        self,
        chapter_title: str,
        chapter_description: str,
        question_responses: List[Dict[str, str]],
        book_metadata: Optional[Dict] = None,
        writing_style: Optional[str] = None,
        target_length: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a draft chapter based on Q&A responses using AI.

        Args:
            chapter_title: Title of the chapter
            chapter_description: Brief description of chapter content
            question_responses: List of Q&A pairs from interview questions
            book_metadata: Optional book metadata (title, genre, audience)
            writing_style: Optional writing style preference
            target_length: Target word count for the chapter

        Returns:
            Dict containing the generated draft and metadata
        """
        try:
            prompt = self._build_draft_generation_prompt(
                chapter_title,
                chapter_description,
                question_responses,
                book_metadata,
                writing_style,
                target_length
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a skilled ghostwriter and content creator. Transform interview responses into engaging, well-structured narrative content that flows naturally while preserving the author's voice and ideas."
                },
                {"role": "user", "content": prompt}
            ]

            # Floor of 500 gives small targets headroom so a modest overshoot
            # can't spuriously trip the truncation guard below.
            max_tokens = max(int(target_length * DRAFT_WORDS_TO_TOKENS_FACTOR), 500)
            response = await self._make_openai_request(
                messages,
                temperature=0.8,
                max_tokens=max_tokens,
                long_output=True,
            )

            choice = response.choices[0]
            # Refuse to return a truncated draft: it would be inserted into the
            # editor as-is with success:true, silently losing content (#181).
            if getattr(choice, "finish_reason", None) == "length":
                return {
                    "success": False,
                    # Tagged so the endpoint can map this to 422 rather than 503:
                    # the request hit a model output limit, which the user fixes
                    # by asking for less. "Service unavailable" tells them to
                    # wait and retry, which will fail identically (#352).
                    "error_code": "DRAFT_TRUNCATED",
                    "error": (
                        "The generated draft was cut off before it finished. "
                        "Try a shorter target length."
                    ),
                    "draft": "",
                    "metadata": {},
                }

            draft_content = choice.message.content

            # Calculate metadata
            word_count = len(draft_content.split())
            estimated_reading_time = max(1, word_count // 200)  # ~200 words per minute

            return {
                "success": True,
                "draft": draft_content,
                "metadata": {
                    "word_count": word_count,
                    "estimated_reading_time": estimated_reading_time,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "model_used": self.long_output_model,
                    "writing_style": writing_style or "default",
                    "target_length": target_length,
                    "actual_length": word_count
                },
                "suggestions": self._generate_improvement_suggestions(draft_content)
            }

        except AIServiceError:
            # Let the structured error through. Flattening it to str(e) here
            # discarded error_code, retryable and retry_after, so the endpoint
            # could only answer 503 — losing the rate-limit backoff hint and the
            # distinction between "try later" and "this request is wrong" (#352).
            raise
        except Exception as e:
            logger.error(f"Failed to generate chapter draft: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "draft": "",
                "metadata": {}
            }

    def _build_draft_generation_prompt(
        self,
        chapter_title: str,
        chapter_description: str,
        question_responses: List[Dict[str, str]],
        book_metadata: Optional[Dict],
        writing_style: Optional[str],
        target_length: int
    ) -> str:
        """Build the prompt for draft generation."""
        metadata_context = ""
        if book_metadata:
            title = book_metadata.get("title", "")
            genre = (book_metadata.get("genre") or "")
            audience = (book_metadata.get("target_audience") or "")
            metadata_context = f"""
Book Context:
- Title: {title}
- Genre: {genre}
- Target Audience: {audience}
"""

        style_instruction = ""
        if writing_style:
            style_instruction = f"\nWriting Style: {writing_style}"

        responses_text = "\n\n".join([
            f"Question: {resp['question']}\nAuthor's Response: {resp['answer']}"
            for resp in question_responses
        ])

        return f"""
Generate a compelling chapter draft based on the following information:

Chapter Title: {str(chapter_title or "")[:MAX_CHAPTER_TITLE_CHARS]}
Chapter Description: {str(chapter_description or "")[:MAX_CHAPTER_DESCRIPTION_CHARS]}
{metadata_context}{style_instruction}
Target Length: Approximately {target_length} words

Interview Q&A Responses:
{responses_text}

Please create a well-structured chapter that:
1. Opens with an engaging hook that draws readers in
2. Transforms the Q&A responses into a natural narrative flow
3. Includes concrete examples and details from the responses
4. Maintains the author's voice and perspective
5. Uses appropriate formatting (paragraphs, subheadings if needed)
6. Concludes with a clear takeaway or transition
7. Aims for approximately {target_length} words

Write in a style that is {writing_style or 'engaging, clear, and appropriate for the target audience'}.

Format the output as clean, ready-to-edit prose with proper paragraph breaks.
"""

    def _generate_improvement_suggestions(self, draft_content: str) -> List[str]:
        """Generate suggestions for improving the draft."""
        suggestions = []

        # Basic analysis
        word_count = len(draft_content.split())
        sentence_count = len([s for s in draft_content.split('.') if s.strip()])
        avg_sentence_length = word_count / max(sentence_count, 1)

        if word_count < 500:
            suggestions.append("Consider expanding the content with more examples and details")
        elif word_count > 3000:
            suggestions.append("Consider breaking this into multiple chapters or sections")

        if avg_sentence_length > 25:
            suggestions.append("Some sentences may be too long - consider breaking them up for clarity")
        elif avg_sentence_length < 10:
            suggestions.append("Sentences seem short - consider combining some for better flow")

        if draft_content.count('\n\n') < 3:
            suggestions.append("Add more paragraph breaks to improve readability")

        if not any(word in draft_content.lower() for word in ['example', 'for instance', 'such as']):
            suggestions.append("Consider adding specific examples to illustrate key points")

        return suggestions
