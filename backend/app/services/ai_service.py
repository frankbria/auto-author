# backend/app/services/ai_service.py
import openai
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    AI Service for handling OpenAI API interactions for summary analysis and TOC generation.
    Includes retry mechanism for failed requests.
    """

    def __init__(self):
        """Initialize the AI service with OpenAI client."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"  # Using GPT-4 for better analysis capabilities
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.max_delay = 60.0  # Maximum delay between retries

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry mechanism.

        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Attempting API call (attempt {attempt + 1}/{self.max_retries})"
                )
                return await func(*args, **kwargs)

            except openai.RateLimitError as e:
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for rate limit error")

            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"API timeout/connection error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for API timeout/connection error")

            except openai.InternalServerError as e:
                last_exception = e
                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"OpenAI server error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for server error")

            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Non-retryable error occurred: {str(e)}")
                raise e

        # If we've exhausted all retries, raise the last exception
        raise last_exception

    async def _make_openai_request(
        self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 1000
    ):
        """
        Make an OpenAI API request with retry logic.

        Args:
            messages: List of message dictionaries for the chat completion
            temperature: Temperature for response generation
            max_tokens: Maximum tokens for the response

        Returns:
            OpenAI response object
        """

        def _sync_request():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        async def _async_wrapper():
            return _sync_request()

        return await self._retry_with_backoff(_async_wrapper)

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
            analysis_text = response.choices[0].message.content
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
        """
        try:
            prompt = self._build_questions_prompt(summary, book_metadata, num_questions)

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert book editor. Generate insightful clarifying questions that will help create a better Table of Contents structure for non-fiction books.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self._make_openai_request(
                messages=messages, temperature=0.4, max_tokens=800
            )

            questions_text = response.choices[0].message.content
            questions = self._parse_questions_response(questions_text)

            logger.info(f"Generated {len(questions)} clarifying questions for summary")
            return questions

        except Exception as e:
            logger.error(
                f"Error generating clarifying questions after all retries: {str(e)}"
            )
            # Return fallback questions
            return [
                "What is the main problem or challenge your book addresses?",
                "Who is your target audience and what level of expertise do they have?",
                "What are the 3-5 key concepts or topics you want to cover?",
                "What practical outcomes should readers achieve after reading your book?",
            ]

    def _build_summary_analysis_prompt(
        self, summary: str, book_metadata: Optional[Dict]
    ) -> str:
        """Build the prompt for summary analysis."""
        metadata_context = ""
        if book_metadata:
            title = book_metadata.get("title", "")
            genre = book_metadata.get("genre", "")
            audience = book_metadata.get("target_audience", "")
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
            genre = book_metadata.get("genre", "")
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

        # Parse the response
        for line in lines:
            line = line.strip()
            if line.startswith("READINESS:"):
                readiness = line.split(":", 1)[1].strip().lower()
                is_ready = "ready" in readiness and "not ready" not in readiness
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except:
                    confidence = 0.5
            elif line.startswith("ANALYSIS:"):
                analysis = line.split(":", 1)[1].strip()
            elif line.startswith("SUGGESTIONS:"):
                suggestions_text = line.split(":", 1)[1].strip()
                # Split suggestions by common delimiters
                suggestions = [
                    s.strip() for s in suggestions_text.split(".") if s.strip()
                ]
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
            # Remove numbering and clean up
            if line and (
                line[0].isdigit() or line.startswith("-") or line.startswith("•")
            ):
                # Remove number prefix (1., 2), etc.)
                cleaned = line.split(".", 1)[-1].strip()
                if cleaned and cleaned.endswith("?"):
                    questions.append(cleaned)

        # If parsing failed, try splitting by question marks
        if not questions and "?" in questions_text:
            potential_questions = questions_text.split("?")
            questions = [q.strip() + "?" for q in potential_questions if q.strip()]

        # Fallback to default questions if still no valid questions found
        if len(questions) == 0:
            questions = [
                "What is the main problem your book solves?",
                "Who is your target audience?",
                "What are the key topics you want to cover?",
                "What should readers be able to do after reading your book?",
            ]

        return questions[:5]  # Limit to 5 questions max

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
        """
        try:
            # Prepare the prompt for TOC generation
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
                messages=messages, temperature=0.4, max_tokens=1500
            )

            toc_text = response.choices[0].message.content
            return self._parse_toc_response(toc_text)

        except Exception as e:
            logger.error(f"Error generating TOC after all retries: {str(e)}")
            raise Exception(f"Failed to generate TOC: {str(e)}")

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
            genre = book_metadata.get("genre", "")
            audience = book_metadata.get("target_audience", "")
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

    def _parse_toc_response(self, toc_text: str) -> Dict:
        """Parse the AI TOC response into a structured format."""
        try:
            # Try to extract JSON from the response
            import json
            import re

            # Look for JSON content between curly braces
            json_match = re.search(r"\{.*\}", toc_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                toc_data = json.loads(json_str)

                # Validate required fields
                if "chapters" in toc_data and isinstance(toc_data["chapters"], list):
                    return {
                        "toc": toc_data,
                        "success": True,
                        "chapters_count": len(toc_data["chapters"]),
                        "has_subchapters": any(
                            chapter.get("subchapters", [])
                            for chapter in toc_data["chapters"]
                        ),
                    }

            # Fallback: Create a simple structure from text
            return self._create_fallback_toc(toc_text)

        except Exception as e:
            logger.warning(f"Error parsing TOC response: {str(e)}")
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

        # If no chapters found, create default structure
        if not chapters:
            chapters = [
                {
                    "id": "ch1",
                    "title": "Introduction",
                    "description": "Introduction to the topic",
                    "level": 1,
                    "order": 1,
                    "subchapters": [],
                },
                {
                    "id": "ch2",
                    "title": "Main Content",
                    "description": "Core content of the book",
                    "level": 1,
                    "order": 2,
                    "subchapters": [],
                },
                {
                    "id": "ch3",
                    "title": "Conclusion",
                    "description": "Summary and next steps",
                    "level": 1,
                    "order": 3,
                    "subchapters": [],
                },
            ]

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


# Singleton instance
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
            
            questions_text = response.choices[0].message.content
            questions = self._parse_chapter_questions_response(questions_text)
            
            logger.info(f"Generated {len(questions)} questions for chapter")
            return questions
            
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
        import re
        
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
            pass
        
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
            question_lines = []
            for line in lines:
                if '?' in line and len(line.strip()) > 10:
                    # Extract just the question part
                    question_text = line.strip()
                    # Remove numbering, bullets, etc.
                    question_text = re.sub(r'^[\d\.\-\*\•]\s*', '', question_text)
                    question_text = question_text.strip('"\'')
                    
                    if question_text:
                        questions.append({
                            'question_text': question_text,
                            'question_type': 'plot',  # Default type
                            'difficulty': 'medium',   # Default difficulty
                            'help_text': 'Consider the key elements that would engage readers in this chapter.'
                        })
        
        return questions[:20]  # Limit to reasonable number

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
            
            response = await self._make_openai_request(
                messages, temperature=0.8
            )
            
            draft_content = response.choices[0].message.content
            
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
                    "model_used": self.model,
                    "writing_style": writing_style or "default",
                    "target_length": target_length,
                    "actual_length": word_count
                },
                "suggestions": self._generate_improvement_suggestions(draft_content)
            }
            
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
            genre = book_metadata.get("genre", "")
            audience = book_metadata.get("target_audience", "")
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

Chapter Title: {chapter_title}
Chapter Description: {chapter_description}
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


ai_service = AIService()
