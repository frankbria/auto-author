"""
Comprehensive tests for genre_question_templates.py service.

Tests cover:
- Template retrieval by genre
- Template customization with book metadata
- Template coverage validation
- Multi-genre support
- Variable substitution
- Fallback to default templates
- Edge cases (unknown genres, missing variables, empty templates)
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from app.services.genre_question_templates import (
    GenreQuestionTemplates,
    GenreType,
    genre_question_templates,
)


@pytest.fixture
def template_service():
    """Create a fresh GenreQuestionTemplates instance for each test."""
    return GenreQuestionTemplates()


class TestGetGenreQuestions:
    """Test suite for get_genre_questions method."""

    def test_fiction_genre_questions(self, template_service):
        """Test generating questions for fiction genre."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            chapter_title="The Beginning",
            count=4
        )

        assert len(questions) == 4
        assert all(q['genre'] == GenreType.FICTION for q in questions)
        assert all('question_text' in q for q in questions)
        assert all('question_type' in q for q in questions)
        assert all('difficulty' in q for q in questions)
        assert all('help_text' in q for q in questions)

    def test_non_fiction_genre_questions(self, template_service):
        """Test generating questions for non-fiction genre."""
        questions = template_service.get_genre_questions(
            genre="non_fiction",
            chapter_title="Introduction to AI",
            count=3
        )

        assert len(questions) == 3
        assert all(q['genre'] == GenreType.NON_FICTION for q in questions)
        # Should have concept, practical, or research questions
        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'concept', 'practical', 'research'})

    def test_technical_genre_questions(self, template_service):
        """Test generating questions for technical genre."""
        questions = template_service.get_genre_questions(
            genre="technical",
            chapter_title="API Design Patterns",
            count=6
        )

        assert len(questions) == 6
        assert all(q['genre'] == GenreType.TECHNICAL for q in questions)
        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'process', 'implementation', 'architecture'})

    def test_specific_question_types(self, template_service):
        """Test generating specific question types only."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            count=4,
            question_types=['character', 'plot']
        )

        assert len(questions) == 4
        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'character', 'plot'})

    def test_chapter_title_customization(self, template_service):
        """Test that chapter title is inserted into questions."""
        chapter_title = "The Great Escape"
        questions = template_service.get_genre_questions(
            genre="fiction",
            chapter_title=chapter_title,
            count=5
        )

        # At least some questions should reference the chapter title
        questions_with_title = [q for q in questions if chapter_title in q['question_text']]
        assert len(questions_with_title) > 0

    def test_question_diversity(self, template_service):
        """Test that questions cycle through different types."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            count=8
        )

        question_types = [q['question_type'] for q in questions]
        # Should have multiple different types
        unique_types = set(question_types)
        assert len(unique_types) >= 3  # At least 3 different types


class TestGenreNormalization:
    """Test suite for genre normalization."""

    def test_normalize_sci_fi_variations(self, template_service):
        """Test that sci-fi variations map correctly."""
        # Note: The service only has templates for certain genres
        # Science fiction is a GenreType enum but doesn't have templates, so it falls back to fiction
        variations = ['sci-fi', 'scifi', 'sf']

        for variant in variations:
            questions = template_service.get_genre_questions(genre=variant, count=1)
            # These should normalize to science_fiction value but fall back to fiction templates
            assert questions[0]['genre'] in [GenreType.SCIENCE_FICTION, GenreType.FICTION]

    def test_normalize_non_fiction_variations(self, template_service):
        """Test that non-fiction variations map correctly."""
        variations = ['non-fiction', 'nonfiction', 'non_fiction', 'Non Fiction']

        for variant in variations:
            questions = template_service.get_genre_questions(genre=variant, count=1)
            assert questions[0]['genre'] == GenreType.NON_FICTION

    def test_normalize_self_help_variations(self, template_service):
        """Test that self-help variations map correctly."""
        # Note: SELF_HELP is a GenreType enum but doesn't have templates, so it falls back to fiction
        variations = ['self-help', 'selfhelp', 'self_help']

        for variant in variations:
            questions = template_service.get_genre_questions(genre=variant, count=1)
            # These should normalize to self_help value but fall back to fiction templates
            assert questions[0]['genre'] in [GenreType.SELF_HELP, GenreType.FICTION]

    def test_normalize_technical_variations(self, template_service):
        """Test that technical variations map correctly."""
        variations = ['tech', 'technical', 'technical_writing']

        for variant in variations:
            questions = template_service.get_genre_questions(genre=variant, count=1)
            assert questions[0]['genre'] == GenreType.TECHNICAL

    def test_unknown_genre_fallback(self, template_service):
        """Test that unknown genres fall back to fiction."""
        questions = template_service.get_genre_questions(
            genre="completely_unknown_genre",
            count=2
        )

        assert len(questions) == 2
        assert all(q['genre'] == GenreType.FICTION for q in questions)


class TestTemplateCustomization:
    """Test suite for template customization."""

    def test_character_name_placeholder(self, template_service):
        """Test that {character_name} placeholder is replaced."""
        # Get a question that might have character_name placeholder
        questions = template_service.get_genre_questions(
            genre="fiction",
            question_types=['character'],
            count=5
        )

        # None should have the raw placeholder
        for q in questions:
            assert "{character_name}" not in q['question_text']
            # Should be replaced with "your protagonist" or similar

    def test_chapter_title_in_template(self, template_service):
        """Test chapter title insertion in templates."""
        customized = template_service._customize_template(
            template="What happens in this chapter?",
            chapter_title="The Final Battle",
            genre="fiction"
        )

        assert "The Final Battle" in customized
        assert 'this chapter ("The Final Battle")' in customized

    def test_empty_chapter_title(self, template_service):
        """Test customization with empty chapter title."""
        customized = template_service._customize_template(
            template="What happens in this chapter?",
            chapter_title="",
            genre="fiction"
        )

        # Should not modify the template
        assert customized == "What happens in this chapter?"


class TestDifficultyAssignment:
    """Test suite for difficulty level assignment."""

    def test_technical_implementation_is_hard(self, template_service):
        """Test that technical implementation questions are marked hard."""
        difficulty = template_service._get_default_difficulty(
            GenreType.TECHNICAL,
            'implementation'
        )
        assert difficulty == 'hard'

    def test_fiction_theme_is_hard(self, template_service):
        """Test that fiction theme questions are marked hard."""
        difficulty = template_service._get_default_difficulty(
            GenreType.FICTION,
            'theme'
        )
        assert difficulty == 'hard'

    def test_non_fiction_practical_is_easy(self, template_service):
        """Test that non-fiction practical questions are marked easy."""
        difficulty = template_service._get_default_difficulty(
            GenreType.NON_FICTION,
            'practical'
        )
        assert difficulty == 'easy'

    def test_unknown_type_defaults_to_medium(self, template_service):
        """Test that unknown question types default to medium difficulty."""
        difficulty = template_service._get_default_difficulty(
            GenreType.FICTION,
            'unknown_type'
        )
        assert difficulty == 'medium'


class TestHelpText:
    """Test suite for help text generation."""

    def test_fiction_character_help_text(self, template_service):
        """Test help text for fiction character questions."""
        help_text = template_service._get_help_text(
            GenreType.FICTION,
            'character'
        )

        assert len(help_text) > 0
        assert 'character' in help_text.lower() or 'motivation' in help_text.lower()

    def test_technical_process_help_text(self, template_service):
        """Test help text for technical process questions."""
        help_text = template_service._get_help_text(
            GenreType.TECHNICAL,
            'process'
        )

        assert len(help_text) > 0
        assert 'step' in help_text.lower() or 'process' in help_text.lower()

    def test_unknown_type_default_help_text(self, template_service):
        """Test default help text for unknown types."""
        help_text = template_service._get_help_text(
            GenreType.FICTION,
            'unknown_type'
        )

        assert len(help_text) > 0
        assert 'chapter' in help_text.lower()


class TestSupportedGenres:
    """Test suite for supported genres functionality."""

    def test_get_supported_genres(self, template_service):
        """Test retrieving list of supported genres."""
        genres = template_service.get_supported_genres()

        assert len(genres) > 0
        assert 'fiction' in genres
        assert 'non_fiction' in genres
        assert 'technical' in genres

    def test_get_question_types_for_genre(self, template_service):
        """Test retrieving question types for specific genres."""
        fiction_types = template_service.get_question_types_for_genre('fiction')
        assert 'character' in fiction_types
        assert 'plot' in fiction_types
        assert 'setting' in fiction_types
        assert 'theme' in fiction_types

        technical_types = template_service.get_question_types_for_genre('technical')
        assert 'process' in technical_types
        assert 'implementation' in technical_types
        assert 'architecture' in technical_types

    def test_get_question_types_for_unknown_genre(self, template_service):
        """Test question types for unknown genre falls back to fiction."""
        # Unknown genres are normalized to fiction, which has templates
        types = template_service.get_question_types_for_genre('unknown_genre')
        # Should fall back to fiction types
        assert len(types) > 0  # Fiction has character, plot, setting, theme


class TestGenreCoverageAnalysis:
    """Test suite for genre coverage analysis."""

    def test_analyze_complete_coverage(self, template_service):
        """Test analysis when all question types are covered."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            count=8  # Enough to cover all types
        )

        analysis = template_service.analyze_genre_coverage(questions)

        assert 'primary_genre' in analysis
        assert analysis['primary_genre'] == GenreType.FICTION
        assert 'total_questions' in analysis
        assert analysis['total_questions'] == len(questions)
        assert 'coverage_score' in analysis
        assert 'type_distribution' in analysis

    def test_analyze_partial_coverage(self, template_service):
        """Test analysis when only some types are covered."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            question_types=['character'],
            count=3
        )

        analysis = template_service.analyze_genre_coverage(questions)

        assert analysis['coverage_score'] < 1.0  # Not full coverage
        assert len(analysis['missing_types']) > 0

    def test_analyze_empty_questions(self, template_service):
        """Test analysis with no questions."""
        analysis = template_service.analyze_genre_coverage([])

        assert 'error' in analysis

    def test_recommendations_for_missing_types(self, template_service):
        """Test that recommendations are generated for missing types."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            question_types=['character'],
            count=2
        )

        analysis = template_service.analyze_genre_coverage(questions)

        assert 'recommendations' in analysis
        assert len(analysis['recommendations']) > 0


class TestMultiGenreSupport:
    """Test suite for multiple genres."""

    def test_fantasy_worldbuilding_questions(self, template_service):
        """Test fantasy-specific question types."""
        questions = template_service.get_genre_questions(
            genre="fantasy",
            count=6
        )

        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'worldbuilding', 'magic', 'mythology'})

    def test_mystery_investigation_questions(self, template_service):
        """Test mystery-specific question types."""
        questions = template_service.get_genre_questions(
            genre="mystery",
            count=6
        )

        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'investigation', 'suspects', 'revelation'})

    def test_business_strategy_questions(self, template_service):
        """Test business-specific question types."""
        questions = template_service.get_genre_questions(
            genre="business",
            count=6
        )

        question_types = {q['question_type'] for q in questions}
        assert question_types.issubset({'strategy', 'leadership', 'execution'})


class TestSingletonInstance:
    """Test suite for singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that the singleton instance is available."""
        assert genre_question_templates is not None
        assert isinstance(genre_question_templates, GenreQuestionTemplates)

    def test_singleton_has_templates(self):
        """Test that singleton is properly initialized."""
        assert len(genre_question_templates.templates) > 0
        assert GenreType.FICTION in genre_question_templates.templates
        assert GenreType.NON_FICTION in genre_question_templates.templates


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_zero_questions_requested(self, template_service):
        """Test requesting zero questions."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            count=0
        )

        assert questions == []

    def test_very_large_count(self, template_service):
        """Test requesting a very large number of questions."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            count=100
        )

        assert len(questions) == 100
        # Should still have diversity
        question_types = {q['question_type'] for q in questions}
        assert len(question_types) > 1

    def test_empty_question_types_list(self, template_service):
        """Test with empty question types list."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            question_types=[],
            count=3
        )

        # Should fall back to all available types
        assert len(questions) == 3

    def test_invalid_question_types(self, template_service):
        """Test with invalid question types."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            question_types=['invalid_type1', 'invalid_type2'],
            count=3
        )

        # Should fall back to all available types
        assert len(questions) == 3

    def test_special_characters_in_chapter_title(self, template_service):
        """Test handling special characters in chapter title."""
        questions = template_service.get_genre_questions(
            genre="fiction",
            chapter_title='Chapter "The End?" & More...',
            count=2
        )

        assert len(questions) == 2
        # Should not crash with special characters
