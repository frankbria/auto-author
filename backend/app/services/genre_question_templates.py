"""
Genre-specific question templates for generating contextually appropriate questions.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import random
import logging

logger = logging.getLogger(__name__)


class GenreType(str, Enum):
    """Supported genre types for question generation."""
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    TECHNICAL = "technical"
    EDUCATIONAL = "educational"
    BUSINESS = "business"
    SELF_HELP = "self_help"
    BIOGRAPHY = "biography"
    HISTORY = "history"
    SCIENCE = "science"
    HEALTH = "health"
    TRAVEL = "travel"
    COOKING = "cooking"
    ARTS = "arts"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    THRILLER = "thriller"
    SCIENCE_FICTION = "science_fiction"


class GenreQuestionTemplates:
    """Service for managing genre-specific question templates."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize question templates organized by genre and question type."""
        return {
            GenreType.FICTION: {
                "character": [
                    "What drives {character_name} to make their key decision in this chapter?",
                    "How does {character_name} change or grow throughout this chapter?",
                    "What internal conflict does {character_name} face in this chapter?",
                    "What does the reader learn about {character_name}'s past in this chapter?",
                    "How do other characters perceive {character_name} in this chapter?",
                    "What character flaws or strengths are revealed in this chapter?",
                    "What relationships are tested or strengthened in this chapter?"
                ],
                "plot": [
                    "What major event or turning point occurs in this chapter?",
                    "How does this chapter advance the central conflict of your story?",
                    "What obstacles prevent your protagonist from achieving their goal?",
                    "What unexpected twist or revelation occurs in this chapter?",
                    "How does the pacing change throughout this chapter?",
                    "What consequences from previous chapters come into play?",
                    "What new complications arise for your characters?"
                ],
                "setting": [
                    "How does the setting reflect the emotional tone of this chapter?",
                    "What sensory details bring this location to life for readers?",
                    "How does the environment influence your characters' actions?",
                    "What makes this setting unique or memorable?",
                    "How has the setting changed since earlier in the story?",
                    "What symbolic meaning does the setting convey?",
                    "How do weather or atmospheric conditions affect the mood?"
                ],
                "theme": [
                    "What universal truth or message emerges in this chapter?",
                    "How do the events of this chapter relate to your story's central theme?",
                    "What moral dilemma or ethical question is explored?",
                    "How do your characters' choices reflect deeper themes?",
                    "What symbols or metaphors reinforce your thematic elements?",
                    "How might different readers interpret this chapter's meaning?",
                    "What questions about human nature does this chapter raise?"
                ]
            },
            
            GenreType.NON_FICTION: {
                "concept": [
                    "What is the core concept or principle this chapter introduces?",
                    "How does this concept build upon previous chapters?",
                    "What real-world examples illustrate this concept effectively?",
                    "What common misconceptions about this topic should you address?",
                    "How can readers immediately apply this concept in their lives?",
                    "What research or evidence supports your main points?",
                    "What counterarguments or alternative viewpoints exist?"
                ],
                "practical": [
                    "What specific steps should readers take after reading this chapter?",
                    "What tools or resources do readers need to implement your advice?",
                    "What common mistakes should readers avoid when applying this information?",
                    "How can readers measure their progress or success?",
                    "What variations or adaptations might different readers need?",
                    "What obstacles might readers face, and how can they overcome them?",
                    "How long should readers expect to see results?"
                ],
                "research": [
                    "What studies, statistics, or expert opinions support your claims?",
                    "How recent and relevant is the research you're citing?",
                    "What gaps in current research or knowledge should you acknowledge?",
                    "How do different experts or schools of thought approach this topic?",
                    "What methodology or framework guides your analysis?",
                    "What case studies or success stories can you include?",
                    "How has thinking about this topic evolved over time?"
                ]
            },
            
            GenreType.TECHNICAL: {
                "process": [
                    "What is the step-by-step process readers need to follow?",
                    "What prerequisites or background knowledge do readers need?",
                    "What tools, software, or equipment are required?",
                    "What are the most common errors in this process and how to avoid them?",
                    "How can readers troubleshoot problems that arise?",
                    "What variations of this process exist for different scenarios?",
                    "How can readers verify their implementation is correct?"
                ],
                "implementation": [
                    "What code examples or practical demonstrations will you provide?",
                    "How do you balance comprehensiveness with clarity in your examples?",
                    "What best practices should readers follow in their implementation?",
                    "How do you handle different skill levels among your readers?",
                    "What testing or validation steps should readers perform?",
                    "How do you address platform or version-specific considerations?",
                    "What performance or security implications should readers consider?"
                ],
                "architecture": [
                    "How does this component fit into the larger system or framework?",
                    "What design patterns or principles are you applying?",
                    "How do you justify your architectural decisions?",
                    "What trade-offs or limitations does this approach have?",
                    "How does this solution scale or adapt to different requirements?",
                    "What alternative approaches did you consider and why did you reject them?",
                    "How does this integrate with existing systems or standards?"
                ]
            },
            
            GenreType.BUSINESS: {
                "strategy": [
                    "What strategic advantage or competitive edge does this approach provide?",
                    "How do market conditions or industry trends support this strategy?",
                    "What resources or capabilities are required to execute this strategy?",
                    "What risks or potential obstacles could derail this approach?",
                    "How do you measure the success or ROI of this strategy?",
                    "How does this strategy align with current business objectives?",
                    "What timeline or phases are involved in implementation?"
                ],
                "leadership": [
                    "What leadership qualities or skills does this chapter highlight?",
                    "How can leaders effectively communicate this information to their teams?",
                    "What common leadership challenges does this chapter address?",
                    "How do different leadership styles apply to this situation?",
                    "What cultural or organizational factors influence leadership effectiveness?",
                    "How can leaders build buy-in and support for these ideas?",
                    "What role does emotional intelligence play in this context?"
                ],
                "execution": [
                    "What specific actions should business leaders take immediately?",
                    "How do you prioritize competing demands on time and resources?",
                    "What metrics or KPIs should leaders track to monitor progress?",
                    "How do you adapt this approach for different company sizes or industries?",
                    "What change management considerations are important?",
                    "How do you overcome resistance or skepticism from stakeholders?",
                    "What role does technology play in enabling these solutions?"
                ]
            },
            
            GenreType.FANTASY: {
                "worldbuilding": [
                    "What unique aspects of your fantasy world are revealed in this chapter?",
                    "How do the rules of magic or supernatural elements work in this scene?",
                    "What cultural, political, or social structures shape this part of your world?",
                    "How does the history or mythology of your world influence current events?",
                    "What creatures, races, or beings inhabit this part of your world?",
                    "How do geography and environment affect the story in this chapter?",
                    "What technologies or magical systems are available to your characters?"
                ],
                "magic": [
                    "How does the magic system in your world function and what are its limitations?",
                    "What cost or consequence does using magic have for your characters?",
                    "How does magical ability affect social status or relationships?",
                    "What magical artifacts, spells, or powers are introduced in this chapter?",
                    "How do different characters or cultures approach magic differently?",
                    "What conflicts arise from the use or misuse of magical power?",
                    "How does magic interact with the physical world and natural laws?"
                ],
                "mythology": [
                    "What legends, prophecies, or ancient stories influence this chapter?",
                    "How do your characters' beliefs or superstitions affect their actions?",
                    "What gods, spirits, or supernatural entities play a role in this chapter?",
                    "How does the mythology of your world explain current conflicts or challenges?",
                    "What rituals, ceremonies, or traditions are important in this chapter?",
                    "How do different cultures or groups interpret the same mythological elements?",
                    "What ancient mysteries or forgotten knowledge becomes relevant?"
                ]
            },
            
            GenreType.MYSTERY: {
                "investigation": [
                    "What new clue or piece of evidence is discovered in this chapter?",
                    "How does your detective or protagonist approach problem-solving?",
                    "What investigative techniques or methods are employed?",
                    "How do you balance revealing information with maintaining suspense?",
                    "What false leads or red herrings do you introduce?",
                    "How do witness interviews or interrogations advance the plot?",
                    "What patterns or connections begin to emerge from the evidence?"
                ],
                "suspects": [
                    "What new suspects are introduced or existing ones developed?",
                    "What motives, means, and opportunities do various suspects have?",
                    "How do alibis and character backgrounds affect the investigation?",
                    "What secrets or hidden relationships are revealed about suspects?",
                    "How do you maintain reader suspicion across multiple characters?",
                    "What behavior or actions make certain characters seem guilty or innocent?",
                    "How do past crimes or incidents connect to current suspects?"
                ],
                "revelation": [
                    "What major revelation or plot twist occurs in this chapter?",
                    "How do you prepare readers for revelations while maintaining surprise?",
                    "What assumptions or theories are proven wrong in this chapter?",
                    "How does new information change the direction of the investigation?",
                    "What emotional impact does this revelation have on your characters?",
                    "How do you ensure revelations feel logical and well-supported?",
                    "What questions are answered and what new mysteries emerge?"
                ]
            }
        }
    
    def get_genre_questions(
        self, 
        genre: str, 
        chapter_title: str = "", 
        count: int = 5,
        question_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate genre-specific questions for a chapter.
        
        Args:
            genre: The genre of the book
            chapter_title: Title of the chapter for context
            count: Number of questions to generate
            question_types: Specific types to focus on (optional)
            
        Returns:
            List of question dictionaries
        """
        # Normalize genre
        normalized_genre = self._normalize_genre(genre)
        
        if normalized_genre not in self.templates:
            # Fall back to fiction if genre not found
            normalized_genre = GenreType.FICTION
        
        genre_templates = self.templates[normalized_genre]
        
        # Determine which question types to use
        if question_types:
            available_types = [t for t in question_types if t in genre_templates]
        else:
            available_types = list(genre_templates.keys())
        
        if not available_types:
            available_types = list(genre_templates.keys())
        
        questions = []
        type_cycle = 0
        
        for i in range(count):
            # Cycle through question types for diversity
            question_type = available_types[type_cycle % len(available_types)]
            type_cycle += 1
            
            # Get random template from this type
            templates = genre_templates[question_type]
            template = random.choice(templates)
            
            # Customize template with chapter context
            question_text = self._customize_template(template, chapter_title, genre)
            
            questions.append({
                'question_text': question_text,
                'question_type': question_type,
                'difficulty': self._get_default_difficulty(normalized_genre, question_type),
                'genre': normalized_genre,
                'template_used': template,
                'help_text': self._get_help_text(normalized_genre, question_type)
            })
        
        return questions
    
    def _normalize_genre(self, genre: str) -> str:
        """Normalize genre string to match our enum values."""
        genre_lower = genre.lower().replace(' ', '_').replace('-', '_')
        
        # Map common variations
        genre_mappings = {
            'sci_fi': GenreType.SCIENCE_FICTION,
            'scifi': GenreType.SCIENCE_FICTION,
            'sf': GenreType.SCIENCE_FICTION,
            'non_fiction': GenreType.NON_FICTION,
            'nonfiction': GenreType.NON_FICTION,
            'self_help': GenreType.SELF_HELP,
            'selfhelp': GenreType.SELF_HELP,
            'tech': GenreType.TECHNICAL,
            'technical_writing': GenreType.TECHNICAL,
            'how_to': GenreType.EDUCATIONAL,
            'howto': GenreType.EDUCATIONAL,
            'textbook': GenreType.EDUCATIONAL,
            'memoir': GenreType.BIOGRAPHY,
            'autobiography': GenreType.BIOGRAPHY
        }
        
        if genre_lower in genre_mappings:
            return genre_mappings[genre_lower]
        
        # Try direct enum match
        for genre_type in GenreType:
            if genre_type.value == genre_lower:
                return genre_type.value
        
        # Default fallback
        return GenreType.FICTION
    
    def _customize_template(self, template: str, chapter_title: str, genre: str) -> str:
        """Customize a template with chapter-specific context."""
        # Replace placeholder variables
        customized = template
        
        # Generic placeholders
        if "{character_name}" in customized:
            customized = customized.replace("{character_name}", "your protagonist")
        
        # Add chapter-specific context
        if chapter_title and len(chapter_title) > 0:
            # Add chapter title relevance where appropriate
            if "this chapter" in customized:
                customized = customized.replace("this chapter", f'this chapter ("{chapter_title}")')
        
        return customized
    
    def _get_default_difficulty(self, genre: str, question_type: str) -> str:
        """Get default difficulty level based on genre and question type."""
        difficulty_mapping = {
            GenreType.TECHNICAL: {
                'process': 'medium',
                'implementation': 'hard',
                'architecture': 'hard'
            },
            GenreType.FICTION: {
                'character': 'medium',
                'plot': 'easy',
                'setting': 'easy',
                'theme': 'hard'
            },
            GenreType.NON_FICTION: {
                'concept': 'medium',
                'practical': 'easy',
                'research': 'hard'
            }
        }
        
        if genre in difficulty_mapping and question_type in difficulty_mapping[genre]:
            return difficulty_mapping[genre][question_type]
        
        return 'medium'  # Default
    
    def _get_help_text(self, genre: str, question_type: str) -> str:
        """Get helpful guidance text for answering questions of this type."""
        help_mapping = {
            GenreType.FICTION: {
                'character': "Focus on internal motivations, character development, and relationships. Consider how actions reveal personality.",
                'plot': "Think about cause and effect, conflict escalation, and how events move the story forward.",
                'setting': "Describe not just what the place looks like, but how it feels and affects the characters.",
                'theme': "Consider the deeper meaning and universal truths your story explores."
            },
            GenreType.NON_FICTION: {
                'concept': "Explain complex ideas clearly with examples. Connect to readers' existing knowledge.",
                'practical': "Provide actionable steps and real-world applications. Address common implementation challenges.",
                'research': "Cite credible sources and explain the significance of your evidence."
            },
            GenreType.TECHNICAL: {
                'process': "Break down complex procedures into clear, sequential steps with examples.",
                'implementation': "Provide working code examples and explain best practices.",
                'architecture': "Explain design decisions and trade-offs clearly."
            }
        }
        
        if genre in help_mapping and question_type in help_mapping[genre]:
            return help_mapping[genre][question_type]
        
        return "Consider how this element serves your overall chapter goals and engages your target audience."
    
    def get_supported_genres(self) -> List[str]:
        """Get list of all supported genres."""
        return [genre.value for genre in GenreType]
    
    def get_question_types_for_genre(self, genre: str) -> List[str]:
        """Get available question types for a specific genre."""
        normalized_genre = self._normalize_genre(genre)
        if normalized_genre in self.templates:
            return list(self.templates[normalized_genre].keys())
        return []
    
    def analyze_genre_coverage(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how well questions cover different aspects of a genre."""
        if not questions:
            return {'error': 'No questions to analyze'}
        
        # Count questions by type
        type_counts = {}
        genres_found = set()
        
        for question in questions:
            q_type = question.get('question_type', 'unknown')
            genre = question.get('genre', 'unknown')
            
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
            genres_found.add(genre)
        
        # Determine primary genre
        primary_genre = list(genres_found)[0] if len(genres_found) == 1 else 'mixed'
        
        # Check coverage for primary genre
        if primary_genre in self.templates:
            expected_types = set(self.templates[primary_genre].keys())
            covered_types = set(type_counts.keys())
            missing_types = expected_types - covered_types
            
            coverage_score = len(covered_types) / len(expected_types) if expected_types else 0
        else:
            missing_types = set()
            coverage_score = 1.0
        
        return {
            'primary_genre': primary_genre,
            'total_questions': len(questions),
            'type_distribution': type_counts,
            'coverage_score': round(coverage_score, 2),
            'missing_types': list(missing_types),
            'recommendations': self._generate_genre_recommendations(
                primary_genre, type_counts, missing_types
            )
        }
    
    def _generate_genre_recommendations(
        self, 
        genre: str, 
        type_counts: Dict[str, int], 
        missing_types: set
    ) -> List[str]:
        """Generate recommendations for improving genre coverage."""
        recommendations = []
        
        if missing_types:
            recommendations.append(
                f"Consider adding questions about: {', '.join(missing_types)}"
            )
        
        if genre == GenreType.FICTION:
            if type_counts.get('character', 0) == 0:
                recommendations.append("Fiction benefits from strong character development questions")
            if type_counts.get('theme', 0) == 0:
                recommendations.append("Consider adding questions about themes and deeper meaning")
        
        elif genre == GenreType.TECHNICAL:
            if type_counts.get('implementation', 0) == 0:
                recommendations.append("Technical content should include practical implementation questions")
        
        elif genre == GenreType.NON_FICTION:
            if type_counts.get('practical', 0) == 0:
                recommendations.append("Non-fiction readers appreciate actionable, practical questions")
        
        total_questions = sum(type_counts.values())
        if total_questions < 5:
            recommendations.append("Consider generating more questions for comprehensive coverage")
        
        return recommendations


# Singleton instance
genre_question_templates = GenreQuestionTemplates()
