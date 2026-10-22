"""TOC generation, its prompt, validation, parser and fallback (#922)."""
import re
import uuid
from typing import Dict, List, Optional
from app.services.ai_errors import AIServiceError
from app.services.ai.transport import (
    TOC_MAX_COMPLETION_TOKENS,
    logger,
)


class TocGenerationMixin:
    """Generates the Table of Contents from a summary and the wizard's answers."""

    async def generate_toc_from_summary_and_responses(
        self,
        summary: str,
        question_responses: List[Dict[str, str]],
        book_metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate a Table of Contents based on the book summary and user responses to clarifying questions.

        Args:
            summary: The book summary text
            question_responses: List of {"question": str, "answer": str} pairs
            book_metadata: Optional book metadata (title, genre, audience, etc.)

        Returns:
            Dict containing the generated TOC structure

        Raises:
            AIServiceError: If generation fails
        """
        correlation_id = str(uuid.uuid4())

        try:
            # Generate new TOC
            prompt = self._build_toc_generation_prompt(
                summary, question_responses, book_metadata
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert book editor and content strategist. Generate well-structured Table of Contents based on book summaries and clarifying question responses.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._make_openai_request(
                messages=messages,
                temperature=0.4,
                max_tokens=TOC_MAX_COMPLETION_TOKENS,
                correlation_id=correlation_id,
                long_output=True,
            )

            choice = response.choices[0]
            # Truncated JSON can never parse, and a retry hits the same limit
            # while spending quota: fail clearly and non-retryably (#774).
            if getattr(choice, "finish_reason", None) == "length":
                raise AIServiceError(
                    message=(
                        "The generated table of contents was cut off before it "
                        "finished. Try a shorter summary or fewer chapters."
                    ),
                    error_code="AI_RESPONSE_TRUNCATED",
                    retryable=False,
                    correlation_id=correlation_id,
                )

            toc_text = choice.message.content
            toc_result = self._parse_toc_response(toc_text)

            logger.info(
                f"Generated TOC [correlation_id={correlation_id}]"
            )
            return toc_result

        except AIServiceError as e:
            logger.error(
                f"Error generating TOC "
                f"[correlation_id={correlation_id}]: {str(e)}"
            )
            raise

    def _build_toc_generation_prompt(
        self,
        summary: str,
        question_responses: List[Dict[str, str]],
        book_metadata: Optional[Dict],
    ) -> str:
        """Build the prompt for TOC generation."""
        metadata_context = ""
        if book_metadata:
            title = book_metadata.get("title", "")
            genre = (book_metadata.get("genre") or "")
            audience = (book_metadata.get("target_audience") or "")
            metadata_context = (
                f"\nBook Title: {title}\nGenre: {genre}\nTarget Audience: {audience}\n"
            )

        responses_text = "\n".join(
            [
                f"Q: {resp['question']}\nA: {resp['answer']}"
                for resp in question_responses
            ]
        )

        return f"""
Generate a comprehensive Table of Contents for a book based on the following information:

{metadata_context}
Book Summary:
{summary}

Clarifying Questions and Responses:
{responses_text}

Create a hierarchical Table of Contents with:
- 6-12 main chapters
- 2-4 subchapters per chapter where appropriate
- Clear, descriptive chapter titles
- Brief descriptions for each chapter
- Logical flow from beginner to advanced topics (if applicable)
- Practical, actionable content organization

Format your response as JSON with this structure:
{{
  "chapters": [
    {{
      "id": "ch1",
      "title": "Chapter Title",
      "description": "Brief description of what this chapter covers",
      "level": 1,
      "order": 1,
      "subchapters": [
        {{
          "id": "ch1-1",
          "title": "Subchapter Title",
          "description": "Brief description",
          "level": 2,
          "order": 1
        }}
      ]
    }}
  ],
  "total_chapters": 8,
  "estimated_pages": 200,
  "structure_notes": "Brief explanation of the TOC organization logic"
}}

Ensure the TOC is comprehensive, logically ordered, and matches the book's scope and audience.
"""

    def _is_valid_toc(self, toc_data: Dict) -> bool:
        """A usable TOC has a non-empty chapter list where every chapter has a title.

        Guards against the AI returning 200 with unusable content (empty
        chapters, or chapters missing titles) that would otherwise be saved as a
        bogus "successful" TOC. See issue #48.
        """
        chapters = toc_data.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            return False
        return all(
            isinstance(ch, dict)
            and isinstance(ch.get("title"), str)
            and ch.get("title").strip()
            for ch in chapters
        )

    def _parse_toc_response(self, toc_text: str) -> Dict:
        """Parse the AI TOC response into a structured format.

        Raises AIServiceError (retryable) when the response can't be turned into
        a usable TOC, so the caller surfaces a clear error + retry instead of
        silently fabricating placeholder chapters.
        """
        import json

        try:
            json_match = re.search(r"\{.*\}", toc_text, re.DOTALL)
            if json_match:
                toc_data = json.loads(json_match.group(0))
                # The model sometimes wraps the structure under a
                # "table_of_contents" key — unwrap it before validating.
                if isinstance(toc_data.get("table_of_contents"), dict):
                    toc_data = toc_data["table_of_contents"]
                if self._is_valid_toc(toc_data):
                    return {
                        "toc": toc_data,
                        "success": True,
                        "chapters_count": len(toc_data["chapters"]),
                        "has_subchapters": any(
                            chapter.get("subchapters", [])
                            for chapter in toc_data["chapters"]
                        ),
                    }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Error parsing TOC JSON: {str(e)}")

        # No usable JSON — fall back to extracting chapters from plain text. This
        # raises if nothing usable can be recovered.
        return self._create_fallback_toc(toc_text)

    def _create_fallback_toc(self, toc_text: str) -> Dict:
        """Create a fallback TOC structure when parsing fails."""
        lines = toc_text.strip().split("\n")
        chapters = []
        chapter_count = 0

        for line in lines:
            line = line.strip()
            if line and (
                line.startswith("Chapter")
                or line.startswith("ch")
                or any(char.isdigit() for char in line[:5])
            ):
                chapter_count += 1
                chapters.append(
                    {
                        "id": f"ch{chapter_count}",
                        "title": line,
                        "description": "Chapter content to be developed",
                        "level": 1,
                        "order": chapter_count,
                        "subchapters": [],
                    }
                )

        # No chapters could be recovered from the AI response. Fabricating a
        # generic placeholder TOC here would be a silent failure (issue #48):
        # the user would get boilerplate content labelled as a success. Surface
        # a retryable error instead so the UI can show it and offer regeneration.
        if not chapters:
            correlation_id = str(uuid.uuid4())
            logger.warning(
                f"AI returned an unusable TOC; no chapters recoverable "
                f"[correlation_id={correlation_id}]"
            )
            raise AIServiceError(
                message="The AI returned an unusable table of contents. Please try again.",
                error_code="AI_INVALID_RESPONSE",
                retryable=True,
                correlation_id=correlation_id,
            )

        return {
            "toc": {
                "chapters": chapters,
                "total_chapters": len(chapters),
                "estimated_pages": len(chapters) * 25,
                "structure_notes": "Generated TOC structure based on summary analysis",
            },
            "success": True,
            "chapters_count": len(chapters),
            "has_subchapters": False,
        }
