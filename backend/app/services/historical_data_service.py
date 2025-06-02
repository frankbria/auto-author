"""
Historical Data Service - Uses historical question and response data to improve suggestions.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import logging
import statistics

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """Service for analyzing historical data to improve question suggestions."""
    
    def __init__(self):
        self.analysis_cache = {}
        self.cache_ttl = timedelta(hours=1)  # Cache results for 1 hour
    
    def analyze_question_performance_trends(
        self,
        historical_questions: List[Dict[str, Any]],
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze performance trends of questions over a time period.
        
        Args:
            historical_questions: List of questions with performance data
            time_period_days: Number of days to analyze
            
        Returns:
            Analysis of question performance trends
        """
        if not historical_questions:
            return {'error': 'No historical data provided'}
        
        # Filter questions by time period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_period_days)
        recent_questions = [
            q for q in historical_questions 
            if self._parse_date(q.get('created_at', '')) >= cutoff_date
        ]
        
        # Performance metrics analysis
        performance_analysis = self._analyze_performance_metrics(recent_questions)
        
        # Success patterns analysis
        success_patterns = self._identify_success_patterns(recent_questions)
        
        # User engagement analysis
        engagement_analysis = self._analyze_user_engagement(recent_questions)
        
        # Question type effectiveness
        type_effectiveness = self._analyze_question_type_effectiveness(recent_questions)
        
        return {
            'analysis_period': f'{time_period_days} days',
            'total_questions_analyzed': len(recent_questions),
            'performance_metrics': performance_analysis,
            'success_patterns': success_patterns,
            'engagement_analysis': engagement_analysis,
            'type_effectiveness': type_effectiveness,
            'improvement_recommendations': self._generate_improvement_recommendations(
                performance_analysis, success_patterns, type_effectiveness
            )
        }
    
    def suggest_improvements_for_chapter(
        self,
        chapter_context: Dict[str, Any],
        historical_data: List[Dict[str, Any]],
        current_questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Suggest improvements for chapter questions based on historical data.
        
        Args:
            chapter_context: Context about the current chapter
            historical_data: Historical question and response data
            current_questions: Current questions for the chapter
            
        Returns:
            Suggested improvements and optimizations
        """
        # Find similar chapters in historical data
        similar_chapters = self._find_similar_chapters(chapter_context, historical_data)
        
        # Analyze what worked well for similar chapters
        successful_patterns = self._extract_successful_patterns(similar_chapters)
        
        # Compare current questions with successful patterns
        improvement_opportunities = self._identify_improvement_opportunities(
            current_questions, successful_patterns
        )
        
        # Generate specific suggestions
        suggestions = self._generate_specific_suggestions(
            improvement_opportunities, successful_patterns, chapter_context
        )
        
        return {
            'similar_chapters_found': len(similar_chapters),
            'successful_patterns': successful_patterns,
            'improvement_opportunities': improvement_opportunities,
            'specific_suggestions': suggestions,
            'confidence_score': self._calculate_suggestion_confidence(similar_chapters, successful_patterns)
        }
    
    def predict_question_success(
        self,
        question: Dict[str, Any],
        chapter_context: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Predict how successful a question is likely to be based on historical data.
        
        Args:
            question: Question to analyze
            chapter_context: Context about the chapter
            historical_data: Historical performance data
            
        Returns:
            Success prediction with confidence score
        """
        # Extract features from the question
        question_features = self._extract_question_features(question)
        
        # Find similar questions in historical data
        similar_questions = self._find_similar_questions(question_features, historical_data)
        
        if not similar_questions:
            return {
                'predicted_success_score': 0.5,  # Neutral prediction
                'confidence': 0.1,
                'reasoning': 'No similar questions found in historical data',
                'recommendations': ['Monitor performance and collect feedback']
            }
        
        # Calculate predicted success based on similar questions
        success_scores = [q.get('success_score', 0.5) for q in similar_questions]
        predicted_score = statistics.mean(success_scores)
        confidence = self._calculate_prediction_confidence(similar_questions, question_features)
        
        # Generate reasoning and recommendations
        reasoning = self._generate_prediction_reasoning(similar_questions, question_features)
        recommendations = self._generate_prediction_recommendations(predicted_score, similar_questions)
        
        return {
            'predicted_success_score': round(predicted_score, 2),
            'confidence': round(confidence, 2),
            'similar_questions_count': len(similar_questions),
            'reasoning': reasoning,
            'recommendations': recommendations,
            'risk_factors': self._identify_risk_factors(question_features, similar_questions)
        }
    
    def optimize_question_sequence(
        self,
        questions: List[Dict[str, Any]],
        historical_data: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Optimize the sequence of questions based on historical engagement patterns.
        
        Args:
            questions: List of questions to sequence
            historical_data: Historical engagement data
            user_profile: Optional user profile for personalization
            
        Returns:
            Optimized sequence of questions
        """
        if not questions:
            return questions
        
        # Analyze historical sequence patterns
        sequence_patterns = self._analyze_sequence_patterns(historical_data, user_profile)
        
        # Score questions based on optimal positioning
        scored_questions = []
        for question in questions:
            position_score = self._calculate_position_score(question, sequence_patterns)
            scored_questions.append((position_score, question))
        
        # Sort by optimal position and difficulty progression
        optimized_sequence = self._create_optimal_sequence(scored_questions, sequence_patterns)
        
        return optimized_sequence
    
    def _parse_date(self, date_string: str) -> datetime:
        """Parse date string safely."""
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.min.replace(tzinfo=timezone.utc)
    
    def _analyze_performance_metrics(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze basic performance metrics for questions."""
        if not questions:
            return {}
        
        # Response rates
        total_questions = len(questions)
        questions_with_responses = len([q for q in questions if q.get('response_count', 0) > 0])
        response_rate = questions_with_responses / total_questions if total_questions > 0 else 0
        
        # Average ratings
        ratings = [q.get('average_rating') for q in questions if q.get('average_rating') is not None]
        avg_rating = statistics.mean(ratings) if ratings else None
        
        # Completion rates
        completion_rates = [q.get('completion_rate', 0) for q in questions]
        avg_completion_rate = statistics.mean(completion_rates) if completion_rates else 0
        
        # Response quality scores
        quality_scores = [q.get('avg_response_quality', 0) for q in questions]
        avg_quality_score = statistics.mean(quality_scores) if quality_scores else 0
        
        return {
            'response_rate': round(response_rate, 2),
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'average_completion_rate': round(avg_completion_rate, 2),
            'average_response_quality': round(avg_quality_score, 2),
            'total_questions': total_questions,
            'questions_with_responses': questions_with_responses
        }
    
    def _identify_success_patterns(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in successful questions."""
        # Define success criteria
        successful_questions = [
            q for q in questions 
            if q.get('average_rating', 0) >= 4.0 and q.get('completion_rate', 0) >= 0.7
        ]
        
        if not successful_questions:
            return {'patterns': [], 'insights': ['Not enough successful questions to identify patterns']}
        
        patterns = {}
        
        # Question type patterns
        type_success_rates = defaultdict(list)
        for question in questions:
            q_type = question.get('question_type', 'unknown')
            success_score = self._calculate_question_success_score(question)
            type_success_rates[q_type].append(success_score)
        
        # Calculate average success by type
        type_averages = {
            q_type: statistics.mean(scores) 
            for q_type, scores in type_success_rates.items()
        }
        patterns['successful_question_types'] = sorted(
            type_averages.items(), key=lambda x: x[1], reverse=True
        )
        
        # Difficulty patterns
        difficulty_success = defaultdict(list)
        for question in questions:
            difficulty = question.get('difficulty', 'medium')
            success_score = self._calculate_question_success_score(question)
            difficulty_success[difficulty].append(success_score)
        
        patterns['optimal_difficulty_distribution'] = {
            difficulty: statistics.mean(scores)
            for difficulty, scores in difficulty_success.items()
        }
        
        # Length patterns
        successful_lengths = [len(q.get('question_text', '').split()) for q in successful_questions]
        if successful_lengths:
            patterns['optimal_question_length'] = {
                'average': round(statistics.mean(successful_lengths), 1),
                'range': f"{min(successful_lengths)}-{max(successful_lengths)} words"
            }
        
        return patterns
    
    def _analyze_user_engagement(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user engagement patterns."""
        engagement_data = {
            'total_responses': sum(q.get('response_count', 0) for q in questions),
            'total_time_spent': sum(q.get('avg_time_spent', 0) for q in questions),
            'feedback_given': sum(q.get('feedback_count', 0) for q in questions)
        }
        
        # Engagement by question characteristics
        engagement_by_type = defaultdict(lambda: {'responses': 0, 'time': 0, 'count': 0})
        for question in questions:
            q_type = question.get('question_type', 'unknown')
            engagement_by_type[q_type]['responses'] += question.get('response_count', 0)
            engagement_by_type[q_type]['time'] += question.get('avg_time_spent', 0)
            engagement_by_type[q_type]['count'] += 1
        
        # Calculate averages
        type_engagement = {}
        for q_type, data in engagement_by_type.items():
            if data['count'] > 0:
                type_engagement[q_type] = {
                    'avg_responses': round(data['responses'] / data['count'], 1),
                    'avg_time_spent': round(data['time'] / data['count'], 1)
                }
        
        engagement_data['engagement_by_type'] = type_engagement
        
        return engagement_data
    
    def _analyze_question_type_effectiveness(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze which question types are most effective."""
        type_metrics = defaultdict(lambda: {
            'count': 0,
            'total_rating': 0,
            'total_completion': 0,
            'total_quality': 0
        })
        
        for question in questions:
            q_type = question.get('question_type', 'unknown')
            metrics = type_metrics[q_type]
            
            metrics['count'] += 1
            metrics['total_rating'] += question.get('average_rating', 0)
            metrics['total_completion'] += question.get('completion_rate', 0)
            metrics['total_quality'] += question.get('avg_response_quality', 0)
        
        # Calculate effectiveness scores
        effectiveness = {}
        for q_type, metrics in type_metrics.items():
            if metrics['count'] > 0:
                effectiveness[q_type] = {
                    'count': metrics['count'],
                    'avg_rating': round(metrics['total_rating'] / metrics['count'], 2),
                    'avg_completion': round(metrics['total_completion'] / metrics['count'], 2),
                    'avg_quality': round(metrics['total_quality'] / metrics['count'], 2),
                    'effectiveness_score': round((
                        (metrics['total_rating'] / metrics['count']) * 0.4 +
                        (metrics['total_completion'] / metrics['count']) * 0.4 +
                        (metrics['total_quality'] / metrics['count']) * 0.2
                    ), 2)
                }
        
        return effectiveness
    
    def _generate_improvement_recommendations(
        self,
        performance_metrics: Dict[str, Any],
        success_patterns: Dict[str, Any],
        type_effectiveness: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement recommendations based on analysis."""
        recommendations = []
        
        # Response rate recommendations
        response_rate = performance_metrics.get('response_rate', 0)
        if response_rate < 0.6:
            recommendations.append("Focus on improving question clarity to increase response rates")
        
        # Rating recommendations
        avg_rating = performance_metrics.get('average_rating')
        if avg_rating and avg_rating < 3.5:
            recommendations.append("Questions need significant improvement - consider simplifying or adding examples")
        
        # Question type recommendations
        if type_effectiveness:
            best_type = max(type_effectiveness.items(), key=lambda x: x[1].get('effectiveness_score', 0))
            recommendations.append(f"Consider using more '{best_type[0]}' questions - they show highest effectiveness")
        
        # Success pattern recommendations
        if 'optimal_question_length' in success_patterns:
            optimal_length = success_patterns['optimal_question_length']
            recommendations.append(f"Optimal question length is {optimal_length['average']} words")
        
        return recommendations
    
    def _find_similar_chapters(
        self,
        chapter_context: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find historically similar chapters."""
        current_genre = chapter_context.get('genre', '').lower()
        current_title_words = set(chapter_context.get('title', '').lower().split())
        
        similar_chapters = []
        for data in historical_data:
            similarity_score = 0
            
            # Genre similarity
            if data.get('genre', '').lower() == current_genre:
                similarity_score += 0.4
            
            # Title similarity
            data_title_words = set(data.get('title', '').lower().split())
            title_overlap = len(current_title_words.intersection(data_title_words))
            if title_overlap > 0:
                similarity_score += min(0.3, title_overlap * 0.1)
            
            # Content length similarity
            current_length = len(chapter_context.get('content', ''))
            data_length = len(data.get('content', ''))
            if current_length > 0 and data_length > 0:
                length_ratio = min(current_length, data_length) / max(current_length, data_length)
                similarity_score += length_ratio * 0.3
            
            if similarity_score >= 0.3:  # Threshold for similarity
                data['similarity_score'] = similarity_score
                similar_chapters.append(data)
        
        return sorted(similar_chapters, key=lambda x: x['similarity_score'], reverse=True)[:10]
    
    def _extract_successful_patterns(self, similar_chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from successful similar chapters."""
        if not similar_chapters:
            return {}
        
        # Filter for successful chapters (high engagement and ratings)
        successful = [
            ch for ch in similar_chapters 
            if ch.get('avg_rating', 0) >= 4.0 and ch.get('completion_rate', 0) >= 0.7
        ]
        
        if not successful:
            return {'warning': 'No highly successful similar chapters found'}
        
        patterns = {}
        
        # Question type distribution in successful chapters
        type_counts = Counter()
        for chapter in successful:
            for question in chapter.get('questions', []):
                type_counts[question.get('question_type')] += 1
        
        patterns['successful_question_types'] = dict(type_counts.most_common())
        
        # Optimal question count
        question_counts = [len(ch.get('questions', [])) for ch in successful]
        if question_counts:
            patterns['optimal_question_count'] = {
                'average': round(statistics.mean(question_counts), 1),
                'range': f"{min(question_counts)}-{max(question_counts)}"
            }
        
        return patterns
    
    def _identify_improvement_opportunities(
        self,
        current_questions: List[Dict[str, Any]],
        successful_patterns: Dict[str, Any]
    ) -> List[str]:
        """Identify specific improvement opportunities."""
        opportunities = []
        
        if not successful_patterns:
            return ['No historical data available for comparison']
        
        # Check question count
        current_count = len(current_questions)
        optimal_range = successful_patterns.get('optimal_question_count', {})
        if optimal_range:
            avg_optimal = optimal_range.get('average', current_count)
            if current_count < avg_optimal * 0.8:
                opportunities.append(f"Consider adding more questions (optimal: ~{avg_optimal})")
            elif current_count > avg_optimal * 1.2:
                opportunities.append(f"Consider reducing question count (optimal: ~{avg_optimal})")
        
        # Check question type distribution
        current_types = Counter(q.get('question_type') for q in current_questions)
        successful_types = successful_patterns.get('successful_question_types', {})
        
        if successful_types:
            top_successful_type = max(successful_types.items(), key=lambda x: x[1])[0]
            if current_types.get(top_successful_type, 0) == 0:
                opportunities.append(f"Consider adding '{top_successful_type}' questions - they perform well historically")
        
        return opportunities
    
    def _generate_specific_suggestions(
        self,
        opportunities: List[str],
        successful_patterns: Dict[str, Any],
        chapter_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific, actionable suggestions."""
        suggestions = []
        
        for opportunity in opportunities:
            if "adding more questions" in opportunity:
                suggestions.append({
                    'type': 'add_questions',
                    'priority': 'medium',
                    'description': opportunity,
                    'action': 'Generate additional questions to reach optimal count'
                })
            
            elif "reducing question count" in opportunity:
                suggestions.append({
                    'type': 'reduce_questions',
                    'priority': 'low',
                    'description': opportunity,
                    'action': 'Remove lowest-performing questions to optimize count'
                })
            
            elif "adding" in opportunity and "questions" in opportunity:
                question_type = opportunity.split("'")[1] if "'" in opportunity else "character"
                suggestions.append({
                    'type': 'add_question_type',
                    'priority': 'high',
                    'description': opportunity,
                    'action': f'Add more {question_type} questions',
                    'question_type': question_type
                })
        
        return suggestions
    
    def _calculate_suggestion_confidence(
        self,
        similar_chapters: List[Dict[str, Any]],
        successful_patterns: Dict[str, Any]
    ) -> float:
        """Calculate confidence in suggestions."""
        confidence = 0.0
        
        # Base confidence on number of similar chapters
        if len(similar_chapters) >= 5:
            confidence += 0.4
        elif len(similar_chapters) >= 3:
            confidence += 0.3
        else:
            confidence += 0.1
        
        # Boost confidence if patterns are clear
        if successful_patterns and len(successful_patterns) > 2:
            confidence += 0.3
        
        # Consider recency of data
        recent_chapters = [
            ch for ch in similar_chapters 
            if self._parse_date(ch.get('created_at', '')) > datetime.now(timezone.utc) - timedelta(days=90)
        ]
        
        if len(recent_chapters) > len(similar_chapters) * 0.5:
            confidence += 0.3
        
        return min(1.0, confidence)
    
    def _extract_question_features(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from a question for similarity matching."""
        text = question.get('question_text', '')
        return {
            'length': len(text.split()),
            'question_type': question.get('question_type', 'unknown'),
            'difficulty': question.get('difficulty', 'medium'),
            'has_examples': bool(question.get('examples')),
            'word_count': len(text.split()),
            'character_count': len(text),
            'contains_how': 'how' in text.lower(),
            'contains_what': 'what' in text.lower(),
            'contains_why': 'why' in text.lower()
        }
    
    def _find_similar_questions(
        self,
        question_features: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find similar questions in historical data."""
        similar_questions = []
        
        for data in historical_data:
            for question in data.get('questions', []):
                similarity_score = self._calculate_question_similarity(
                    question_features, question
                )
                
                if similarity_score >= 0.5:  # Similarity threshold
                    question['similarity_score'] = similarity_score
                    similar_questions.append(question)
        
        return sorted(similar_questions, key=lambda x: x['similarity_score'], reverse=True)[:20]
    
    def _calculate_question_similarity(
        self,
        features1: Dict[str, Any],
        question2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two questions."""
        features2 = self._extract_question_features(question2)
        
        similarity = 0.0
        
        # Type similarity (high weight)
        if features1['question_type'] == features2['question_type']:
            similarity += 0.4
        
        # Difficulty similarity
        if features1['difficulty'] == features2['difficulty']:
            similarity += 0.2
        
        # Length similarity
        length1, length2 = features1['length'], features2['length']
        if length1 > 0 and length2 > 0:
            length_ratio = min(length1, length2) / max(length1, length2)
            similarity += length_ratio * 0.2
        
        # Question word patterns
        pattern_score = 0
        pattern_count = 0
        for key in ['contains_how', 'contains_what', 'contains_why']:
            if features1[key] == features2[key]:
                pattern_score += 1
            pattern_count += 1
        
        if pattern_count > 0:
            similarity += (pattern_score / pattern_count) * 0.2
        
        return similarity
    
    def _calculate_question_success_score(self, question: Dict[str, Any]) -> float:
        """Calculate a composite success score for a question."""
        rating = question.get('average_rating', 0)
        completion = question.get('completion_rate', 0)
        quality = question.get('avg_response_quality', 0)
        
        # Weighted average
        return (rating * 0.4 + completion * 0.4 + quality * 0.2) / 5.0  # Normalize to 0-1
    
    def _calculate_prediction_confidence(
        self,
        similar_questions: List[Dict[str, Any]],
        question_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence in success prediction."""
        if not similar_questions:
            return 0.1
        
        # Base confidence on number of similar questions
        confidence = min(0.5, len(similar_questions) * 0.1)
        
        # Boost confidence for high similarity scores
        avg_similarity = statistics.mean(q.get('similarity_score', 0) for q in similar_questions)
        confidence += avg_similarity * 0.3
        
        # Consider consistency of success scores
        success_scores = [self._calculate_question_success_score(q) for q in similar_questions]
        if len(success_scores) > 1:
            consistency = 1.0 - statistics.stdev(success_scores)
            confidence += consistency * 0.2
        
        return min(1.0, confidence)
    
    def _generate_prediction_reasoning(
        self,
        similar_questions: List[Dict[str, Any]],
        question_features: Dict[str, Any]
    ) -> str:
        """Generate reasoning for the success prediction."""
        if not similar_questions:
            return "No similar questions found for comparison"
        
        avg_success = statistics.mean(
            self._calculate_question_success_score(q) for q in similar_questions
        )
        
        if avg_success >= 0.7:
            return f"Similar questions have performed well historically (avg success: {avg_success:.1%})"
        elif avg_success >= 0.5:
            return f"Similar questions have moderate performance (avg success: {avg_success:.1%})"
        else:
            return f"Similar questions have struggled historically (avg success: {avg_success:.1%})"
    
    def _generate_prediction_recommendations(
        self,
        predicted_score: float,
        similar_questions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on prediction."""
        recommendations = []
        
        if predicted_score < 0.5:
            recommendations.append("Consider revising question for better clarity")
            recommendations.append("Add examples or help text to improve understanding")
        elif predicted_score < 0.7:
            recommendations.append("Monitor performance and gather feedback")
            recommendations.append("Consider minor adjustments based on user responses")
        else:
            recommendations.append("Question shows strong potential")
            recommendations.append("Use as a template for similar questions")
        
        return recommendations
    
    def _identify_risk_factors(
        self,
        question_features: Dict[str, Any],
        similar_questions: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify potential risk factors for question performance."""
        risks = []
        
        # Length risks
        if question_features['length'] > 30:
            risks.append("Question may be too long - consider shortening")
        elif question_features['length'] < 5:
            risks.append("Question may be too brief - consider adding context")
        
        # Historical pattern risks
        if similar_questions:
            low_performers = [q for q in similar_questions if self._calculate_question_success_score(q) < 0.4]
            if len(low_performers) > len(similar_questions) * 0.5:
                risks.append("Similar questions have historically underperformed")
        
        return risks
    
    def _analyze_sequence_patterns(
        self,
        historical_data: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze optimal question sequencing patterns."""
        # This is a simplified version - in practice would be more sophisticated
        patterns = {
            'optimal_start_types': ['character', 'setting'],  # Easier questions first
            'optimal_end_types': ['theme', 'research'],       # Complex questions last
            'difficulty_progression': 'easy_to_hard',
            'type_transitions': {
                'character': ['plot', 'setting'],
                'plot': ['character', 'theme'],
                'setting': ['character', 'plot'],
                'theme': ['research', 'character']
            }
        }
        
        return patterns
    
    def _calculate_position_score(
        self,
        question: Dict[str, Any],
        sequence_patterns: Dict[str, Any]
    ) -> float:
        """Calculate optimal position score for a question."""

        score = 0.5  # Base score
        
        question_type = question.get('question_type', 'unknown')
        difficulty = question.get('difficulty', 'medium')
        
        # Prefer easier questions at the start
        if question_type in sequence_patterns.get('optimal_start_types', []):
            score += 0.3
        
        # Prefer complex questions at the end
        if question_type in sequence_patterns.get('optimal_end_types', []):
            score += 0.2
        
        # Difficulty progression consideration
        if difficulty == 'easy':
            score += 0.1  # Slightly prefer easier questions
        elif difficulty == 'hard':
            score -= 0.1  # Slightly prefer to place later
        
        return score
    
    def _create_optimal_sequence(
        self,
        scored_questions: List[Tuple[float, Dict[str, Any]]],
        sequence_patterns: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create optimally sequenced list of questions."""
        # Sort by position score first
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        
        # Apply difficulty progression
        progression = sequence_patterns.get('difficulty_progression', 'easy_to_hard')
        
        if progression == 'easy_to_hard':
            # Sort by difficulty within similar position scores
            difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
            scored_questions.sort(
                key=lambda x: (x[0], difficulty_order.get(x[1].get('difficulty', 'medium'), 2)),
                reverse=True
            )
        
        return [question for score, question in scored_questions]


# Singleton instance
historical_data_service = HistoricalDataService()

