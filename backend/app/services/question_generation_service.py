from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from app.schemas.book import (
    QuestionCreate, 
    Question,
    QuestionResponse, 
    QuestionResponseCreate,
    QuestionRating,
    QuestionProgressResponse,
    QuestionListResponse,
    GenerateQuestionsResponse,
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionMetadata
)
from app.services.ai_service import AIService
from app.utils.validators import validate_text_safety
from app.db.database import (
    create_question,
    get_questions_for_chapter as db_get_questions_for_chapter,
    save_question_response as db_save_question_response,
    get_question_response as db_get_question_response,
    save_question_rating as db_save_question_rating,
    get_chapter_question_progress as db_get_chapter_question_progress,
    delete_questions_for_chapter,
    get_question_by_id,
    get_book_by_id,
)

logger = logging.getLogger(__name__)

class QuestionGenerationService:
    """Service for generating and managing chapter-specific questions."""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
    
    async def generate_questions_for_chapter(
        self,
        book_id: str,
        chapter_id: str,
        count: int = 10,
        difficulty: Optional[str] = None,
        focus: Optional[List[str]] = None,
        user_id: str = None,
        current_user: Dict[str, Any] = None
    ) -> GenerateQuestionsResponse:
        """
        Generate interview-style questions for a specific chapter and save them to the database.
        
        Args:
            book_id: The ID of the book
            chapter_id: The ID of the chapter
            count: Number of questions to generate (default: 10)
            difficulty: Optional difficulty level for questions
            focus: Optional list of question types to focus on
            user_id: User ID for storing questions
            current_user: Current user context
            
        Returns:
            GenerateQuestionsResponse with generated questions
        """
        logger.info(
            f"Generating {count} questions for chapter {chapter_id} in book {book_id}"
        )
        
        # Get book and chapter info
        book = await get_book_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        
        # Find chapter in TOC
        chapter_title = "Chapter"
        chapter_content = ""
        chapter_description = ""
        
        def find_chapter(chapters):
            for ch in chapters:
                if ch.get("id") == chapter_id:
                    return ch
                if ch.get("subchapters"):
                    found = find_chapter(ch["subchapters"])
                    if found:
                        return found
            return None
        
        toc = book.get("table_of_contents", {})
        chapters = toc.get("chapters", [])
        chapter = find_chapter(chapters)
        
        if chapter:
            chapter_title = chapter.get("title", "Chapter")
            chapter_content = chapter.get("content", "")
            chapter_description = chapter.get("description", "")
        
        # Prepare book metadata
        book_metadata = {
            "title": book.get("title", ""),
            "genre": book.get("genre", ""),
            "target_audience": book.get("target_audience", ""),
        }
        
        # Convert difficulty and focus to enum types
        difficulty_enum = None
        if difficulty:
            try:
                difficulty_enum = QuestionDifficulty(difficulty)
            except ValueError:
                difficulty_enum = QuestionDifficulty.MEDIUM
        
        focus_types = []
        if focus:
            for f in focus:
                try:
                    focus_types.append(QuestionType(f))
                except ValueError:
                    continue
        
        # Limit question count to reasonable range
        count = max(3, min(count, 20))
        
        # Generate questions using AI
        try:
            questions = await self.generate_chapter_questions(
                book_id=book_id,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chapter_content=chapter_content,
                book_metadata=book_metadata,
                count=count,
                difficulty=difficulty_enum,
                focus_types=focus_types
            )
            
            # Save questions to database
            saved_questions = []
            for question in questions:
                saved_question_dict = await create_question(question, user_id or current_user.get("clerk_id"))
                try:
                    # Convert dict to Question object
                    saved_question = Question(**saved_question_dict)
                    saved_questions.append(saved_question)
                except Exception as e:
                    logger.error(f"Error converting question dict to Question object: {e}")
                    logger.error(f"Question dict keys: {list(saved_question_dict.keys())}")
                    logger.error(f"Question dict: {saved_question_dict}")
                    raise
            
            logger.info(f"Saved {len(saved_questions)} questions to database")
            
            try:
                response = GenerateQuestionsResponse(
                    questions=saved_questions,
                    generation_id=str(uuid.uuid4()),
                    total=len(saved_questions)
                )
                return response
            except Exception as e:
                logger.error(f"Error creating GenerateQuestionsResponse: {e}")
                raise
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise e
    
    async def get_questions_for_chapter(
        self,
        book_id: str,
        chapter_id: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        question_type: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> QuestionListResponse:
        """Get questions for a specific chapter with optional filtering."""
        # Use current user ID - this should be passed in or retrieved from context
        user_id = "current_user_id"  # TODO: Get from request context
        
        return await db_get_questions_for_chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=user_id,
            status=status,
            category=category,
            question_type=question_type,
            page=page,
            limit=limit
        )
    
    async def save_question_response(
        self,
        book_id: str,
        chapter_id: str,
        question_id: str,
        response_data: QuestionResponseCreate,
        user_id: str
    ) -> Dict[str, Any]:
        """Save or update a question response."""
        # Validate that the question exists and belongs to the user
        question = await get_question_by_id(question_id, user_id)
        if not question:
            raise ValueError("Question not found or access denied")
        
        if question["book_id"] != book_id or question["chapter_id"] != chapter_id:
            raise ValueError("Question does not belong to the specified book/chapter")
        
        return await db_save_question_response(question_id, response_data, user_id)
    
    async def get_question_response(
        self,
        question_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a question response."""
        return await db_get_question_response(question_id, user_id)
    
    async def save_question_rating(
        self,
        question_id: str,
        rating_data: QuestionRating,
        user_id: str
    ) -> Dict[str, Any]:
        """Save or update a question rating."""
        # Validate that the question exists and belongs to the user
        question = await get_question_by_id(question_id, user_id)
        if not question:
            raise ValueError("Question not found or access denied")
        
        return await db_save_question_rating(question_id, rating_data, user_id)
    
    async def get_chapter_question_progress(
        self,
        book_id: str,
        chapter_id: str,
        user_id: str
    ) -> QuestionProgressResponse:
        """Get question progress for a chapter."""
        return await db_get_chapter_question_progress(book_id, chapter_id, user_id)
    
    async def regenerate_chapter_questions(
        self,
        book_id: str,
        chapter_id: str,
        count: int = 10,
        difficulty: Optional[str] = None,
        focus: Optional[List[str]] = None,
        user_id: str = None,
        current_user: Dict[str, Any] = None,
        preserve_responses: bool = True
    ) -> GenerateQuestionsResponse:
        """
        Regenerate questions for a chapter, optionally preserving existing responses.
        """
        logger.info(
            f"Regenerating {count} questions for chapter {chapter_id} in book {book_id}, "
            f"preserve_responses={preserve_responses}"
        )
        
        user_id = user_id or current_user.get("clerk_id")
        
        # Delete existing questions (preserving those with responses if requested)
        deleted_count = await delete_questions_for_chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=user_id,
            preserve_with_responses=preserve_responses
        )
        
        # Generate new questions to replace deleted ones
        new_count = count if not preserve_responses else deleted_count
        if new_count > 0:
            result = await self.generate_questions_for_chapter(
                book_id=book_id,
                chapter_id=chapter_id,
                count=new_count,
                difficulty=difficulty,
                focus=focus,
                user_id=user_id,
                current_user=current_user
            )
            
            # Add metadata about the regeneration
            result.preserved_count = count - deleted_count if preserve_responses else 0
            result.new_count = new_count
            result.total = result.preserved_count + result.new_count
            
            return result
        else:
            # No questions were deleted, return empty result
            return GenerateQuestionsResponse(
                questions=[],
                generation_id=str(uuid.uuid4()),
                total=0
            )
    
    async def generate_chapter_questions(
        self,
        book_id: str,
        chapter_id: str,
        chapter_title: str,
        chapter_content: str,
        book_metadata: Dict[str, Any],
        count: int = 10,
        difficulty: Optional[QuestionDifficulty] = None,
        focus_types: Optional[List[QuestionType]] = None
    ) -> List[QuestionCreate]:
        """
        Generate interview-style questions for a specific chapter.
        
        Args:
            book_id: The ID of the book
            chapter_id: The ID of the chapter
            chapter_title: The title of the chapter
            chapter_content: The content of the chapter (if available)
            book_metadata: Metadata about the book (genre, audience, etc.)
            count: Number of questions to generate (default: 10)
            difficulty: Optional difficulty level for questions
            focus_types: Optional list of question types to focus on
            
        Returns:
            List of generated questions
        """
        logger.info(
            f"Generating {count} questions for chapter {chapter_id} in book {book_id}"
        )
        
        # Limit question count to reasonable range
        count = max(3, min(count, 20))
        
        # Prepare question generation prompt
        prompt = self._build_question_generation_prompt(
            chapter_title=chapter_title,
            chapter_content=chapter_content,
            book_metadata=book_metadata,
            count=count,
            difficulty=difficulty,
            focus_types=focus_types
        )
        
        # Generate questions using AI service
        try:
            raw_questions = await self.ai_service.generate_chapter_questions(prompt, count)
            
            # Process and validate questions
            questions = self._process_generated_questions(
                raw_questions=raw_questions,
                book_id=book_id,
                chapter_id=chapter_id,
                count=count,
                requested_difficulty=difficulty,
                requested_focus_types=focus_types
            )
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            # Fallback to template questions if AI generation fails
            return self._generate_fallback_questions(
                book_id=book_id,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                count=count,
                difficulty=difficulty,
                focus_types=focus_types
            )
    
    def _build_question_generation_prompt(
        self,
        chapter_title: str,
        chapter_content: str,
        book_metadata: Dict[str, Any],
        count: int,
        difficulty: Optional[QuestionDifficulty] = None,
        focus_types: Optional[List[QuestionType]] = None
    ) -> str:
        """Build the prompt for generating questions."""
        
        # Extract relevant metadata
        genre = book_metadata.get("genre", "")
        audience = book_metadata.get("audience", "")
        book_title = book_metadata.get("title", "")
        
        # Create base prompt
        prompt = f"""
        Generate {count} thoughtful interview-style questions about the chapter titled "{chapter_title}" 
        from the book "{book_title}".
        
        These questions should help the author develop their chapter content by exploring key aspects that readers 
        would want to understand. The questions should be diverse and cover important elements that would make 
        the chapter compelling and complete.
        """
        
        # Add content context if available
        if chapter_content:
            # Truncate content if too long
            content_excerpt = chapter_content[:5000] + "..." if len(chapter_content) > 5000 else chapter_content
            prompt += f"""
            The current chapter content is:
            ---
            {content_excerpt}
            ---
            
            Based on this content, generate questions that will help the author expand and improve the chapter.
            """
        else:
            prompt += f"""
            The chapter does not have any content yet. Generate questions that will help the author create initial 
            content for this chapter based on the title.
            """
        
        # Add genre and audience context
        if genre or audience:
            prompt += "\n\nAdditional context:"
            if genre:
                prompt += f"\n- This is a {genre} book."
            if audience:
                prompt += f"\n- The target audience is {audience}."
        
        # Add difficulty guidance
        if difficulty:
            difficulty_guidance = {
                QuestionDifficulty.EASY: "straightforward and focused on basic elements",
                QuestionDifficulty.MEDIUM: "moderately challenging and requiring thoughtful consideration",
                QuestionDifficulty.HARD: "challenging and requiring deep analysis or creative thinking"
            }
            prompt += f"\n\nMake the questions {difficulty_guidance.get(difficulty, '')}."
        
        # Add focus type guidance
        if focus_types and len(focus_types) > 0:
            focus_descriptions = []
            for focus in focus_types:
                if focus == QuestionType.CHARACTER:
                    focus_descriptions.append("character development, motivations, relationships, and arcs")
                elif focus == QuestionType.PLOT:
                    focus_descriptions.append("plot structure, events, conflicts, and narrative progression")
                elif focus == QuestionType.SETTING:
                    focus_descriptions.append("setting details, world-building, atmosphere, and environment")
                elif focus == QuestionType.THEME:
                    focus_descriptions.append("themes, messages, symbolism, and deeper meaning")
                elif focus == QuestionType.RESEARCH:
                    focus_descriptions.append("research needs, factual accuracy, and technical details")
            
            if focus_descriptions:
                focus_text = ", ".join(focus_descriptions)
                prompt += f"\n\nFocus the questions primarily on {focus_text}."
        
        # Add question structure guidance
        prompt += """
        
        Format each question as a JSON object with the following structure:
        {
            "question_text": "The actual question to ask the author",
            "question_type": "character|plot|setting|theme|research",
            "difficulty": "easy|medium|hard",
            "help_text": "Optional guidance to help the author answer the question",
            "examples": ["Optional example 1", "Optional example 2"]
        }
        
        Return the questions as a JSON array of these objects.
        """
        
        return prompt
    
    def _process_generated_questions(
        self,
        raw_questions: List[Dict[str, Any]],
        book_id: str,
        chapter_id: str,
        count: int,
        requested_difficulty: Optional[QuestionDifficulty] = None,
        requested_focus_types: Optional[List[QuestionType]] = None
    ) -> List[QuestionCreate]:
        """Process and validate the raw questions from the AI service."""
        
        processed_questions = []
        
        # Ensure we have at least some questions
        if not raw_questions or len(raw_questions) == 0:
            return self._generate_fallback_questions(
                book_id=book_id,
                chapter_id=chapter_id,
                chapter_title="Chapter",
                count=count,
                difficulty=requested_difficulty,
                focus_types=requested_focus_types
            )
        
        # Process each question
        for i, q in enumerate(raw_questions):
            try:
                # Extract fields with validation
                question_text = q.get("question_text", "").strip()
                
                # Validate question text
                if not question_text or len(question_text) < 10:
                    continue
                
                # Check content safety
                if not validate_text_safety(question_text):
                    continue
                
                # Parse question type
                raw_type = q.get("question_type", "").lower()
                if raw_type == "character":
                    question_type = QuestionType.CHARACTER
                elif raw_type == "plot":
                    question_type = QuestionType.PLOT
                elif raw_type == "setting":
                    question_type = QuestionType.SETTING
                elif raw_type == "theme":
                    question_type = QuestionType.THEME
                elif raw_type == "research":
                    question_type = QuestionType.RESEARCH
                else:
                    # Default to a random type if not specified or invalid
                    question_types = [t for t in QuestionType]
                    question_type = question_types[i % len(question_types)]
                
                # Parse difficulty
                raw_difficulty = q.get("difficulty", "").lower()
                if raw_difficulty == "easy":
                    difficulty = QuestionDifficulty.EASY
                elif raw_difficulty == "medium":
                    difficulty = QuestionDifficulty.MEDIUM
                elif raw_difficulty == "hard":
                    difficulty = QuestionDifficulty.HARD
                else:
                    # Use requested difficulty or default to medium
                    difficulty = requested_difficulty or QuestionDifficulty.MEDIUM
                
                # Process help text and examples
                help_text = q.get("help_text", "").strip()
                examples = q.get("examples", [])
                if isinstance(examples, list):
                    examples = [ex for ex in examples if isinstance(ex, str)]
                else:
                    examples = []
                
                # Create metadata
                metadata = QuestionMetadata(
                    suggested_response_length=self._get_suggested_length(difficulty),
                    help_text=help_text if help_text else None,
                    examples=examples if examples else None
                )
                
                # Create question
                question = QuestionCreate(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    question_text=question_text,
                    question_type=question_type,
                    difficulty=difficulty,
                    category="development",
                    order=i + 1,
                    metadata=metadata
                )
                
                processed_questions.append(question)
                
            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                continue
        
        # If we have too few questions, add some fallback ones
        if len(processed_questions) < min(3, count):
            fallback_questions = self._generate_fallback_questions(
                book_id=book_id,
                chapter_id=chapter_id,
                chapter_title="Chapter",
                count=max(3, count - len(processed_questions)),
                difficulty=requested_difficulty,
                focus_types=requested_focus_types
            )
            processed_questions.extend(fallback_questions)
        
        # Limit to requested count
        return processed_questions[:count]
    
    def _generate_fallback_questions(
        self,
        book_id: str,
        chapter_id: str,
        chapter_title: str,
        count: int = 5,
        difficulty: Optional[QuestionDifficulty] = None,
        focus_types: Optional[List[QuestionType]] = None
    ) -> List[QuestionCreate]:
        """Generate fallback questions if AI generation fails."""
        
        logger.info(f"Generating {count} fallback questions for chapter {chapter_id}")
        
        # Default difficulty
        if not difficulty:
            difficulty = QuestionDifficulty.MEDIUM
        
        # Default focus types to use all types
        if not focus_types or len(focus_types) == 0:
            focus_types = [t for t in QuestionType]
        
        # Template questions by type
        templates = {
            QuestionType.CHARACTER: [
                "Who are the main characters in this chapter and what are their key traits?",
                "How does the protagonist change or develop during this chapter?",
                "What motivates the main character's actions in this chapter?",
                "What conflicts or tensions exist between characters in this chapter?",
                "How do the relationships between characters evolve in this chapter?"
            ],
            QuestionType.PLOT: [
                f"What is the main event or conflict in {chapter_title}?",
                "How does this chapter advance the overall story?",
                "What obstacles or challenges arise in this chapter?",
                "Is there a turning point or climax in this chapter?",
                "How does this chapter connect to previous and future events in the story?"
            ],
            QuestionType.SETTING: [
                "Where does this chapter take place and how is the setting described?",
                "How does the environment or atmosphere contribute to the mood of the chapter?",
                "What sensory details (sights, sounds, smells) bring the setting to life?",
                "How does the setting influence the characters or events in this chapter?",
                "Are there any changes to the setting during this chapter?"
            ],
            QuestionType.THEME: [
                "What themes or messages are explored in this chapter?",
                "What symbols or motifs appear in this chapter?",
                "How does this chapter contribute to the book's overall meaning?",
                "What moral dilemmas or philosophical questions arise in this chapter?",
                "How might different readers interpret the events of this chapter?"
            ],
            QuestionType.RESEARCH: [
                "What research might be needed to make this chapter more authentic?",
                "Are there any technical details that require verification?",
                "What historical, cultural, or scientific facts are relevant to this chapter?",
                "Are there any specialized terms or concepts that need explanation?",
                "What expert knowledge would enhance the realism of this chapter?"
            ]
        }
        
        # Helper metadata by type
        helper_metadata = {
            QuestionType.CHARACTER: {
                "help_text": "Consider physical traits, psychological aspects, backstory, and character development.",
                "examples": ["The protagonist shows determination through her decision to confront her fear"]
            },
            QuestionType.PLOT: {
                "help_text": "Focus on the sequence of events, cause and effect, conflicts, and resolution.",
                "examples": ["The discovery of the map sets in motion a chain of events that leads to..."]
            },
            QuestionType.SETTING: {
                "help_text": "Include time, place, atmosphere, and how the setting affects the story.",
                "examples": ["The dark, narrow alleyways create a sense of claustrophobia that mirrors the character's mental state"]
            },
            QuestionType.THEME: {
                "help_text": "Think about underlying messages, symbols, and deeper meaning.",
                "examples": ["The recurring image of birds represents freedom and the character's desire to escape"]
            },
            QuestionType.RESEARCH: {
                "help_text": "Consider what facts, terminology, or technical details need verification.",
                "examples": ["The medical procedure described would require research on current surgical practices"]
            }
        }
        
        # Generate questions
        questions = []
        for i in range(count):
            # Select question type from focus types (cycling through them)
            question_type = focus_types[i % len(focus_types)]
            
            # Select question template
            templates_for_type = templates[question_type]
            template_idx = i % len(templates_for_type)
            question_text = templates_for_type[template_idx]
            
            # Get helper metadata
            helper_data = helper_metadata[question_type]
            metadata = QuestionMetadata(
                suggested_response_length=self._get_suggested_length(difficulty),
                help_text=helper_data.get("help_text"),
                examples=helper_data.get("examples")
            )
            
            # Create question
            question = QuestionCreate(
                book_id=book_id,
                chapter_id=chapter_id,
                question_text=question_text,
                question_type=question_type,
                difficulty=difficulty,
                category="development",
                order=i + 1,
                metadata=metadata
            )
            
            questions.append(question)
        
        return questions
    
    def _get_suggested_length(self, difficulty: QuestionDifficulty) -> str:
        """Get suggested response length based on difficulty."""
        if difficulty == QuestionDifficulty.EASY:
            return "100-200 words"
        elif difficulty == QuestionDifficulty.MEDIUM:
            return "200-300 words"
        else:  # HARD
            return "300-500 words"
    
    async def get_question_progress(
        self,
        questions: List[Dict[str, Any]]
    ) -> QuestionProgressResponse:
        """Calculate question progress from a list of questions."""
        
        total = len(questions)
        completed = 0
        in_progress = 0
        
        for question in questions:
            response_status = question.get("response_status")
            if response_status == ResponseStatus.COMPLETED:
                completed += 1
            elif response_status == ResponseStatus.DRAFT:
                in_progress += 1
        
        # Calculate progress percentage
        progress = float(completed) / total if total > 0 else 0.0
        
        # Determine overall status
        if completed == total:
            status = "completed"
        elif completed > 0 or in_progress > 0:
            status = "in-progress"
        else:
            status = "not-started"
            
        return QuestionProgressResponse(
            total=total,
            completed=completed,
            in_progress=in_progress,
            progress=progress,
            status=status
        )



# Factory function to create a QuestionGenerationService instance
def get_question_generation_service(db=None):
    """
    Factory function to get a QuestionGenerationService instance.
    
    Args:
        db: Database connection (optional, for future use)
        
    Returns:
        QuestionGenerationService instance
    """
    from app.services.ai_service import ai_service
    return QuestionGenerationService(ai_service)
