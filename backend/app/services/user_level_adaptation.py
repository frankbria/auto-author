"""
User Level Adaptation Service - Adapts questions based on writing experience and skill level.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WritingLevel(str, Enum):
    """User writing experience levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"


class ExperienceArea(str, Enum):
    """Areas of writing experience."""
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    TECHNICAL = "technical"
    BUSINESS = "business"
    ACADEMIC = "academic"
    CREATIVE = "creative"
    JOURNALISTIC = "journalistic"


class UserLevelAdaptationService:
    """Service for adapting questions based on user's writing level and experience."""
    
    def __init__(self):
        self.level_adaptations = self._initialize_level_adaptations()
        self.complexity_adjustments = self._initialize_complexity_adjustments()
    
    def _initialize_level_adaptations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize adaptations for different writing levels."""
        return {
            WritingLevel.BEGINNER: {
                "question_style": "simple_direct",
                "complexity_level": 0.3,
                "guidance_level": "detailed",
                "focus_areas": ["basic_structure", "character_basics", "plot_flow"],
                "avoid_concepts": ["advanced_techniques", "literary_theory", "complex_narrative"],
                "preferred_question_types": ["character", "plot", "setting"],
                "examples_needed": True,
                "step_by_step": True,
                "encouragement": True
            },
            WritingLevel.INTERMEDIATE: {
                "question_style": "guided_exploration",
                "complexity_level": 0.6,
                "guidance_level": "moderate",
                "focus_areas": ["character_development", "pacing", "dialogue", "world_building"],
                "avoid_concepts": ["experimental_techniques", "meta_narrative"],
                "preferred_question_types": ["character", "plot", "setting", "theme"],
                "examples_needed": True,
                "step_by_step": False,
                "encouragement": False
            },
            WritingLevel.ADVANCED: {
                "question_style": "analytical_deep",
                "complexity_level": 0.8,
                "guidance_level": "minimal",
                "focus_areas": ["theme", "symbolism", "narrative_techniques", "style"],
                "avoid_concepts": [],
                "preferred_question_types": ["theme", "character", "plot", "research"],
                "examples_needed": False,
                "step_by_step": False,
                "encouragement": False
            },
            WritingLevel.PROFESSIONAL: {
                "question_style": "strategic_craft",
                "complexity_level": 1.0,
                "guidance_level": "strategic",
                "focus_areas": ["market_considerations", "audience_targeting", "craft_mastery"],
                "avoid_concepts": [],
                "preferred_question_types": ["theme", "research", "character", "plot"],
                "examples_needed": False,
                "step_by_step": False,
                "encouragement": False
            }
        }
    
    def _initialize_complexity_adjustments(self) -> Dict[str, Dict[str, Any]]:
        """Initialize complexity adjustments for different question types."""
        return {
            "character": {
                WritingLevel.BEGINNER: {
                    "focus": "basic_traits_and_goals",
                    "questions": [
                        "What does your main character want most in this chapter?",
                        "How would you describe your character's personality?",
                        "What problem does your character face in this chapter?"
                    ]
                },
                WritingLevel.INTERMEDIATE: {
                    "focus": "development_and_motivation",
                    "questions": [
                        "How does your character's internal conflict drive their actions?",
                        "What contradictions in your character create interesting tension?",
                        "How do other characters view your protagonist differently than they view themselves?"
                    ]
                },
                WritingLevel.ADVANCED: {
                    "focus": "psychological_depth_and_archetype",
                    "questions": [
                        "What unconscious psychological patterns drive your character's behavior?",
                        "How does your character embody or subvert archetypal patterns?",
                        "What philosophical worldview does your character represent or challenge?"
                    ]
                }
            },
            "plot": {
                WritingLevel.BEGINNER: {
                    "focus": "basic_story_progression",
                    "questions": [
                        "What happens first, next, and last in this chapter?",
                        "What problem gets bigger or smaller in this chapter?",
                        "How does this chapter move the story forward?"
                    ]
                },
                WritingLevel.INTERMEDIATE: {
                    "focus": "conflict_and_tension",
                    "questions": [
                        "How does the central conflict escalate or transform in this chapter?",
                        "What unexpected complications arise from previous choices?",
                        "How do subplots intersect with the main storyline?"
                    ]
                },
                WritingLevel.ADVANCED: {
                    "focus": "narrative_structure_and_pacing",
                    "questions": [
                        "How does this chapter's pacing serve the overall narrative rhythm?",
                        "What structural function does this chapter serve in your story architecture?",
                        "How do you balance revelation and withholding to maintain narrative tension?"
                    ]
                }
            },
            "theme": {
                WritingLevel.BEGINNER: {
                    "focus": "basic_message",
                    "questions": [
                        "What lesson or message does this chapter teach?",
                        "What important idea do you want readers to think about?",
                        "How do your characters learn something important?"
                    ]
                },
                WritingLevel.INTERMEDIATE: {
                    "focus": "thematic_development",
                    "questions": [
                        "How do the events in this chapter reflect larger themes about human nature?",
                        "What moral questions does this chapter raise without directly answering?",
                        "How do symbols or recurring motifs reinforce your thematic content?"
                    ]
                },
                WritingLevel.ADVANCED: {
                    "focus": "philosophical_exploration",
                    "questions": [
                        "How does this chapter contribute to your exploration of existential questions?",
                        "What philosophical tensions are embodied in the conflict between characters or ideas?",
                        "How do you use literary devices to create thematic resonance without didacticism?"
                    ]
                }
            }
        }
    
    def adapt_questions_for_user(
        self,
        questions: List[Dict[str, Any]],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Adapt questions based on user's writing level and experience.
        
        Args:
            questions: Original list of questions
            user_profile: User's writing profile including level and experience
            
        Returns:
            Adapted questions suitable for the user's level
        """
        writing_level = user_profile.get('writing_level', WritingLevel.INTERMEDIATE)
        experience_areas = user_profile.get('experience_areas', [])
        preferred_guidance = user_profile.get('guidance_preference', 'auto')
        
        # Normalize writing level
        if isinstance(writing_level, str):
            try:
                writing_level = WritingLevel(writing_level.lower())
            except ValueError:
                writing_level = WritingLevel.INTERMEDIATE
        
        adaptations = self.level_adaptations.get(writing_level, self.level_adaptations[WritingLevel.INTERMEDIATE])
        
        adapted_questions = []
        
        for question in questions:
            adapted_question = self._adapt_single_question(
                question, writing_level, adaptations, experience_areas
            )
            adapted_questions.append(adapted_question)
        
        # Apply level-specific filtering and reordering
        adapted_questions = self._apply_level_filtering(adapted_questions, adaptations)
        adapted_questions = self._reorder_by_difficulty(adapted_questions, writing_level)
        
        return adapted_questions
    
    def _adapt_single_question(
        self,
        question: Dict[str, Any],
        writing_level: WritingLevel,
        adaptations: Dict[str, Any],
        experience_areas: List[str]
    ) -> Dict[str, Any]:
        """Adapt a single question for the user's level."""
        adapted = question.copy()
        
        question_type = question.get('question_type', 'general')
        question_text = question.get('question_text', '')
        
        # Adjust complexity of question text
        if question_type in self.complexity_adjustments:
            level_adjustments = self.complexity_adjustments[question_type].get(
                writing_level, 
                self.complexity_adjustments[question_type].get(WritingLevel.INTERMEDIATE, {})
            )
            
            # Replace with level-appropriate questions if available
            if 'questions' in level_adjustments:
                # Find a suitable replacement or keep original
                adapted['question_text'] = self._select_appropriate_question(
                    question_text, level_adjustments['questions'], writing_level
                )
        
        # Adjust help text based on guidance level
        guidance_level = adaptations.get('guidance_level', 'moderate')
        adapted['help_text'] = self._adapt_help_text(
            question.get('help_text', ''), guidance_level, writing_level, question_type
        )
        
        # Add examples if needed
        if adaptations.get('examples_needed', False):
            adapted['examples'] = self._generate_examples(question_type, writing_level)
        
        # Add encouragement for beginners
        if adaptations.get('encouragement', False):
            adapted['encouragement'] = self._generate_encouragement(question_type)
        
        # Adjust difficulty rating
        adapted['difficulty'] = self._adjust_difficulty(
            question.get('difficulty', 'medium'), writing_level
        )
        
        # Add level-specific metadata
        adapted['adapted_for_level'] = writing_level.value
        adapted['guidance_level'] = guidance_level
        
        return adapted
    
    def _select_appropriate_question(
        self, 
        original_question: str, 
        level_questions: List[str], 
        writing_level: WritingLevel
    ) -> str:
        """Select the most appropriate question for the user's level."""
        # For now, return the first available level-appropriate question
        # In a more sophisticated version, we could use similarity matching
        if level_questions:
            return level_questions[0]
        return original_question
    
    def _adapt_help_text(
        self, 
        original_help: str, 
        guidance_level: str, 
        writing_level: WritingLevel,
        question_type: str
    ) -> str:
        """Adapt help text based on user's preferred guidance level."""
        base_help = original_help or "Consider this aspect of your chapter development."
        
        if guidance_level == "detailed" or writing_level == WritingLevel.BEGINNER:
            return self._expand_help_text(base_help, question_type, writing_level)
        elif guidance_level == "minimal" or writing_level == WritingLevel.ADVANCED:
            return self._condense_help_text(base_help)
        else:
            return base_help
    
    def _expand_help_text(self, base_help: str, question_type: str, writing_level: WritingLevel) -> str:
        """Expand help text with more detailed guidance."""
        expanded_guidance = {
            'character': "Think about what makes your character unique. Consider their background, motivations, fears, and goals. How do they speak and act? What do they want, and what's stopping them from getting it?",
            'plot': "Focus on the sequence of events. What happens first? What causes what? How do events build tension or resolve conflicts? Think about cause and effect relationships.",
            'setting': "Describe where and when your story takes place. Use all five senses - what do characters see, hear, smell, feel, and taste? How does the environment affect the mood and actions?",
            'theme': "Think about the bigger ideas your story explores. What questions about life, society, or human nature does your story raise? What might readers learn or think about?"
        }
        
        type_guidance = expanded_guidance.get(question_type, base_help)
        return f"{base_help} {type_guidance}"
    
    def _condense_help_text(self, base_help: str) -> str:
        """Condense help text for advanced users who need less guidance."""
        # Extract the core concept from verbose help text
        sentences = base_help.split('.')
        if sentences:
            return sentences[0] + "."
        return base_help
    
    def _generate_examples(self, question_type: str, writing_level: WritingLevel) -> List[str]:
        """Generate examples to help users understand the question."""
        examples = {
            'character': [
                "She wants to prove herself worthy of her father's respect.",
                "He fears abandonment, so he pushes people away first.",
                "The protagonist discovers they've been living a lie."
            ],
            'plot': [
                "The protagonist faces their greatest fear.",
                "A secret from the past is revealed.",
                "The stakes are raised when someone unexpected arrives."
            ],
            'setting': [
                "The abandoned warehouse echoed with dripping water and distant sirens.",
                "Sunlight filtered through ancient stained glass windows.",
                "The bustling marketplace filled with exotic scents and colorful fabrics."
            ]
        }
        
        return examples.get(question_type, ["Consider specific, concrete details that bring your story to life."])
    
    def _generate_encouragement(self, question_type: str) -> str:
        """Generate encouraging text for beginner writers."""
        encouragements = {
            'character': "Remember, even small character details can make a big difference in how readers connect with your story!",
            'plot': "Don't worry about making everything perfect - focus on making sure events feel connected and purposeful.",
            'setting': "Use your imagination! Even familiar places can become interesting with the right details.",
            'theme': "Themes often emerge naturally from your story - you don't have to force them."
        }
        
        return encouragements.get(question_type, "Trust your instincts and keep writing!")
    
    def _adjust_difficulty(self, original_difficulty: str, writing_level: WritingLevel) -> str:
        """Adjust difficulty rating based on user's level."""
        difficulty_adjustments = {
            WritingLevel.BEGINNER: {
                'easy': 'easy',
                'medium': 'easy',
                'hard': 'medium'
            },
            WritingLevel.INTERMEDIATE: {
                'easy': 'easy',
                'medium': 'medium',
                'hard': 'medium'
            },
            WritingLevel.ADVANCED: {
                'easy': 'medium',
                'medium': 'medium',
                'hard': 'hard'
            },
            WritingLevel.PROFESSIONAL: {
                'easy': 'medium',
                'medium': 'hard',
                'hard': 'hard'
            }
        }
        
        adjustments = difficulty_adjustments.get(writing_level, {})
        return adjustments.get(original_difficulty, original_difficulty)
    
    def _apply_level_filtering(
        self, 
        questions: List[Dict[str, Any]], 
        adaptations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter questions based on level-appropriate focus areas."""
        preferred_types = adaptations.get('preferred_question_types', [])
        avoid_concepts = adaptations.get('avoid_concepts', [])
        
        if not preferred_types:
            return questions
        
        # Score questions based on preference
        scored_questions = []
        for question in questions:
            score = 0
            question_type = question.get('question_type', '')
            question_text = question.get('question_text', '').lower()
            
            # Boost score for preferred types
            if question_type in preferred_types:
                score += 10
            
            # Reduce score for concepts to avoid
            for avoid_concept in avoid_concepts:
                if avoid_concept.replace('_', ' ') in question_text:
                    score -= 5
            
            scored_questions.append((score, question))
        
        # Sort by score and return questions
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        return [q[1] for q in scored_questions]
    
    def _reorder_by_difficulty(
        self, 
        questions: List[Dict[str, Any]], 
        writing_level: WritingLevel
    ) -> List[Dict[str, Any]]:
        """Reorder questions based on appropriate difficulty progression."""
        if writing_level == WritingLevel.BEGINNER:
            # Start with easiest questions
            questions.sort(key=lambda q: {'easy': 1, 'medium': 2, 'hard': 3}.get(q.get('difficulty', 'medium'), 2))
        elif writing_level == WritingLevel.PROFESSIONAL:
            # Start with more challenging questions
            questions.sort(key=lambda q: {'hard': 1, 'medium': 2, 'easy': 3}.get(q.get('difficulty', 'medium'), 2))
        
        return questions
    
    def analyze_user_progression(
        self, 
        user_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze user's progression and suggest level adjustments.
        
        Args:
            user_responses: List of user's question responses with quality metrics
            
        Returns:
            Analysis of user progression and recommendations
        """
        if not user_responses:
            return {'error': 'No responses to analyze'}
        
        # Calculate metrics
        total_responses = len(user_responses)
        avg_response_length = sum(len(r.get('response_text', '').split()) for r in user_responses) / total_responses
        
        # Count difficulty levels handled
        difficulty_counts = {}
        for response in user_responses:
            difficulty = response.get('question_difficulty', 'medium')
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        # Analyze response quality (if available)
        quality_scores = [r.get('quality_score', 0) for r in user_responses if 'quality_score' in r]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Determine suggested level
        current_level = self._determine_suggested_level(
            avg_response_length, difficulty_counts, avg_quality, total_responses
        )
        
        return {
            'total_responses': total_responses,
            'average_response_length': round(avg_response_length, 1),
            'difficulty_distribution': difficulty_counts,
            'average_quality_score': round(avg_quality, 2),
            'suggested_level': current_level,
            'progression_indicators': self._get_progression_indicators(
                avg_response_length, difficulty_counts, avg_quality
            ),
            'recommendations': self._generate_progression_recommendations(
                current_level, difficulty_counts, avg_quality
            )
        }
    
    def _determine_suggested_level(
        self, 
        avg_length: float, 
        difficulty_counts: Dict[str, int], 
        avg_quality: float, 
        total_responses: int
    ) -> str:
        """Determine suggested writing level based on response patterns."""
        score = 0
        
        # Length scoring
        if avg_length < 50:
            score += 1  # Beginner
        elif avg_length < 150:
            score += 2  # Intermediate
        elif avg_length < 300:
            score += 3  # Advanced
        else:
            score += 4  # Professional
        
        # Difficulty handling
        hard_ratio = difficulty_counts.get('hard', 0) / total_responses
        if hard_ratio > 0.5:
            score += 2
        elif hard_ratio > 0.2:
            score += 1
        
        # Quality scoring
        if avg_quality > 0.8:
            score += 2
        elif avg_quality > 0.6:
            score += 1
        
        # Convert score to level
        if score <= 2:
            return WritingLevel.BEGINNER
        elif score <= 4:
            return WritingLevel.INTERMEDIATE
        elif score <= 6:
            return WritingLevel.ADVANCED
        else:
            return WritingLevel.PROFESSIONAL
    
    def _get_progression_indicators(
        self, 
        avg_length: float, 
        difficulty_counts: Dict[str, int], 
        avg_quality: float
    ) -> List[str]:
        """Get indicators of user's writing progression."""
        indicators = []
        
        if avg_length > 200:
            indicators.append("Shows ability to develop ideas in depth")
        
        if difficulty_counts.get('hard', 0) > 0:
            indicators.append("Comfortable with challenging questions")
        
        if avg_quality > 0.7:
            indicators.append("Demonstrates strong response quality")
        
        if not indicators:
            indicators.append("Building foundational writing skills")
        
        return indicators
    
    def _generate_progression_recommendations(
        self, 
        suggested_level: str, 
        difficulty_counts: Dict[str, int], 
        avg_quality: float
    ) -> List[str]:
        """Generate recommendations for user progression."""
        recommendations = []
        
        if suggested_level == WritingLevel.BEGINNER:
            recommendations.append("Focus on completing responses to build writing confidence")
            recommendations.append("Try to elaborate more on your initial thoughts")
        
        elif suggested_level == WritingLevel.INTERMEDIATE:
            recommendations.append("Challenge yourself with more complex question types")
            recommendations.append("Focus on connecting different elements of your story")
        
        elif suggested_level == WritingLevel.ADVANCED:
            recommendations.append("Explore deeper thematic questions")
            recommendations.append("Consider how your choices affect reader experience")
        
        else:  # Professional
            recommendations.append("Focus on strategic and market-oriented questions")
            recommendations.append("Consider mentoring other writers")
        
        return recommendations


# Singleton instance
user_level_adaptation_service = UserLevelAdaptationService()
