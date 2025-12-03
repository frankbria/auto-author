"""
Tests for Question Feedback Service - Comprehensive test coverage for feedback processing
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from app.services.question_feedback_service import (
    QuestionFeedbackService,
    FeedbackType,
    RefinementAction,
    question_feedback_service
)


@pytest.fixture
def feedback_service():
    """Create a fresh instance of QuestionFeedbackService for testing."""
    return QuestionFeedbackService()


@pytest.fixture
def sample_feedback_data():
    """Sample feedback data for testing."""
    return {
        'type': FeedbackType.RATING,
        'rating': 4,
        'comment': 'This question was helpful and clear',
        'context': {'chapter_id': 'ch-123', 'session_id': 'sess-456'}
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing."""
    return {
        'writing_level': 'intermediate',
        'preferred_genres': ['fiction', 'mystery']
    }


@pytest.fixture
def sample_question():
    """Sample question for testing refinement."""
    return {
        'question_text': 'What motivates your character in this scene?',
        'question_type': 'character',
        'difficulty': 'medium',
        'help_text': 'Think about the character\'s goals.'
    }


class TestProcessQuestionFeedback:
    """Tests for individual feedback processing."""

    def test_process_basic_rating_feedback(self, feedback_service, sample_feedback_data, sample_user_profile):
        """Test processing basic rating feedback."""
        result = feedback_service.process_question_feedback(
            'q-123',
            sample_feedback_data,
            sample_user_profile
        )

        assert result['question_id'] == 'q-123'
        assert result['feedback_type'] == FeedbackType.RATING.value
        assert result['rating'] == 4
        assert result['comment'] == 'This question was helpful and clear'
        assert result['user_level'] == 'intermediate'
        assert result['user_genre_preference'] == ['fiction', 'mystery']
        assert 'timestamp' in result
        assert result['weight'] == 1.0
        assert 'insights' in result

    def test_process_feedback_with_string_type(self, feedback_service):
        """Test processing feedback when type is provided as string."""
        feedback_data = {
            'type': 'too_easy',
            'rating': 2,
            'comment': 'This was obvious'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        assert result['feedback_type'] == FeedbackType.TOO_EASY.value
        assert result['weight'] == 0.8

    def test_process_feedback_with_invalid_type(self, feedback_service):
        """Test processing feedback with invalid type defaults to RATING."""
        feedback_data = {
            'type': 'invalid_type',
            'rating': 3
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        assert result['feedback_type'] == FeedbackType.RATING.value

    def test_process_feedback_without_user_profile(self, feedback_service, sample_feedback_data):
        """Test processing feedback without user profile."""
        result = feedback_service.process_question_feedback('q-123', sample_feedback_data)

        assert result['user_level'] is None
        assert result['user_genre_preference'] == []

    def test_feedback_insights_low_rating(self, feedback_service):
        """Test that low ratings generate appropriate insights."""
        feedback_data = {
            'rating': 1,
            'comment': 'Very confusing and unclear'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)
        insights = result['insights']

        assert 'User found question unsatisfactory' in insights
        assert 'Question may need clearer wording' in insights

    def test_feedback_insights_high_rating(self, feedback_service):
        """Test that high ratings generate positive insights."""
        feedback_data = {
            'rating': 5,
            'comment': 'Perfect question, very helpful'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)
        insights = result['insights']

        assert 'User found question helpful' in insights

    def test_feedback_insights_difficulty_comments(self, feedback_service):
        """Test insights generation from difficulty-related comments."""
        # Too easy
        easy_feedback = {'rating': 3, 'comment': 'This was too easy and obvious'}
        result = feedback_service.process_question_feedback('q-123', easy_feedback)
        assert any('too easy' in insight.lower() for insight in result['insights'])

        # Too hard
        hard_feedback = {'rating': 3, 'comment': 'This was too difficult and complex'}
        result = feedback_service.process_question_feedback('q-123', hard_feedback)
        assert any('too challenging' in insight.lower() for insight in result['insights'])

    def test_feedback_insights_relevance_comments(self, feedback_service):
        """Test insights generation from relevance-related comments."""
        feedback_data = {
            'rating': 2,
            'comment': 'This question is irrelevant to my chapter'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)
        insights = result['insights']

        assert any('relevance' in insight.lower() for insight in insights)

    def test_feedback_type_specific_insights(self, feedback_service):
        """Test insights for specific feedback types."""
        # Repetitive feedback
        repetitive = {'type': FeedbackType.REPETITIVE, 'rating': 2}
        result = feedback_service.process_question_feedback('q-123', repetitive)
        assert any('similar' in insight.lower() for insight in result['insights'])

        # Needs examples
        needs_examples = {'type': FeedbackType.NEEDS_EXAMPLES, 'rating': 3}
        result = feedback_service.process_question_feedback('q-123', needs_examples)
        assert any('examples' in insight.lower() for insight in result['insights'])


class TestAnalyzeFeedbackTrends:
    """Tests for feedback trend analysis."""

    def test_analyze_empty_feedback(self, feedback_service):
        """Test analyzing empty feedback list."""
        result = feedback_service.analyze_question_feedback_trends([])

        assert 'error' in result
        assert result['error'] == 'No feedback data provided'

    def test_analyze_single_feedback(self, feedback_service):
        """Test analyzing single feedback entry."""
        feedbacks = [
            {
                'rating': 4,
                'feedback_type': FeedbackType.HELPFUL,
                'user_level': 'intermediate'
            }
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['total_feedback_count'] == 1
        assert result['average_rating'] == 4.0
        assert result['rating_standard_deviation'] == 0.0
        assert FeedbackType.HELPFUL in result['feedback_type_distribution']

    def test_analyze_multiple_consistent_feedback(self, feedback_service):
        """Test analyzing multiple consistent feedback entries."""
        feedbacks = [
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'rating': 5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'},
            {'rating': 4, 'feedback_type': FeedbackType.PERFECT, 'user_level': 'intermediate'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['total_feedback_count'] == 3
        assert result['average_rating'] == 4.33
        assert result['rating_standard_deviation'] < 0.6
        assert result['confidence_score'] > 0.5

    def test_analyze_mixed_feedback(self, feedback_service):
        """Test analyzing mixed feedback with different ratings."""
        feedbacks = [
            {'rating': 1, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'},
            {'rating': 5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'},
            {'rating': 3, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'intermediate'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['total_feedback_count'] == 3
        assert 1 <= result['average_rating'] <= 5
        assert result['rating_standard_deviation'] > 0
        assert len(result['level_analysis']) == 3

    def test_level_analysis_calculation(self, feedback_service):
        """Test that level-based analysis is calculated correctly."""
        feedbacks = [
            {'rating': 2, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'},
            {'rating': 2, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'},
            {'rating': 5, 'feedback_type': FeedbackType.TOO_EASY, 'user_level': 'advanced'},
            {'rating': 5, 'feedback_type': FeedbackType.TOO_EASY, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)
        level_analysis = result['level_analysis']

        assert 'beginner' in level_analysis
        assert 'advanced' in level_analysis
        assert level_analysis['beginner']['count'] == 2
        assert level_analysis['beginner']['avg_rating'] == 2.0
        assert level_analysis['advanced']['count'] == 2
        assert level_analysis['advanced']['avg_rating'] == 5.0

    def test_recommended_actions_insufficient_feedback(self, feedback_service):
        """Test that insufficient feedback results in NO_ACTION."""
        feedbacks = [
            {'rating': 2, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'intermediate'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.NO_ACTION in result['recommended_actions']

    def test_recommended_actions_poor_rating(self, feedback_service):
        """Test that poor ratings trigger removal action."""
        feedbacks = [
            {'rating': 1, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'intermediate'},
            {'rating': 2, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'beginner'},
            {'rating': 1, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.MARK_FOR_REMOVAL in result['recommended_actions']

    def test_recommended_actions_too_hard(self, feedback_service):
        """Test that TOO_HARD feedback triggers difficulty decrease."""
        feedbacks = [
            {'rating': 2.5, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'},
            {'rating': 2.8, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'intermediate'},
            {'rating': 2.5, 'feedback_type': FeedbackType.TOO_HARD, 'user_level': 'beginner'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.DECREASE_DIFFICULTY in result['recommended_actions']

    def test_recommended_actions_too_easy(self, feedback_service):
        """Test that TOO_EASY feedback triggers difficulty increase."""
        feedbacks = [
            {'rating': 2.5, 'feedback_type': FeedbackType.TOO_EASY, 'user_level': 'advanced'},
            {'rating': 2.8, 'feedback_type': FeedbackType.TOO_EASY, 'user_level': 'advanced'},
            {'rating': 2.5, 'feedback_type': FeedbackType.TOO_EASY, 'user_level': 'intermediate'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.INCREASE_DIFFICULTY in result['recommended_actions']

    def test_recommended_actions_unclear(self, feedback_service):
        """Test that UNCLEAR feedback triggers ADD_CLARITY action."""
        feedbacks = [
            {'rating': 2.8, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'intermediate'},
            {'rating': 2.5, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'beginner'},
            {'rating': 2.9, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.ADD_CLARITY in result['recommended_actions']

    def test_recommended_actions_needs_examples(self, feedback_service):
        """Test that NEEDS_EXAMPLES feedback triggers ADD_EXAMPLES action."""
        feedbacks = [
            {'rating': 3.5, 'feedback_type': FeedbackType.NEEDS_EXAMPLES, 'user_level': 'beginner'},
            {'rating': 3.5, 'feedback_type': FeedbackType.NEEDS_EXAMPLES, 'user_level': 'intermediate'},
            {'rating': 3.5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.ADD_EXAMPLES in result['recommended_actions']

    def test_recommended_actions_excellent_rating(self, feedback_service):
        """Test that excellent ratings trigger priority boost."""
        feedbacks = [
            {'rating': 5, 'feedback_type': FeedbackType.PERFECT, 'user_level': 'intermediate'},
            {'rating': 5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'},
            {'rating': 4.5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'beginner'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert RefinementAction.BOOST_PRIORITY in result['recommended_actions']

    def test_confidence_score_high_feedback_count(self, feedback_service):
        """Test that high feedback count increases confidence."""
        feedbacks = [{'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'} for _ in range(10)]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['confidence_score'] >= 0.7

    def test_confidence_score_consistent_ratings(self, feedback_service):
        """Test that consistent ratings increase confidence."""
        feedbacks = [
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'},
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'beginner'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['rating_standard_deviation'] == 0.0
        assert result['confidence_score'] > 0.5

    def test_priority_score_calculation(self, feedback_service):
        """Test priority score calculation."""
        # Low rating = high priority
        low_rating_feedbacks = [
            {'rating': 1.5, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'intermediate'},
            {'rating': 2, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': 'beginner'},
            {'rating': 1.5, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(low_rating_feedbacks)

        assert result['priority_score'] > 0.7

    def test_feedback_insights_generation(self, feedback_service):
        """Test that insights are generated from feedback analysis."""
        feedbacks = [
            {'rating': 4.5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'rating': 4.5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'rating': 4.8, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)
        insights = result['insights']

        assert len(insights) > 0
        assert any('helpful' in insight.lower() for insight in insights)


class TestRefineQuestionBasedOnFeedback:
    """Tests for question refinement."""

    def test_refine_question_decrease_difficulty(self, feedback_service, sample_question):
        """Test simplifying a question that's too difficult."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.DECREASE_DIFFICULTY],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert len(result['refinement_info']['actions_taken']) > 0
        assert 'Simplified' in result['refinement_info']['actions_taken'][0]

    def test_refine_question_increase_difficulty(self, feedback_service, sample_question):
        """Test increasing complexity of a question that's too easy."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.INCREASE_DIFFICULTY],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert any('complexity' in action.lower() for action in result['refinement_info']['actions_taken'])

    def test_refine_question_add_clarity(self, feedback_service, sample_question):
        """Test adding clarity to unclear questions."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.ADD_CLARITY],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert any('clarity' in action.lower() for action in result['refinement_info']['actions_taken'])
        assert len(result['help_text']) > len(sample_question['help_text'])

    def test_refine_question_add_examples(self, feedback_service, sample_question):
        """Test adding examples to questions."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.ADD_EXAMPLES],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert 'examples' in result  # Should have added examples
        assert any('examples' in action.lower() for action in result['refinement_info']['actions_taken'])

    def test_refine_question_improve_relevance(self, feedback_service, sample_question):
        """Test improving question relevance to chapter."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.IMPROVE_RELEVANCE],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert any('relevance' in action.lower() for action in result['refinement_info']['actions_taken'])

    def test_refine_question_multiple_actions(self, feedback_service, sample_question):
        """Test applying multiple refinement actions."""
        feedback_analysis = {
            'recommended_actions': [
                RefinementAction.ADD_CLARITY,
                RefinementAction.ADD_EXAMPLES
            ],
            'total_feedback_count': 8,
            'confidence_score': 0.9
        }

        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert 'refinement_info' in result
        assert len(result['refinement_info']['actions_taken']) == 2

    def test_refine_question_preserves_original(self, feedback_service, sample_question):
        """Test that refinement preserves original question text in metadata."""
        feedback_analysis = {
            'recommended_actions': [RefinementAction.ADD_CLARITY],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        original_text = sample_question['question_text']
        result = feedback_service.refine_question_based_on_feedback(
            sample_question,
            feedback_analysis
        )

        assert result['refinement_info']['original_version'] == original_text

    def test_simplify_question_with_complex_phrases(self, feedback_service):
        """Test simplification of questions with complex phrases."""
        question = {
            'question_text': 'What unconscious psychological patterns drive your character?',
            'difficulty': 'hard'
        }

        result = feedback_service._simplify_question(question)

        assert 'What motivates' in result['question_text']
        assert result['difficulty'] == 'medium'

    def test_increase_complexity_with_simple_phrases(self, feedback_service):
        """Test increasing complexity of simple questions."""
        question = {
            'question_text': 'What does your character want in this scene?',
            'difficulty': 'easy'
        }

        result = feedback_service._increase_question_complexity(question)

        assert 'motivations' in result['question_text'] or 'drives' in result['question_text']
        assert result['difficulty'] == 'medium'

    def test_add_clarity_enhances_help_text(self, feedback_service):
        """Test that adding clarity enhances help text."""
        question = {
            'question_text': 'What happens?',
            'help_text': 'Think about events.'
        }

        result = feedback_service._add_clarity_to_question(question)

        assert len(result['help_text']) >= len(question['help_text'])
        assert 'specific' in result['help_text'].lower()
        # Verify enhancement was added
        assert 'concrete examples' in result['help_text'].lower()

    def test_add_examples_by_question_type(self, feedback_service):
        """Test that examples are added based on question type."""
        character_question = {'question_type': 'character'}
        result = feedback_service._add_examples_to_question(character_question)
        assert 'examples' in result

        plot_question = {'question_type': 'plot'}
        result = feedback_service._add_examples_to_question(plot_question)
        assert 'examples' in result

        setting_question = {'question_type': 'setting'}
        result = feedback_service._add_examples_to_question(setting_question)
        assert 'examples' in result

    def test_improve_relevance_adds_chapter_context(self, feedback_service):
        """Test that improving relevance adds chapter-specific context."""
        question = {
            'question_text': 'What is the main conflict?',
            'help_text': 'Consider the story.'
        }

        result = feedback_service._improve_question_relevance(question)

        assert 'this chapter' in result['question_text'].lower() or 'this specific chapter' in result['question_text'].lower()
        assert len(result['help_text']) >= len(question['help_text'])
        # Verify chapter-specific enhancement was added
        assert 'focus specifically' in result['help_text'].lower() or 'chapter' in result['help_text'].lower()


class TestGenerateFeedbackSummaryReport:
    """Tests for feedback summary report generation."""

    def test_generate_summary_empty_analyses(self, feedback_service):
        """Test generating summary with no analyses."""
        result = feedback_service.generate_feedback_summary_report([])

        assert 'error' in result

    def test_generate_summary_single_analysis(self, feedback_service):
        """Test generating summary with single analysis."""
        analyses = [
            {
                'total_feedback_count': 5,
                'average_rating': 4.2,
                'recommended_actions': [RefinementAction.ADD_CLARITY]
            }
        ]

        result = feedback_service.generate_feedback_summary_report(analyses)

        assert result['summary']['total_questions_analyzed'] == 1
        assert result['summary']['total_feedback_received'] == 5
        assert result['summary']['overall_average_rating'] == 4.2

    def test_generate_summary_multiple_analyses(self, feedback_service):
        """Test generating summary with multiple analyses."""
        analyses = [
            {
                'total_feedback_count': 5,
                'average_rating': 4.5,
                'recommended_actions': [RefinementAction.BOOST_PRIORITY]
            },
            {
                'total_feedback_count': 8,
                'average_rating': 3.2,
                'recommended_actions': [RefinementAction.ADD_CLARITY, RefinementAction.DECREASE_DIFFICULTY]
            },
            {
                'total_feedback_count': 3,
                'average_rating': 2.0,
                'recommended_actions': [RefinementAction.MARK_FOR_REMOVAL]
            }
        ]

        result = feedback_service.generate_feedback_summary_report(analyses)

        assert result['summary']['total_questions_analyzed'] == 3
        assert result['summary']['total_feedback_received'] == 16
        assert result['summary']['overall_average_rating'] > 0
        assert len(result['top_issues']) > 0

    def test_generate_summary_quality_distribution(self, feedback_service):
        """Test quality distribution calculation in summary."""
        analyses = [
            {'total_feedback_count': 5, 'average_rating': 4.8, 'recommended_actions': []},
            {'total_feedback_count': 5, 'average_rating': 4.0, 'recommended_actions': []},
            {'total_feedback_count': 5, 'average_rating': 3.0, 'recommended_actions': []},
            {'total_feedback_count': 5, 'average_rating': 2.0, 'recommended_actions': []}
        ]

        result = feedback_service.generate_feedback_summary_report(analyses)
        distribution = result['quality_distribution']

        assert distribution['excellent'] == 1
        assert distribution['good'] == 1
        assert distribution['needs_improvement'] == 1
        assert distribution['poor'] == 1

    def test_generate_summary_recommendations(self, feedback_service):
        """Test that summary includes recommendations."""
        analyses = [
            {
                'total_feedback_count': 5,
                'average_rating': 2.5,
                'recommended_actions': [RefinementAction.ADD_CLARITY]
            },
            {
                'total_feedback_count': 5,
                'average_rating': 2.8,
                'recommended_actions': [RefinementAction.ADD_CLARITY]
            },
            {
                'total_feedback_count': 5,
                'average_rating': 2.3,
                'recommended_actions': [RefinementAction.ADD_CLARITY]
            }
        ]

        result = feedback_service.generate_feedback_summary_report(analyses)

        assert 'recommendations' in result
        assert len(result['recommendations']) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_feedback_without_rating(self, feedback_service):
        """Test processing feedback without a rating."""
        feedback_data = {
            'type': FeedbackType.HELPFUL,
            'comment': 'Great question!'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        assert result['rating'] is None
        assert result['comment'] == 'Great question!'

    def test_analyze_feedback_without_ratings(self, feedback_service):
        """Test analyzing feedback when no ratings are provided."""
        feedbacks = [
            {'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert result['average_rating'] is None
        assert result['total_feedback_count'] == 2

    def test_very_long_comment(self, feedback_service):
        """Test handling very long comments."""
        feedback_data = {
            'rating': 4,
            'comment': 'A' * 10000  # Very long comment
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        assert len(result['comment']) == 10000

    def test_invalid_rating_values(self, feedback_service):
        """Test handling invalid rating values."""
        # Rating outside 1-5 range
        feedback_data = {
            'rating': 10,
            'comment': 'Best question ever!'
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        # Should still process but rating is stored as-is (validation should happen at API layer)
        assert result['rating'] == 10

    def test_missing_context_fields(self, feedback_service):
        """Test handling missing optional context fields."""
        feedback_data = {
            'rating': 4
            # No type, comment, or context
        }

        result = feedback_service.process_question_feedback('q-123', feedback_data)

        assert result['comment'] == ''
        assert result['context'] == {}

    def test_unknown_user_level_in_analysis(self, feedback_service):
        """Test handling feedback with unknown user levels."""
        feedbacks = [
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL},  # No user_level
            {'rating': 3, 'feedback_type': FeedbackType.UNCLEAR, 'user_level': None}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        assert 'unknown' in result['level_analysis'] or None in result['level_analysis']

    def test_empty_question_text_refinement(self, feedback_service):
        """Test refining question with empty text."""
        question = {
            'question_text': '',
            'question_type': 'character'
        }
        feedback_analysis = {
            'recommended_actions': [RefinementAction.ADD_CLARITY],
            'total_feedback_count': 5,
            'confidence_score': 0.8
        }

        result = feedback_service.refine_question_based_on_feedback(
            question,
            feedback_analysis
        )

        # Should handle gracefully
        assert 'refinement_info' in result


class TestSingletonInstance:
    """Tests for singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available."""
        from app.services.question_feedback_service import question_feedback_service

        assert question_feedback_service is not None
        assert isinstance(question_feedback_service, QuestionFeedbackService)

    def test_singleton_has_correct_configuration(self):
        """Test that singleton instance has correct configuration."""
        from app.services.question_feedback_service import question_feedback_service

        assert hasattr(question_feedback_service, 'feedback_weights')
        assert hasattr(question_feedback_service, 'refinement_thresholds')
        assert question_feedback_service.refinement_thresholds['min_feedback_count'] == 3


class TestEdgeCasesForFullCoverage:
    """Additional tests to achieve 100% coverage."""

    def test_recommended_actions_irrelevant_feedback(self, feedback_service):
        """Test that IRRELEVANT feedback triggers IMPROVE_RELEVANCE action when rating is in needs_attention range."""
        feedbacks = [
            {'rating': 2.8, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'intermediate'},
            {'rating': 2.5, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'beginner'},
            {'rating': 2.9, 'feedback_type': FeedbackType.IRRELEVANT, 'user_level': 'advanced'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        # This should trigger IMPROVE_RELEVANCE action (line 304)
        assert RefinementAction.IMPROVE_RELEVANCE in result['recommended_actions']

    def test_confidence_score_with_feedback_count_five(self, feedback_service):
        """Test confidence calculation with exactly 5 feedback items."""
        feedbacks = [
            {'rating': 4, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'}
            for _ in range(5)
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        # This should hit the feedback_count >= 5 branch (line 337)
        assert result['confidence_score'] >= 0.5

    def test_confidence_score_with_rating_std_medium_high(self, feedback_service):
        """Test confidence calculation with rating standard deviation between 1.0 and 1.5."""
        feedbacks = [
            {'rating': 2.0, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'intermediate'},
            {'rating': 4.0, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'advanced'},
            {'rating': 4.5, 'feedback_type': FeedbackType.HELPFUL, 'user_level': 'beginner'}
        ]

        result = feedback_service.analyze_question_feedback_trends(feedbacks)

        # Rating std should be between 1.0 and 1.5, hitting line 349
        rating_std = result['rating_standard_deviation']
        assert 1.0 < rating_std <= 1.5
        assert result['confidence_score'] > 0

    def test_overall_recommendations_improve_relevance_threshold(self, feedback_service):
        """Test that recommendations include relevance improvement when 20%+ questions need it."""
        # Create 10 analyses where 3+ need relevance improvement (>20%)
        analyses = [
            {
                'total_feedback_count': 5,
                'average_rating': 2.8,
                'recommended_actions': [RefinementAction.IMPROVE_RELEVANCE]
            },
            {
                'total_feedback_count': 5,
                'average_rating': 2.5,
                'recommended_actions': [RefinementAction.IMPROVE_RELEVANCE]
            },
            {
                'total_feedback_count': 5,
                'average_rating': 2.7,
                'recommended_actions': [RefinementAction.IMPROVE_RELEVANCE]
            },
        ] + [
            {
                'total_feedback_count': 5,
                'average_rating': 4.0,
                'recommended_actions': [RefinementAction.NO_ACTION]
            }
            for _ in range(7)
        ]

        result = feedback_service.generate_feedback_summary_report(analyses)

        # This should hit line 593
        assert any('relevance' in rec.lower() for rec in result['recommendations'])
