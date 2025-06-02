"""
Question Feedback Service - Handles user feedback and ratings to improve question quality.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone
import logging
import statistics

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback users can provide."""
    RATING = "rating"
    TOO_EASY = "too_easy"
    TOO_HARD = "too_hard"
    IRRELEVANT = "irrelevant"
    UNCLEAR = "unclear"
    HELPFUL = "helpful"
    REPETITIVE = "repetitive"
    NEEDS_EXAMPLES = "needs_examples"
    PERFECT = "perfect"


class RefinementAction(str, Enum):
    """Actions that can be taken based on feedback."""
    INCREASE_DIFFICULTY = "increase_difficulty"
    DECREASE_DIFFICULTY = "decrease_difficulty"
    IMPROVE_RELEVANCE = "improve_relevance"
    ADD_CLARITY = "add_clarity"
    ADD_EXAMPLES = "add_examples"
    MARK_FOR_REMOVAL = "mark_for_removal"
    BOOST_PRIORITY = "boost_priority"
    NO_ACTION = "no_action"


class QuestionFeedbackService:
    """Service for processing user feedback and refining questions."""
    
    def __init__(self):
        self.feedback_weights = {
            FeedbackType.RATING: 1.0,
            FeedbackType.TOO_EASY: 0.8,
            FeedbackType.TOO_HARD: 0.8,
            FeedbackType.IRRELEVANT: 1.2,
            FeedbackType.UNCLEAR: 1.0,
            FeedbackType.HELPFUL: 0.9,
            FeedbackType.REPETITIVE: 1.1,
            FeedbackType.NEEDS_EXAMPLES: 0.7,
            FeedbackType.PERFECT: 0.9
        }
        
        self.refinement_thresholds = {
            "remove_threshold": 2.0,  # Below this average rating, consider removal
            "needs_attention_threshold": 3.0,  # Below this, needs refinement
            "excellent_threshold": 4.5,  # Above this, boost priority
            "min_feedback_count": 3  # Minimum feedback needed for reliable analysis
        }
    
    def process_question_feedback(
        self,
        question_id: str,
        feedback_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process individual feedback for a question.
        
        Args:
            question_id: ID of the question
            feedback_data: Feedback from user
            user_profile: Optional user profile for context
            
        Returns:
            Processed feedback record
        """
        feedback_type = feedback_data.get('type', FeedbackType.RATING)
        if isinstance(feedback_type, str):
            try:
                feedback_type = FeedbackType(feedback_type)
            except ValueError:
                feedback_type = FeedbackType.RATING
        
        # Create feedback record
        feedback_record = {
            'question_id': question_id,
            'feedback_type': feedback_type.value,
            'rating': feedback_data.get('rating'),
            'comment': feedback_data.get('comment', ''),
            'user_level': user_profile.get('writing_level') if user_profile else None,
            'user_genre_preference': user_profile.get('preferred_genres', []) if user_profile else [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'weight': self.feedback_weights.get(feedback_type, 1.0),
            'context': feedback_data.get('context', {})
        }
        
        # Analyze sentiment and extract insights
        insights = self._analyze_feedback_insights(feedback_record)
        feedback_record['insights'] = insights
        
        return feedback_record
    
    def analyze_question_feedback_trends(
        self,
        question_feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze feedback trends for a question to determine refinement actions.
        
        Args:
            question_feedbacks: List of feedback records for a question
            
        Returns:
            Analysis results with recommended actions
        """
        if not question_feedbacks:
            return {'error': 'No feedback data provided'}
        
        # Calculate basic metrics
        total_feedback = len(question_feedbacks)
        ratings = [f.get('rating') for f in question_feedbacks if f.get('rating') is not None]
        
        avg_rating = statistics.mean(ratings) if ratings else None
        rating_std = statistics.stdev(ratings) if len(ratings) > 1 else 0
        
        # Count feedback types
        feedback_type_counts = {}
        for feedback in question_feedbacks:
            fb_type = feedback.get('feedback_type', 'unknown')
            feedback_type_counts[fb_type] = feedback_type_counts.get(fb_type, 0) + 1
        
        # Analyze by user level
        level_analysis = self._analyze_feedback_by_level(question_feedbacks)
        
        # Determine recommended actions
        recommended_actions = self._determine_refinement_actions(
            avg_rating, feedback_type_counts, level_analysis, total_feedback
        )
        
        # Calculate confidence in recommendations
        confidence = self._calculate_recommendation_confidence(
            total_feedback, rating_std, feedback_type_counts
        )
        
        return {
            'total_feedback_count': total_feedback,
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'rating_standard_deviation': round(rating_std, 2),
            'feedback_type_distribution': feedback_type_counts,
            'level_analysis': level_analysis,
            'recommended_actions': recommended_actions,
            'confidence_score': confidence,
            'priority_score': self._calculate_priority_score(avg_rating, total_feedback, feedback_type_counts),
            'insights': self._generate_feedback_insights(feedback_type_counts, level_analysis)
        }
    
    def refine_question_based_on_feedback(
        self,
        question: Dict[str, Any],
        feedback_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate refined version of a question based on feedback analysis.
        
        Args:
            question: Original question dictionary
            feedback_analysis: Analysis results from analyze_question_feedback_trends
            
        Returns:
            Refined question with improvements
        """
        refined_question = question.copy()
        actions_taken = []
        
        recommended_actions = feedback_analysis.get('recommended_actions', [])
        
        for action in recommended_actions:
            if action == RefinementAction.DECREASE_DIFFICULTY:
                refined_question = self._simplify_question(refined_question)
                actions_taken.append('Simplified question text and difficulty')
                
            elif action == RefinementAction.INCREASE_DIFFICULTY:
                refined_question = self._increase_question_complexity(refined_question)
                actions_taken.append('Increased question complexity')
                
            elif action == RefinementAction.ADD_CLARITY:
                refined_question = self._add_clarity_to_question(refined_question)
                actions_taken.append('Added clarity and clearer instructions')
                
            elif action == RefinementAction.ADD_EXAMPLES:
                refined_question = self._add_examples_to_question(refined_question)
                actions_taken.append('Added helpful examples')
                
            elif action == RefinementAction.IMPROVE_RELEVANCE:
                refined_question = self._improve_question_relevance(refined_question)
                actions_taken.append('Improved relevance to chapter content')
        
        # Add refinement metadata
        refined_question['refinement_info'] = {
            'original_version': question.get('question_text'),
            'refinement_date': datetime.now(timezone.utc).isoformat(),
            'actions_taken': actions_taken,
            'based_on_feedback_count': feedback_analysis.get('total_feedback_count', 0),
            'confidence_score': feedback_analysis.get('confidence_score', 0)
        }
        
        return refined_question
    
    def _analyze_feedback_insights(self, feedback_record: Dict[str, Any]) -> List[str]:
        """Extract insights from individual feedback."""
        insights = []
        
        feedback_type = feedback_record.get('feedback_type')
        rating = feedback_record.get('rating')
        comment = feedback_record.get('comment', '').lower()
        
        # Rating-based insights
        if rating is not None:
            if rating <= 2:
                insights.append('User found question unsatisfactory')
            elif rating >= 4:
                insights.append('User found question helpful')
        
        # Comment-based insights
        if comment:
            if any(word in comment for word in ['confusing', 'unclear', 'understand']):
                insights.append('Question may need clearer wording')
            if any(word in comment for word in ['easy', 'simple', 'obvious']):
                insights.append('Question may be too easy for user level')
            if any(word in comment for word in ['hard', 'difficult', 'complex']):
                insights.append('Question may be too challenging')
            if any(word in comment for word in ['irrelevant', 'unrelated', 'relevant']):
                insights.append('Question relevance needs attention')
        
        # Type-specific insights
        if feedback_type == FeedbackType.REPETITIVE:
            insights.append('Question may be too similar to others')
        elif feedback_type == FeedbackType.NEEDS_EXAMPLES:
            insights.append('Question would benefit from examples')
        
        return insights
    
    def _analyze_feedback_by_level(self, feedbacks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze feedback patterns by user writing level."""
        level_data = {}
        
        for feedback in feedbacks:
            level = feedback.get('user_level', 'unknown')
            if level not in level_data:
                level_data[level] = {
                    'count': 0,
                    'ratings': [],
                    'common_feedback_types': {},
                    'avg_rating': 0
                }
            
            level_data[level]['count'] += 1
            
            if feedback.get('rating') is not None:
                level_data[level]['ratings'].append(feedback['rating'])
            
            fb_type = feedback.get('feedback_type', 'unknown')
            level_data[level]['common_feedback_types'][fb_type] = \
                level_data[level]['common_feedback_types'].get(fb_type, 0) + 1
        
        # Calculate averages
        for level, data in level_data.items():
            if data['ratings']:
                data['avg_rating'] = statistics.mean(data['ratings'])
        
        return level_data
    
    def _determine_refinement_actions(
        self,
        avg_rating: Optional[float],
        feedback_types: Dict[str, int],
        level_analysis: Dict[str, Any],
        total_feedback: int
    ) -> List[str]:
        """Determine what refinement actions should be taken."""
        actions = []
        
        # Check if we have enough feedback to make decisions
        if total_feedback < self.refinement_thresholds['min_feedback_count']:
            return [RefinementAction.NO_ACTION]
        
        # Rating-based actions
        if avg_rating is not None:
            if avg_rating <= self.refinement_thresholds['remove_threshold']:
                actions.append(RefinementAction.MARK_FOR_REMOVAL)
            elif avg_rating <= self.refinement_thresholds['needs_attention_threshold']:
                # Determine specific improvements needed
                if feedback_types.get(FeedbackType.TOO_HARD, 0) > feedback_types.get(FeedbackType.TOO_EASY, 0):
                    actions.append(RefinementAction.DECREASE_DIFFICULTY)
                elif feedback_types.get(FeedbackType.TOO_EASY, 0) > feedback_types.get(FeedbackType.TOO_HARD, 0):
                    actions.append(RefinementAction.INCREASE_DIFFICULTY)
                
                if feedback_types.get(FeedbackType.UNCLEAR, 0) > 0:
                    actions.append(RefinementAction.ADD_CLARITY)
                    
                if feedback_types.get(FeedbackType.IRRELEVANT, 0) > 0:
                    actions.append(RefinementAction.IMPROVE_RELEVANCE)
            
            elif avg_rating >= self.refinement_thresholds['excellent_threshold']:
                actions.append(RefinementAction.BOOST_PRIORITY)
        
        # Feedback type-based actions
        if feedback_types.get(FeedbackType.NEEDS_EXAMPLES, 0) > 0:
            actions.append(RefinementAction.ADD_EXAMPLES)
        
        # Level-specific analysis
        beginner_issues = level_analysis.get('beginner', {}).get('common_feedback_types', {})
        if beginner_issues.get(FeedbackType.TOO_HARD, 0) > 1:
            actions.append(RefinementAction.DECREASE_DIFFICULTY)
        
        advanced_issues = level_analysis.get('advanced', {}).get('common_feedback_types', {})
        if advanced_issues.get(FeedbackType.TOO_EASY, 0) > 1:
            actions.append(RefinementAction.INCREASE_DIFFICULTY)
        
        return list(set(actions)) if actions else [RefinementAction.NO_ACTION]
    
    def _calculate_recommendation_confidence(
        self,
        feedback_count: int,
        rating_std: float,
        feedback_types: Dict[str, int]
    ) -> float:
        """Calculate confidence in the recommendations."""
        confidence = 0.0
        
        # Base confidence on feedback count
        if feedback_count >= 10:
            confidence += 0.4
        elif feedback_count >= 5:
            confidence += 0.3
        elif feedback_count >= 3:
            confidence += 0.2
        else:
            confidence += 0.1
        
        # Factor in rating consistency (lower std = higher confidence)
        if rating_std <= 0.5:
            confidence += 0.3
        elif rating_std <= 1.0:
            confidence += 0.2
        elif rating_std <= 1.5:
            confidence += 0.1
        
        # Factor in feedback type consistency
        dominant_type_count = max(feedback_types.values()) if feedback_types else 0
        total_feedback = sum(feedback_types.values()) if feedback_types else 1
        
        if dominant_type_count / total_feedback >= 0.6:
            confidence += 0.3
        elif dominant_type_count / total_feedback >= 0.4:
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _calculate_priority_score(
        self,
        avg_rating: Optional[float],
        feedback_count: int,
        feedback_types: Dict[str, int]
    ) -> float:
        """Calculate priority score for question refinement."""
        if avg_rating is None:
            return 0.5
        
        # Base score on rating (lower rating = higher priority for fixing)
        priority = (5.0 - avg_rating) / 5.0
        
        # Boost priority based on feedback volume
        volume_multiplier = min(2.0, 1.0 + (feedback_count / 10))
        priority *= volume_multiplier
        
        # Boost priority for critical feedback types
        critical_feedback = feedback_types.get(FeedbackType.IRRELEVANT, 0) + \
                          feedback_types.get(FeedbackType.UNCLEAR, 0)
        
        if critical_feedback > 0:
            priority *= 1.5
        
        return min(1.0, priority)
    
    def _generate_feedback_insights(
        self,
        feedback_types: Dict[str, int],
        level_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate human-readable insights from feedback analysis."""
        insights = []
        
        total_feedback = sum(feedback_types.values())
        
        # Most common feedback type
        if feedback_types:
            most_common = max(feedback_types.items(), key=lambda x: x[1])
            insights.append(f"Most common feedback: {most_common[0]} ({most_common[1]} times)")
        
        # Level-specific insights
        for level, data in level_analysis.items():
            if data['count'] >= 2:  # Only report levels with meaningful data
                avg_rating = data.get('avg_rating', 0)
                if avg_rating:
                    insights.append(f"{level.title()} users rate this {avg_rating:.1f}/5 on average")
        
        # Patterns and recommendations
        if feedback_types.get(FeedbackType.TOO_EASY, 0) > feedback_types.get(FeedbackType.TOO_HARD, 0):
            insights.append("Question may be too easy for most users")
        elif feedback_types.get(FeedbackType.TOO_HARD, 0) > feedback_types.get(FeedbackType.TOO_EASY, 0):
            insights.append("Question may be too challenging for most users")
        
        if feedback_types.get(FeedbackType.HELPFUL, 0) > total_feedback * 0.5:
            insights.append("Question is generally helpful to users")
        
        return insights
    
    def _simplify_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify a question that's too difficult."""
        question_text = question.get('question_text', '')
        
        # Simplification strategies
        simplifications = {
            'What unconscious psychological patterns': 'What motivates',
            'How does your character embody or subvert archetypal': 'What type of character is',
            'philosophical worldview': 'beliefs and values',
            'narrative architecture': 'story structure',
            'thematic resonance': 'main themes'
        }
        
        simplified_text = question_text
        for complex_phrase, simple_phrase in simplifications.items():
            if complex_phrase in simplified_text:
                simplified_text = simplified_text.replace(complex_phrase, simple_phrase)
        
        question['question_text'] = simplified_text
        question['difficulty'] = 'easy' if question.get('difficulty') == 'medium' else 'medium'
        
        return question
    
    def _increase_question_complexity(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Increase complexity of a question that's too easy."""
        question_text = question.get('question_text', '')
        
        # Add complexity through more sophisticated language and concepts
        complexity_additions = {
            'What does your character want': 'What drives your character\'s deepest motivations and how do these manifest',
            'How does the plot advance': 'How does the narrative progression serve your thematic development',
            'Where does this take place': 'How does the setting function as both literal space and symbolic representation'
        }
        
        enhanced_text = question_text
        for simple_phrase, complex_phrase in complexity_additions.items():
            if simple_phrase in enhanced_text:
                enhanced_text = enhanced_text.replace(simple_phrase, complex_phrase)
        
        question['question_text'] = enhanced_text
        question['difficulty'] = 'hard' if question.get('difficulty') == 'medium' else 'medium'
        
        return question
    
    def _add_clarity_to_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Add clarity to a question that users find unclear."""
        help_text = question.get('help_text', '')
        
        # Enhance help text with more specific guidance
        enhanced_help = f"{help_text} Be specific and consider concrete examples. Think about how this element affects your readers' experience."
        
        question['help_text'] = enhanced_help
        
        # Add clarifying context to the question itself if it's very short
        question_text = question.get('question_text', '')
        if len(question_text.split()) < 8:
            question['question_text'] = f"{question_text} Provide specific details and explain your reasoning."
        
        return question
    
    def _add_examples_to_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Add examples to help users understand the question better."""
        question_type = question.get('question_type', 'general')
        
        examples_by_type = {
            'character': [
                "Example: 'Sarah wants to prove herself worthy of her father's respect, but her fear of failure keeps her from taking risks.'",
                "Example: 'The antagonist believes the ends justify the means, while the protagonist values honesty above all.'"
            ],
            'plot': [
                "Example: 'The discovery of the hidden letter forces the protagonist to confront their family's secret.'",
                "Example: 'Each obstacle makes the character stronger, building toward the final confrontation.'"
            ],
            'setting': [
                "Example: 'The cramped apartment reflects the character's feeling of being trapped in their circumstances.'",
                "Example: 'The storm outside mirrors the emotional turmoil inside the house.'"
            ]
        }
        
        if question_type in examples_by_type:
            question['examples'] = examples_by_type[question_type]
        
        return question
    
    def _improve_question_relevance(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Improve relevance of a question to chapter content."""
        # Add more specific framing that connects to chapter development
        question_text = question.get('question_text', '')
        
        if 'this chapter' not in question_text.lower():
            # Make the question more chapter-specific
            question['question_text'] = f"In this specific chapter, {question_text.lower()}"
        
        # Enhance help text to emphasize chapter-specific thinking
        help_text = question.get('help_text', '')
        enhanced_help = f"Focus specifically on this chapter's content and how it fits into your overall story. {help_text}"
        question['help_text'] = enhanced_help
        
        return question
    
    def generate_feedback_summary_report(
        self,
        question_feedback_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a summary report of feedback trends across multiple questions.
        
        Args:
            question_feedback_analyses: List of feedback analyses for different questions
            
        Returns:
            Summary report with overall insights and recommendations
        """
        if not question_feedback_analyses:
            return {'error': 'No feedback analyses provided'}
        
        # Aggregate metrics
        total_questions = len(question_feedback_analyses)
        total_feedback = sum(analysis.get('total_feedback_count', 0) for analysis in question_feedback_analyses)
        
        # Calculate average ratings
        all_ratings = [analysis.get('average_rating') for analysis in question_feedback_analyses if analysis.get('average_rating')]
        overall_avg_rating = statistics.mean(all_ratings) if all_ratings else None
        
        # Count actions needed
        action_counts = {}
        for analysis in question_feedback_analyses:
            for action in analysis.get('recommended_actions', []):
                action_counts[action] = action_counts.get(action, 0) + 1
        
        # Identify top issues
        top_issues = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate quality metrics
        high_quality_questions = len([a for a in question_feedback_analyses if a.get('average_rating', 0) >= 4.0])
        needs_attention = len([a for a in question_feedback_analyses if a.get('average_rating', 0) <= 3.0])
        
        return {
            'summary': {
                'total_questions_analyzed': total_questions,
                'total_feedback_received': total_feedback,
                'overall_average_rating': round(overall_avg_rating, 2) if overall_avg_rating else None,
                'high_quality_questions': high_quality_questions,
                'questions_needing_attention': needs_attention
            },
            'top_issues': [{'action': action, 'question_count': count} for action, count in top_issues],
            'quality_distribution': {
                'excellent': len([a for a in question_feedback_analyses if a.get('average_rating', 0) >= 4.5]),
                'good': len([a for a in question_feedback_analyses if 3.5 <= a.get('average_rating', 0) < 4.5]),
                'needs_improvement': len([a for a in question_feedback_analyses if 2.5 <= a.get('average_rating', 0) < 3.5]),
                'poor': len([a for a in question_feedback_analyses if a.get('average_rating', 0) < 2.5])
            },
            'recommendations': self._generate_overall_recommendations(action_counts, total_questions, overall_avg_rating)
        }
    
    def _generate_overall_recommendations(
        self,
        action_counts: Dict[str, int],
        total_questions: int,
        avg_rating: Optional[float]
    ) -> List[str]:
        """Generate overall recommendations for question improvement."""
        recommendations = []
        
        # Most common issues
        if action_counts.get(RefinementAction.ADD_CLARITY, 0) > total_questions * 0.2:
            recommendations.append("Focus on making questions clearer and more specific")
        
        if action_counts.get(RefinementAction.DECREASE_DIFFICULTY, 0) > total_questions * 0.3:
            recommendations.append("Consider simplifying questions for better user accessibility")
        
        if action_counts.get(RefinementAction.IMPROVE_RELEVANCE, 0) > total_questions * 0.2:
            recommendations.append("Improve question relevance to chapter-specific content")
        
        # Overall quality assessment
        if avg_rating and avg_rating >= 4.0:
            recommendations.append("Overall question quality is good - focus on fine-tuning")
        elif avg_rating and avg_rating < 3.0:
            recommendations.append("Significant improvements needed across question set")
        
        if not recommendations:
            recommendations.append("Continue monitoring feedback for emerging patterns")
        
        return recommendations


# Singleton instance
question_feedback_service = QuestionFeedbackService()
