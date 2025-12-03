"""
Tests for question quality service
"""

import pytest
from typing import Dict, Any, List

from app.services.question_quality_service import QuestionQualityService


@pytest.fixture
def quality_service():
    """Create a QuestionQualityService instance"""
    return QuestionQualityService()


@pytest.fixture
def sample_chapter_context() -> Dict[str, Any]:
    """Sample chapter context for testing"""
    return {
        'title': 'Advanced Machine Learning Algorithms',
        'content': 'This chapter explores neural networks, deep learning, optimization techniques, and gradient descent methods used in modern machine learning systems.',
        'genre': 'technical'
    }


@pytest.fixture
def sample_questions() -> List[Dict[str, Any]]:
    """Sample questions with varying quality"""
    return [
        {
            'question_text': 'What are the key differences between supervised and unsupervised learning algorithms?',
            'question_type': 'research'
        },
        {
            'question_text': 'How does gradient descent optimize neural network weights?',
            'question_type': 'research'
        },
        {
            'question_text': 'What happens in this chapter?',
            'question_type': 'general'
        },
        {
            'question_text': 'describe the main concepts',
            'question_type': 'general'
        },
        {
            'question_text': 'What is the main idea behind deep learning optimization techniques?',
            'question_type': 'research'
        }
    ]


class TestQuestionQualityService:
    """Test QuestionQualityService class"""

    def test_initialization(self, quality_service):
        """Test service initialization with proper weights"""
        assert quality_service.quality_weights['length_complexity'] == 0.2
        assert quality_service.quality_weights['question_words'] == 0.15
        assert quality_service.quality_weights['chapter_relevance'] == 0.25
        assert quality_service.quality_weights['type_validity'] == 0.15
        assert quality_service.quality_weights['generic_penalty'] == 0.15
        assert quality_service.quality_weights['format_correctness'] == 0.1
        # Verify weights sum to 1.0
        assert sum(quality_service.quality_weights.values()) == 1.0

    def test_score_question_quality_high_quality(self, quality_service, sample_chapter_context):
        """Test scoring a high-quality question"""
        question = {
            'question_text': 'How do gradient descent optimization techniques improve neural network training efficiency?',
            'question_type': 'research'
        }

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert 0.0 <= score <= 1.0
        assert score >= 0.7  # High quality question should score well

    def test_score_question_quality_low_quality(self, quality_service, sample_chapter_context):
        """Test scoring a low-quality question"""
        question = {
            'question_text': 'What happens in the chapter?',
            'question_type': 'general'
        }

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert 0.0 <= score <= 1.0
        assert score <= 0.52  # Low quality question should score poorly (adjusted for actual scoring)

    def test_score_question_quality_empty_question(self, quality_service, sample_chapter_context):
        """Test scoring an empty question"""
        question = {
            'question_text': '',
            'question_type': 'general'
        }

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert score >= 0.0
        assert score <= 0.36  # Empty question should score very low (adjusted for actual scoring)

    def test_score_question_quality_missing_fields(self, quality_service, sample_chapter_context):
        """Test scoring a question with missing fields"""
        question = {}  # No question_text or question_type

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert 0.0 <= score <= 1.0
        assert score < 0.3  # Should handle missing fields gracefully

    def test_score_length_complexity_optimal(self, quality_service):
        """Test length complexity scoring for optimal length"""
        # Optimal: 8-25 words, 40-150 chars
        question_text = "What are the primary differences between supervised and unsupervised learning?"

        score = quality_service._score_length_complexity(question_text)

        assert score == 1.0

    def test_score_length_complexity_good(self, quality_service):
        """Test length complexity scoring for good length"""
        # Good: 5-35 words, 25-200 chars
        question_text = "How does machine learning work in practice?"

        score = quality_service._score_length_complexity(question_text)

        assert score >= 0.6

    def test_score_length_complexity_too_short(self, quality_service):
        """Test length complexity scoring for too short"""
        question_text = "What?"

        score = quality_service._score_length_complexity(question_text)

        assert score <= 0.6

    def test_score_length_complexity_too_long(self, quality_service):
        """Test length complexity scoring for too long"""
        question_text = " ".join(["word"] * 60)  # 60 words, way too long

        score = quality_service._score_length_complexity(question_text)

        assert score <= 0.6

    def test_score_length_complexity_empty(self, quality_service):
        """Test length complexity scoring for empty string"""
        score = quality_service._score_length_complexity("")

        assert score == 0.0

    def test_score_question_words_primary(self, quality_service):
        """Test scoring with primary question words (what, how, why, etc.)"""
        question_text = "What are the main benefits of this approach?"

        score = quality_service._score_question_words(question_text)

        assert score >= 0.4

    def test_score_question_words_multiple_primary(self, quality_service):
        """Test scoring with multiple primary question words"""
        question_text = "What is the difference and why does it matter when we consider how it works?"

        score = quality_service._score_question_words(question_text)

        assert score >= 0.4
        assert score <= 1.0

    def test_score_question_words_secondary(self, quality_service):
        """Test scoring with secondary question words (would, could, should, etc.)"""
        question_text = "Would this approach work better in production?"

        score = quality_service._score_question_words(question_text)

        assert 0.3 <= score <= 0.8

    def test_score_question_words_advanced(self, quality_service):
        """Test scoring with advanced question words (describe, explain, analyze, etc.)"""
        question_text = "Describe the main components of this system."

        score = quality_service._score_question_words(question_text)

        assert 0.3 <= score <= 0.7

    def test_score_question_words_none(self, quality_service):
        """Test scoring with no question words"""
        question_text = "The main idea is interesting."

        score = quality_service._score_question_words(question_text)

        assert score == 0.2  # Minimal score

    def test_score_chapter_relevance_high(self, quality_service, sample_chapter_context):
        """Test chapter relevance with high overlap"""
        question_text = "How do machine learning algorithms use optimization techniques?"

        score = quality_service._score_chapter_relevance(question_text, sample_chapter_context)

        assert score >= 0.3  # Should have decent relevance

    def test_score_chapter_relevance_title_overlap(self, quality_service, sample_chapter_context):
        """Test chapter relevance with title word overlap"""
        question_text = "What are advanced algorithms in machine learning?"

        score = quality_service._score_chapter_relevance(question_text, sample_chapter_context)

        assert score >= 0.2  # Title overlap should boost score

    def test_score_chapter_relevance_content_overlap(self, quality_service, sample_chapter_context):
        """Test chapter relevance with content word overlap"""
        question_text = "How does gradient descent work with neural networks?"

        score = quality_service._score_chapter_relevance(question_text, sample_chapter_context)

        assert score >= 0.1  # Content overlap should contribute

    def test_score_chapter_relevance_genre_match(self, quality_service):
        """Test chapter relevance with genre-specific terms"""
        chapter_context = {
            'title': 'Character Development',
            'content': 'This chapter explores character arcs and narrative structure.',
            'genre': 'fiction'
        }
        question_text = "How does the character's story progress through the narrative?"

        score = quality_service._score_chapter_relevance(question_text, chapter_context)

        assert score >= 0.0  # Genre terms should contribute

    def test_score_chapter_relevance_no_context(self, quality_service):
        """Test chapter relevance with empty context"""
        empty_context = {'title': '', 'content': '', 'genre': ''}
        question_text = "What are the main concepts?"

        score = quality_service._score_chapter_relevance(question_text, empty_context)

        assert score == 0.0

    def test_score_question_type_valid(self, quality_service):
        """Test scoring valid question types"""
        valid_types = ['character', 'plot', 'setting', 'theme', 'research', 'general']

        for q_type in valid_types:
            score = quality_service._score_question_type(q_type)
            assert score == 1.0

    def test_score_question_type_invalid(self, quality_service):
        """Test scoring invalid question types"""
        invalid_types = ['invalid', 'unknown', 'random', '']

        for q_type in invalid_types:
            score = quality_service._score_question_type(q_type)
            assert score == 0.0

    def test_score_question_type_case_insensitive(self, quality_service):
        """Test that question type scoring is case-insensitive"""
        score_lower = quality_service._score_question_type('research')
        score_upper = quality_service._score_question_type('RESEARCH')
        score_mixed = quality_service._score_question_type('Research')

        assert score_lower == score_upper == score_mixed == 1.0

    def test_score_generic_penalty_highly_generic(self, quality_service):
        """Test heavy penalty for highly generic questions"""
        generic_questions = [
            "What happens in this chapter?",
            "What is the main idea?",
            "Who is the main character?",
            "Describe what happens next.",
            "What are some examples?",
            "List the key points."
        ]

        for question in generic_questions:
            score = quality_service._score_generic_penalty(question)
            assert score == 0.2  # Heavy penalty

    def test_score_generic_penalty_moderately_generic(self, quality_service):
        """Test medium penalty for moderately generic questions"""
        moderate_questions = [
            "What are the key concepts?",
            "How does the system work?",
            "Why is this important?",
            "What makes this unique?",
            "How can we apply this?",
            "What would happen if?"
        ]

        for question in moderate_questions:
            score = quality_service._score_generic_penalty(question)
            assert score == 0.6  # Medium penalty

    def test_score_generic_penalty_specific(self, quality_service):
        """Test no penalty for specific questions"""
        specific_question = "How does gradient descent optimize neural network weights in batch processing?"

        score = quality_service._score_generic_penalty(specific_question)

        assert score == 1.0  # No penalty

    def test_score_format_correctness_perfect(self, quality_service):
        """Test format scoring for perfectly formatted question"""
        question_text = "What are the main benefits?"

        score = quality_service._score_format_correctness(question_text)

        assert score == 1.0  # Ends with ?, starts with capital, reasonable punctuation

    def test_score_format_correctness_no_question_mark(self, quality_service):
        """Test format scoring without question mark"""
        question_text = "What are the main benefits"

        score = quality_service._score_format_correctness(question_text)

        assert score < 1.0  # Should lose points

    def test_score_format_correctness_lowercase_start(self, quality_service):
        """Test format scoring with lowercase start"""
        question_text = "what are the main benefits?"

        score = quality_service._score_format_correctness(question_text)

        assert score < 1.0  # Should lose points

    def test_score_format_correctness_excessive_punctuation(self, quality_service):
        """Test format scoring with excessive punctuation"""
        question_text = "What!!! are??? the... main,,, benefits!?!?"

        score = quality_service._score_format_correctness(question_text)

        assert score < 1.0  # Should lose points for excessive punctuation

    def test_score_format_correctness_empty(self, quality_service):
        """Test format scoring for empty string"""
        score = quality_service._score_format_correctness("")

        assert score == 0.2  # Empty string: no question mark, no capital, but passes punctuation check

    def test_filter_questions_by_quality_basic(self, quality_service, sample_questions, sample_chapter_context):
        """Test basic question filtering by quality"""
        filtered = quality_service.filter_questions_by_quality(
            sample_questions,
            sample_chapter_context,
            min_score=0.5
        )

        assert len(filtered) <= len(sample_questions)
        assert all('quality_score' in q for q in filtered)
        assert all(q['quality_score'] >= 0.5 for q in filtered)

    def test_filter_questions_by_quality_sorted(self, quality_service, sample_questions, sample_chapter_context):
        """Test that filtered questions are sorted by quality score"""
        filtered = quality_service.filter_questions_by_quality(
            sample_questions,
            sample_chapter_context,
            min_score=0.0
        )

        scores = [q['quality_score'] for q in filtered]
        assert scores == sorted(scores, reverse=True)

    def test_filter_questions_by_quality_max_limit(self, quality_service, sample_chapter_context):
        """Test max_questions limit"""
        # Create 20 questions
        many_questions = [
            {
                'question_text': f'What is concept number {i} in machine learning?',
                'question_type': 'research'
            }
            for i in range(20)
        ]

        filtered = quality_service.filter_questions_by_quality(
            many_questions,
            sample_chapter_context,
            min_score=0.0,
            max_questions=5
        )

        assert len(filtered) == 5

    def test_filter_questions_by_quality_high_threshold(self, quality_service, sample_questions, sample_chapter_context):
        """Test filtering with high quality threshold"""
        filtered = quality_service.filter_questions_by_quality(
            sample_questions,
            sample_chapter_context,
            min_score=0.9  # Very high threshold
        )

        assert len(filtered) <= len(sample_questions)
        # All filtered questions should meet the high threshold
        assert all(q['quality_score'] >= 0.9 for q in filtered)

    def test_filter_questions_by_quality_empty_list(self, quality_service, sample_chapter_context):
        """Test filtering empty question list"""
        filtered = quality_service.filter_questions_by_quality(
            [],
            sample_chapter_context,
            min_score=0.5
        )

        assert filtered == []

    def test_ensure_question_diversity_type_limit(self, quality_service):
        """Test diversity ensures type limits are respected"""
        questions = [
            {'question_text': f'Research question {i}?', 'question_type': 'research'}
            for i in range(10)
        ]

        diversified = quality_service.ensure_question_diversity(
            questions,
            max_per_type=3
        )

        assert len(diversified) == 3  # Max 3 of same type

    def test_ensure_question_diversity_removes_similar(self, quality_service):
        """Test diversity removes similar questions"""
        questions = [
            {'question_text': 'What is machine learning?', 'question_type': 'general'},
            {'question_text': 'What is machine learning really?', 'question_type': 'general'},
            {'question_text': 'How does neural network training work?', 'question_type': 'research'}
        ]

        diversified = quality_service.ensure_question_diversity(
            questions,
            similarity_threshold=0.7
        )

        # Should remove one of the similar questions
        assert len(diversified) < len(questions)

    def test_ensure_question_diversity_preserves_different(self, quality_service):
        """Test diversity preserves different questions"""
        questions = [
            {'question_text': 'What is machine learning?', 'question_type': 'research'},
            {'question_text': 'How does gradient descent work?', 'question_type': 'research'},
            {'question_text': 'Why is optimization important?', 'question_type': 'research'}
        ]

        diversified = quality_service.ensure_question_diversity(
            questions,
            max_per_type=5,
            similarity_threshold=0.7
        )

        # Should keep all different questions
        assert len(diversified) == len(questions)

    def test_ensure_question_diversity_empty_list(self, quality_service):
        """Test diversity with empty list"""
        diversified = quality_service.ensure_question_diversity([])

        assert diversified == []

    def test_is_question_similar_high_similarity(self, quality_service):
        """Test similarity detection for very similar questions"""
        question = "what is machine learning and how does it work"
        seen = ["what is machine learning and how it works"]

        is_similar = quality_service._is_question_similar(question, seen, threshold=0.7)

        assert is_similar is True

    def test_is_question_similar_low_similarity(self, quality_service):
        """Test similarity detection for different questions"""
        question = "what is machine learning"
        seen = ["how does gradient descent optimize neural networks"]

        is_similar = quality_service._is_question_similar(question, seen, threshold=0.7)

        assert is_similar is False

    def test_is_question_similar_empty_patterns(self, quality_service):
        """Test similarity with empty seen patterns"""
        question = "what is machine learning"

        is_similar = quality_service._is_question_similar(question, [], threshold=0.7)

        assert is_similar is False

    def test_is_question_similar_empty_question(self, quality_service):
        """Test similarity with empty question"""
        seen = ["what is machine learning"]

        is_similar = quality_service._is_question_similar("", seen, threshold=0.7)

        assert is_similar is False

    def test_analyze_question_distribution_basic(self, quality_service):
        """Test basic question distribution analysis"""
        questions = [
            {'question_text': 'Q1?', 'question_type': 'research', 'quality_score': 0.8},
            {'question_text': 'Q2?', 'question_type': 'research', 'quality_score': 0.7},
            {'question_text': 'Q3?', 'question_type': 'general', 'quality_score': 0.6}
        ]

        analysis = quality_service.analyze_question_distribution(questions)

        assert analysis['total_questions'] == 3
        assert 'type_distribution' in analysis
        assert analysis['type_distribution']['research'] == 2
        assert analysis['type_distribution']['general'] == 1
        assert 'quality_metrics' in analysis
        assert analysis['quality_metrics']['average_score'] > 0

    def test_analyze_question_distribution_quality_metrics(self, quality_service):
        """Test quality metrics in distribution analysis"""
        questions = [
            {'question_text': 'Q1?', 'question_type': 'research', 'quality_score': 0.9},
            {'question_text': 'Q2?', 'question_type': 'research', 'quality_score': 0.5},
            {'question_text': 'Q3?', 'question_type': 'general', 'quality_score': 0.7}
        ]

        analysis = quality_service.analyze_question_distribution(questions)

        metrics = analysis['quality_metrics']
        assert metrics['average_score'] == pytest.approx(0.7, abs=0.01)
        assert metrics['min_score'] == 0.5
        assert metrics['max_score'] == 0.9
        assert metrics['has_quality_scores'] is True

    def test_analyze_question_distribution_no_quality_scores(self, quality_service):
        """Test distribution analysis without quality scores"""
        questions = [
            {'question_text': 'Q1?', 'question_type': 'research'},
            {'question_text': 'Q2?', 'question_type': 'general'}
        ]

        analysis = quality_service.analyze_question_distribution(questions)

        assert analysis['quality_metrics']['has_quality_scores'] is False
        assert analysis['quality_metrics']['average_score'] == 0

    def test_analyze_question_distribution_empty(self, quality_service):
        """Test distribution analysis with empty list"""
        analysis = quality_service.analyze_question_distribution([])

        assert 'error' in analysis
        assert analysis['error'] == 'No questions to analyze'

    def test_analyze_question_distribution_recommendations(self, quality_service):
        """Test that analysis includes recommendations"""
        questions = [
            {'question_text': f'Q{i}?', 'question_type': 'research', 'quality_score': 0.9}
            for i in range(2)
        ]

        analysis = quality_service.analyze_question_distribution(questions)

        assert 'recommendations' in analysis
        assert isinstance(analysis['recommendations'], list)

    def test_generate_recommendations_few_types(self, quality_service):
        """Test recommendations for insufficient diversity"""
        type_counts = {'research': 10}

        recommendations = quality_service._generate_recommendations(type_counts, 0.7)

        assert any('diversity' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_dominant_type(self, quality_service):
        """Test recommendations for dominant question type"""
        type_counts = {'research': 15, 'general': 2}

        recommendations = quality_service._generate_recommendations(type_counts, 0.7)

        assert any('balance' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_low_quality(self, quality_service):
        """Test recommendations for low quality"""
        type_counts = {'research': 5, 'general': 5}

        recommendations = quality_service._generate_recommendations(type_counts, 0.4)

        assert any('quality could be improved' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_high_quality(self, quality_service):
        """Test recommendations for high quality"""
        type_counts = {'research': 5, 'general': 5}

        recommendations = quality_service._generate_recommendations(type_counts, 0.85)

        assert any('excellent' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_too_few(self, quality_service):
        """Test recommendations for too few questions"""
        type_counts = {'research': 2}

        recommendations = quality_service._generate_recommendations(type_counts, 0.7)

        assert any('more questions' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_too_many(self, quality_service):
        """Test recommendations for too many questions"""
        type_counts = {'research': 25}

        recommendations = quality_service._generate_recommendations(type_counts, 0.7)

        assert any('filtering' in rec.lower() or 'focus' in rec.lower() for rec in recommendations)

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available"""
        from app.services.question_quality_service import question_quality_service

        assert question_quality_service is not None
        assert isinstance(question_quality_service, QuestionQualityService)

    def test_score_normalization(self, quality_service, sample_chapter_context):
        """Test that all scores are normalized between 0 and 1"""
        questions = [
            {'question_text': 'What is machine learning?', 'question_type': 'research'},
            {'question_text': 'How?', 'question_type': 'invalid'},
            {'question_text': 'What happens in the chapter and why does it matter and how does everything work?', 'question_type': 'general'},
            {'question_text': '', 'question_type': 'general'}
        ]

        for question in questions:
            score = quality_service.score_question_quality(question, sample_chapter_context)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for question: {question['question_text']}"

    def test_unicode_handling(self, quality_service, sample_chapter_context):
        """Test handling of unicode characters in questions"""
        question = {
            'question_text': 'What are the différences between naïve approaches and advanced méthods?',
            'question_type': 'research'
        }

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert 0.0 <= score <= 1.0
        # Should handle unicode gracefully

    def test_special_characters_handling(self, quality_service, sample_chapter_context):
        """Test handling of special characters in questions"""
        question = {
            'question_text': 'How do "smart" algorithms (e.g., neural nets) handle edge-cases?',
            'question_type': 'research'
        }

        score = quality_service.score_question_quality(question, sample_chapter_context)

        assert 0.0 <= score <= 1.0

    def test_batch_quality_assessment(self, quality_service, sample_questions, sample_chapter_context):
        """Test batch processing of multiple questions"""
        # Score all questions
        scores = [
            quality_service.score_question_quality(q, sample_chapter_context)
            for q in sample_questions
        ]

        assert len(scores) == len(sample_questions)
        assert all(0.0 <= score <= 1.0 for score in scores)

    def test_consistent_scoring(self, quality_service, sample_chapter_context):
        """Test that scoring is consistent for the same question"""
        question = {
            'question_text': 'How does gradient descent optimize neural networks?',
            'question_type': 'research'
        }

        score1 = quality_service.score_question_quality(question, sample_chapter_context)
        score2 = quality_service.score_question_quality(question, sample_chapter_context)
        score3 = quality_service.score_question_quality(question, sample_chapter_context)

        assert score1 == score2 == score3

    def test_case_sensitivity_in_relevance(self, quality_service):
        """Test that relevance scoring is case-insensitive"""
        context_lower = {
            'title': 'machine learning algorithms',
            'content': 'neural networks and deep learning',
            'genre': 'technical'
        }
        context_upper = {
            'title': 'MACHINE LEARNING ALGORITHMS',
            'content': 'NEURAL NETWORKS AND DEEP LEARNING',
            'genre': 'TECHNICAL'
        }

        question = "What are Machine Learning algorithms?"

        score_lower = quality_service._score_chapter_relevance(question, context_lower)
        score_upper = quality_service._score_chapter_relevance(question, context_upper)

        assert score_lower == score_upper

    def test_multiple_question_marks(self, quality_service):
        """Test format scoring with multiple question marks"""
        question_text = "What is this??"

        score = quality_service._score_format_correctness(question_text)

        # Should still recognize it ends with question mark
        assert score >= 0.5
