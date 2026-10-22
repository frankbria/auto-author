"""TOC-wizard question flows: summary analysis, clarifying and chapter questions (#922)."""
import re
import uuid
from typing import Dict, List, Optional, Any
from app.schemas.ai_input import MAX_QUESTION_CHARS
from app.services.ai_errors import AIServiceError
from app.services.ai.transport import (
    LIST_MARKER,
    SENTENCE_END,
    logger,
)


class TocFlowsMixin:
    """Summary analysis, clarifying questions and chapter questions."""

    async def analyze_summary_for_toc(
        self, summary: str, book_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze a book summary to determine its suitability for TOC generation.

        Args:
            summary: The book summary text
            book_metadata: Optional book metadata (title, genre, audience, etc.)

        Returns:
            Dict containing analysis results and readiness for TOC generation
        """
        try:
            # Prepare the prompt for summary analysis
            prompt = self._build_summary_analysis_prompt(summary, book_metadata)

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert book editor and content strategist. Analyze book summaries to determine their readiness for Table of Contents generation.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._make_openai_request(
                messages=messages, temperature=0.3, max_tokens=1000
            )

            # Parse the response
            analysis_text = self._untruncated_text(response)
            logger.info(
                f"Summary analysis completed for summary of {len(summary)} characters"
            )

            # Extract structured data from the response
            analysis = self._parse_analysis_response(analysis_text, summary)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing summary after all retries: {str(e)}")
            return {
                "is_ready_for_toc": False,
                "confidence_score": 0.0,
                "analysis": "Error occurred during analysis",
                "suggestions": ["Please try again later or contact support"],
                "error": str(e),
            }

    async def generate_clarifying_questions(
        self, summary: str, book_metadata: Optional[Dict] = None, num_questions: int = 4
    ) -> List[str]:
        """
        Generate clarifying questions based on the book summary to improve TOC generation.

        Args:
            summary: The book summary text
            book_metadata: Optional book metadata
            num_questions: Number of questions to generate (default: 4)

        Returns:
            List of clarifying questions

        Raises:
            AIServiceError: If generation fails
        """
        correlation_id = str(uuid.uuid4())

        try:
            # Generate new questions
            prompt = self._build_questions_prompt(summary, book_metadata, num_questions)

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert book editor. Generate insightful clarifying questions that will help create a better Table of Contents structure for non-fiction books.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._make_openai_request(
                messages=messages,
                temperature=0.4,
                max_tokens=800,
                correlation_id=correlation_id,
            )

            questions_text = self._untruncated_text(response, correlation_id)
            # The wizard sends each question back with its answer, where it is capped (#800).
            questions = [
                question[:MAX_QUESTION_CHARS]
                for question in self._parse_questions_response(questions_text)
            ]

            logger.info(
                f"Generated {len(questions)} clarifying questions "
                f"[correlation_id={correlation_id}]"
            )
            return questions

        except AIServiceError as e:
            logger.error(
                f"Error generating clarifying questions "
                f"[correlation_id={correlation_id}]: {str(e)}"
            )
            raise

    def _build_summary_analysis_prompt(
        self, summary: str, book_metadata: Optional[Dict]
    ) -> str:
        """Build the prompt for summary analysis."""
        metadata_context = ""
        if book_metadata:
            title = book_metadata.get("title", "")
            genre = (book_metadata.get("genre") or "")
            audience = (book_metadata.get("target_audience") or "")
            metadata_context = (
                f"\nBook Title: {title}\nGenre: {genre}\nTarget Audience: {audience}\n"
            )

        return f"""
Please analyze the following book summary for its readiness to generate a Table of Contents:

{metadata_context}
Summary:
{summary}

Evaluate the summary based on these criteria:
1. Clarity of main topic and scope
2. Sufficient detail about content structure
3. Clear target audience identification
4. Logical flow and organization hints
5. Actionable or educational content indicators

Provide your analysis in this format:
READINESS: [Ready/Needs Work/Not Ready]
CONFIDENCE: [0.0-1.0 score]
ANALYSIS: [Brief explanation of readiness assessment]
SUGGESTIONS: [2-3 specific suggestions for improvement if needed]

Keep your response concise and actionable.
"""

    def _build_questions_prompt(
        self, summary: str, book_metadata: Optional[Dict], num_questions: int
    ) -> str:
        """Build the prompt for generating clarifying questions."""
        metadata_context = ""
        if book_metadata:
            title = book_metadata.get("title", "")
            genre = (book_metadata.get("genre") or "")
            metadata_context = f"\nBook Title: {title}\nGenre: {genre}\n"

        return f"""
Based on this book summary, generate {num_questions} clarifying questions that would help create a better Table of Contents structure:

{metadata_context}
Summary:
{summary}

Generate questions that help clarify:
- Content organization and logical flow
- Target audience needs and expertise level
- Key concepts that need detailed coverage
- Practical applications or case studies
- Depth of coverage for different topics

Format your response as a numbered list of {num_questions} questions.
Make questions specific, actionable, and focused on content structure rather than general book details.
"""

    def _parse_analysis_response(
        self, analysis_text: str, original_summary: str
    ) -> Dict:
        """Parse the AI analysis response into structured data."""
        lines = analysis_text.strip().split("\n")

        # Default values
        is_ready = False
        confidence = 0.5
        analysis = "Analysis completed"
        suggestions = []
        in_suggestion_list = False

        # Parse the response
        for line in lines:
            line = line.strip()
            if line.startswith("READINESS:"):
                readiness = line.split(":", 1)[1].strip().lower()
                is_ready = "ready" in readiness and "not ready" not in readiness
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 0.5
            elif line.startswith("ANALYSIS:"):
                analysis = line.split(":", 1)[1].strip()
            elif line.startswith("SUGGESTIONS:"):
                suggestions_text = line.split(":", 1)[1].strip()
                # Split suggestions by common delimiters
                suggestions = [
                    s.strip() for s in SENTENCE_END.split(suggestions_text) if s.strip()
                ]
                # Open models put them on the following lines as a list (#917).
                in_suggestion_list = not suggestions
            elif in_suggestion_list and LIST_MARKER.match(line):
                suggestions.append(LIST_MARKER.sub("", line))
        # Additional metadata
        word_count = len(original_summary.split())
        char_count = len(original_summary)

        return {
            "is_ready_for_toc": is_ready,
            "confidence_score": confidence,
            "analysis": analysis,
            "suggestions": suggestions[:3],  # Limit to 3 suggestions
            "word_count": word_count,
            "character_count": char_count,
            "meets_minimum_requirements": word_count >= 30 and char_count >= 150,
        }

    def _parse_questions_response(self, questions_text: str) -> List[str]:
        """Parse the AI questions response into a list of questions."""
        lines = questions_text.strip().split("\n")
        questions = []

        for line in lines:
            line = line.strip()
            if LIST_MARKER.match(line):
                # Open models wrap items in markdown bold: "1. **Why...?**" (#917).
                cleaned = LIST_MARKER.sub("", line).strip().strip("*_").strip()
                if cleaned and cleaned.endswith("?"):
                    questions.append(cleaned)

        # If parsing failed, try splitting by question marks
        if not questions and "?" in questions_text:
            potential_questions = questions_text.split("?")
            questions = [q.strip() + "?" for q in potential_questions if q.strip()]

        # No questions could be recovered from the AI response. Substituting
        # hard-coded defaults here would be a silent failure (issue #202, same
        # class as the #48 TOC fix): canned content indistinguishable from AI
        # output. Surface a retryable error instead.
        if len(questions) == 0:
            correlation_id = str(uuid.uuid4())
            logger.warning(
                f"AI returned unparseable clarifying questions "
                f"[correlation_id={correlation_id}]"
            )
            raise AIServiceError(
                message="The AI returned unusable clarifying questions. Please try again.",
                error_code="AI_INVALID_RESPONSE",
                retryable=True,
                correlation_id=correlation_id,
            )

        return questions[:5]  # Limit to 5 questions max

    async def generate_chapter_questions(
        self, prompt: str, count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate interview-style questions for a chapter using AI.

        Args:
            prompt: The prompt containing chapter context and requirements
            count: Number of questions to generate

        Returns:
            List of question dictionaries
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert writing coach and interviewer. Generate thoughtful, engaging questions that help authors develop compelling chapter content. Focus on questions that unlock creativity, depth, and reader engagement."
                },
                {"role": "user", "content": prompt}
            ]

            response = await self._make_openai_request(
                messages=messages,
                temperature=0.7,  # Higher creativity for question generation
                max_tokens=2000
            )

            questions_text = self._untruncated_text(response)
            questions = self._parse_chapter_questions_response(questions_text)

            logger.info(f"Generated {len(questions)} questions for chapter")
            return questions

        except AIServiceError as e:
            # A genuine OpenAI failure must surface as a structured error (like
            # the TOC path), not masquerade as an empty result (#182).
            logger.error(f"AI service error generating chapter questions: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error generating chapter questions: {str(e)}")
            # Return empty list, fallback questions will be handled by the service
            return []

    def _parse_chapter_questions_response(self, questions_text: str) -> List[Dict[str, Any]]:
        """
        Parse the AI response containing chapter questions.

        Args:
            questions_text: Raw text response from AI

        Returns:
            List of question dictionaries
        """
        import json

        questions = []

        try:
            # Try to parse as JSON first
            json_match = re.search(r'\[.*\]', questions_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_questions = json.loads(json_str)

                if isinstance(parsed_questions, list):
                    for q in parsed_questions:
                        if isinstance(q, dict) and 'question_text' in q:
                            questions.append(q)
                    return questions
        except json.JSONDecodeError:
            logger.debug("Question text was not valid JSON; falling back to text parsing")

        # Fallback: parse structured text format
        lines = questions_text.strip().split('\n')
        current_question = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for question text
            if line.startswith('"question_text"') or 'question_text' in line:
                match = re.search(r'"question_text"\s*:\s*"([^"]+)"', line)
                if match:
                    current_question['question_text'] = match.group(1)
            elif line.startswith('"question_type"') or 'question_type' in line:
                match = re.search(r'"question_type"\s*:\s*"([^"]+)"', line)
                if match:
                    current_question['question_type'] = match.group(1)
            elif line.startswith('"difficulty"') or 'difficulty' in line:
                match = re.search(r'"difficulty"\s*:\s*"([^"]+)"', line)
                if match:
                    current_question['difficulty'] = match.group(1)
            elif line.startswith('"help_text"') or 'help_text' in line:
                match = re.search(r'"help_text"\s*:\s*"([^"]+)"', line)
                if match:
                    current_question['help_text'] = match.group(1)
            elif line.startswith('}') and current_question.get('question_text'):
                questions.append(current_question.copy())
                current_question = {}

        # If still no questions, try simple question extraction
        if not questions:
            for line in lines:
                if '?' in line and len(line.strip()) > 10:
                    # Extract just the question part
                    question_text = line.strip()
                    # Remove numbering, bullets, etc.
                    question_text = LIST_MARKER.sub('', question_text)
                    question_text = question_text.strip('"\'')

                    if question_text:
                        questions.append({
                            'question_text': question_text,
                            'question_type': 'plot',  # Default type
                            'difficulty': 'medium',   # Default difficulty
                            'help_text': 'Consider the key elements that would engage readers in this chapter.'
                        })

        return questions[:20]  # Limit to reasonable number
