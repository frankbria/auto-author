"""
Question Quality Service - Advanced algorithms for scoring and filtering questions.
"""

import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QuestionQualityService:
    """Service for scoring question quality and ensuring diversity."""
    
    def __init__(self):
        self.quality_weights = {
            'length_complexity': 0.2,
            'question_words': 0.15,
            'chapter_relevance': 0.25,
            'type_validity': 0.15,
            'generic_penalty': 0.15,
            'format_correctness': 0.1
        }
    
    def score_question_quality(self, question: Dict[str, Any], chapter_context: Dict[str, Any]) -> float:
        """
        Score the quality of a generated question based on multiple criteria.
        
        Args:
            question: Question dictionary with text, type, etc.
            chapter_context: Context about the chapter (title, content, metadata)
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        question_text = question.get('question_text', '')
        question_type = question.get('question_type', '')
        
        # Criterion 1: Question length and complexity
        length_score = self._score_length_complexity(question_text)
        score += length_score * self.quality_weights['length_complexity']
        
        # Criterion 2: Contains appropriate question words
        question_words_score = self._score_question_words(question_text)
        score += question_words_score * self.quality_weights['question_words']
        
        # Criterion 3: Relevance to chapter title/content
        relevance_score = self._score_chapter_relevance(question_text, chapter_context)
        score += relevance_score * self.quality_weights['chapter_relevance']
        
        # Criterion 4: Valid question type
        type_score = self._score_question_type(question_type)
        score += type_score * self.quality_weights['type_validity']
        
        # Criterion 5: Avoid generic/template questions
        generic_score = self._score_generic_penalty(question_text)
        score += generic_score * self.quality_weights['generic_penalty']
        
        # Criterion 6: Proper formatting
        format_score = self._score_format_correctness(question_text)
        score += format_score * self.quality_weights['format_correctness']
        
        return min(1.0, max(0.0, score))
    
    def _score_length_complexity(self, question_text: str) -> float:
        """Score based on optimal question length and word complexity."""
        if not question_text:
            return 0.0
            
        word_count = len(question_text.split())
        char_count = len(question_text)
        
        # Optimal ranges
        if 8 <= word_count <= 25 and 40 <= char_count <= 150:
            return 1.0
        elif 5 <= word_count <= 35 and 25 <= char_count <= 200:
            return 0.8
        elif 3 <= word_count <= 45 and 15 <= char_count <= 250:
            return 0.6
        else:
            return 0.3
    
    def _score_question_words(self, question_text: str) -> float:
        """Score based on presence of appropriate question words."""
        question_words = {
            'primary': ['what', 'how', 'why', 'when', 'where', 'who', 'which'],
            'secondary': ['would', 'could', 'should', 'might', 'can', 'will', 'do', 'does', 'did'],
            'advanced': ['describe', 'explain', 'analyze', 'compare', 'evaluate']
        }
        
        text_lower = question_text.lower()
        
        # Check for primary question words (highest value)
        primary_found = sum(1 for word in question_words['primary'] if word in text_lower)
        if primary_found > 0:
            return min(1.0, primary_found * 0.4)
        
        # Check for secondary question words
        secondary_found = sum(1 for word in question_words['secondary'] if word in text_lower)
        if secondary_found > 0:
            return min(0.8, secondary_found * 0.3)
        
        # Check for advanced question words
        advanced_found = sum(1 for word in question_words['advanced'] if word in text_lower)
        if advanced_found > 0:
            return min(0.7, advanced_found * 0.3)
        
        return 0.2  # Minimal score if no question words found
    
    def _score_chapter_relevance(self, question_text: str, chapter_context: Dict[str, Any]) -> float:
        """Score based on relevance to chapter title and content."""
        chapter_title = chapter_context.get('title', '').lower()
        chapter_content = chapter_context.get('content', '').lower()
        book_genre = chapter_context.get('genre', '').lower()
        
        question_lower = question_text.lower()
        relevance_score = 0.0
        
        # Title relevance (highest weight)
        if chapter_title:
            title_words = set(re.findall(r'\b\w+\b', chapter_title))
            question_words = set(re.findall(r'\b\w+\b', question_lower))
            title_overlap = len(title_words.intersection(question_words))
            
            if title_overlap > 0:
                relevance_score += min(0.6, title_overlap * 0.2)
        
        # Content relevance (medium weight)
        if chapter_content:
            # Simple keyword overlap check
            content_words = set(re.findall(r'\b\w{4,}\b', chapter_content))  # Words 4+ chars
            question_words = set(re.findall(r'\b\w{4,}\b', question_lower))
            content_overlap = len(content_words.intersection(question_words))
            
            if content_overlap > 0:
                relevance_score += min(0.3, content_overlap * 0.05)
        
        # Genre relevance (lower weight)
        if book_genre:
            genre_terms = {
                'fiction': ['character', 'plot', 'story', 'narrative', 'scene'],
                'non-fiction': ['concept', 'principle', 'method', 'approach', 'strategy'],
                'technical': ['process', 'system', 'implementation', 'analysis', 'design'],
                'educational': ['learn', 'understand', 'apply', 'practice', 'skill']
            }
            
            for genre_key, terms in genre_terms.items():
                if genre_key in book_genre:
                    genre_overlap = sum(1 for term in terms if term in question_lower)
                    if genre_overlap > 0:
                        relevance_score += min(0.1, genre_overlap * 0.03)
                    break
        
        return min(1.0, relevance_score)
    
    def _score_question_type(self, question_type: str) -> float:
        """Score based on valid question type."""
        valid_types = ['character', 'plot', 'setting', 'theme', 'research', 'general']
        return 1.0 if question_type.lower() in valid_types else 0.0
    
    def _score_generic_penalty(self, question_text: str) -> float:
        """Penalize overly generic or template questions."""
        text_lower = question_text.lower()
        
        # Highly generic patterns (heavy penalty)
        highly_generic = [
            'what happens in', 'what is the main', 'who is the main',
            'describe what happens', 'what are some', 'list the'
        ]
        
        # Moderately generic patterns (medium penalty)
        moderately_generic = [
            'what are the key', 'how does the', 'why is this',
            'what makes', 'how can', 'what would'
        ]
        
        # Check for highly generic patterns
        for pattern in highly_generic:
            if pattern in text_lower:
                return 0.2  # Heavy penalty
        
        # Check for moderately generic patterns
        for pattern in moderately_generic:
            if pattern in text_lower:
                return 0.6  # Medium penalty
        
        return 1.0  # No penalty for specific questions
    
    def _score_format_correctness(self, question_text: str) -> float:
        """Score based on proper question formatting."""
        score = 0.0
        
        # Ends with question mark
        if question_text.strip().endswith('?'):
            score += 0.5
        
        # Starts with capital letter
        if question_text and question_text[0].isupper():
            score += 0.3
        
        # No excessive punctuation
        punctuation_count = sum(1 for c in question_text if c in '!@#$%^&*()_+={}[]|\\:";\'<>,./')
        if punctuation_count <= 3:  # Reasonable amount
            score += 0.2
        
        return min(1.0, score)
    
    def filter_questions_by_quality(
        self, 
        questions: List[Dict[str, Any]], 
        chapter_context: Dict[str, Any], 
        min_score: float = 0.6,
        max_questions: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Filter questions based on quality score and return the best ones.
        
        Args:
            questions: List of question dictionaries
            chapter_context: Context about the chapter
            min_score: Minimum quality score threshold
            max_questions: Maximum number of questions to return
            
        Returns:
            Filtered and scored list of questions
        """
        scored_questions = []
        
        for question in questions:
            score = self.score_question_quality(question, chapter_context)
            if score >= min_score:
                question['quality_score'] = round(score, 3)
                scored_questions.append(question)
        
        # Sort by quality score (highest first)
        scored_questions.sort(key=lambda q: q.get('quality_score', 0), reverse=True)
        
        # Limit to max_questions
        return scored_questions[:max_questions]
    
    def ensure_question_diversity(
        self, 
        questions: List[Dict[str, Any]], 
        max_per_type: int = 4,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Ensure diversity in question types and avoid similar questions.
        
        Args:
            questions: List of question dictionaries
            max_per_type: Maximum questions allowed per type
            similarity_threshold: Threshold for considering questions similar
            
        Returns:
            Diversified list of questions
        """
        type_counts = {}
        diversified_questions = []
        seen_patterns = []
        
        for question in questions:
            question_text = question.get('question_text', '').lower().strip()
            question_type = question.get('question_type', 'general')
            
            # Skip if we have too many of this type already
            type_count = type_counts.get(question_type, 0)
            if type_count >= max_per_type:
                continue
            
            # Check for similarity to existing questions
            is_similar = self._is_question_similar(question_text, seen_patterns, similarity_threshold)
            if is_similar:
                continue
            
            # Add the question
            diversified_questions.append(question)
            seen_patterns.append(question_text)
            type_counts[question_type] = type_count + 1
        
        return diversified_questions
    
    def _is_question_similar(self, question_text: str, seen_patterns: List[str], threshold: float) -> bool:
        """Check if a question is too similar to existing questions."""
        question_words = set(re.findall(r'\b\w+\b', question_text.lower()))
        
        for seen_pattern in seen_patterns:
            seen_words = set(re.findall(r'\b\w+\b', seen_pattern))
            
            if len(question_words) == 0 or len(seen_words) == 0:
                continue
            
            # Calculate Jaccard similarity
            intersection = len(question_words.intersection(seen_words))
            union = len(question_words.union(seen_words))
            similarity = intersection / union if union > 0 else 0
            
            if similarity >= threshold:
                return True
        
        return False
    
    def analyze_question_distribution(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the distribution and quality metrics of a question set.
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Analysis report with metrics and recommendations
        """
        if not questions:
            return {'error': 'No questions to analyze'}
        
        # Type distribution
        type_counts = {}
        quality_scores = []
        
        for question in questions:
            q_type = question.get('question_type', 'unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
            
            if 'quality_score' in question:
                quality_scores.append(question['quality_score'])
        
        # Calculate metrics
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        min_quality = min(quality_scores) if quality_scores else 0
        max_quality = max(quality_scores) if quality_scores else 0
        
        return {
            'total_questions': len(questions),
            'type_distribution': type_counts,
            'quality_metrics': {
                'average_score': round(avg_quality, 3),
                'min_score': round(min_quality, 3),
                'max_score': round(max_quality, 3),
                'has_quality_scores': len(quality_scores) > 0
            },
            'recommendations': self._generate_recommendations(type_counts, avg_quality)
        }
    
    def _generate_recommendations(self, type_counts: Dict[str, int], avg_quality: float) -> List[str]:
        """Generate recommendations for question set improvement."""
        recommendations = []
        
        total_questions = sum(type_counts.values())
        
        # Check type balance
        if len(type_counts) < 3:
            recommendations.append("Consider adding more question types for better diversity")
        
        # Check for dominant types
        for q_type, count in type_counts.items():
            if count > total_questions * 0.6:
                recommendations.append(f"Consider reducing '{q_type}' questions for better balance")
        
        # Check quality
        if avg_quality < 0.6:
            recommendations.append("Overall question quality could be improved")
        elif avg_quality > 0.8:
            recommendations.append("Excellent question quality maintained")
        
        # Check total count
        if total_questions < 5:
            recommendations.append("Consider generating more questions for better coverage")
        elif total_questions > 20:
            recommendations.append("Consider filtering to focus on highest quality questions")
        
        return recommendations


# Singleton instance
question_quality_service = QuestionQualityService()
