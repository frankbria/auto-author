"""Structured-output parsers against a real non-OpenAI model (#917).

Fixtures are completions from nemotron-3-nano:30b (NVIDIA, via
Ollama's OpenAI-compatible endpoint), produced by the app's own prompts for a
business book, verbatim except for trailing whitespace (pre-commit trims it).
Open models format differently from gpt-4: markdown bold around
numbered questions, list-style suggestions under a bare ``SUGGESTIONS:``.
"""
from pathlib import Path

import pytest

from app.services.ai_service import AIService

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ai_provider_outputs" / "nemotron-3-nano-30b"


def _fixture(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


@pytest.fixture
def svc():
    return AIService()


def test_readiness_analysis(svc):
    result = svc._parse_analysis_response(_fixture("analysis"), "summary text")

    assert result["is_ready_for_toc"] is True
    assert result["confidence_score"] == 0.96
    assert result["analysis"].startswith("The summary clearly states")
    assert len(result["suggestions"]) == 3
    assert result["suggestions"][0].startswith("Mention any recurring sections")


def test_clarifying_questions(svc):
    questions = svc._parse_questions_response(_fixture("clarifying_questions"))

    assert len(questions) == 4
    assert questions[0].startswith("How should the chapters be sequenced")
    for q in questions:
        assert q.endswith("?")
        assert "*" not in q
        assert not q[0].isdigit()


def test_toc_json(svc):
    result = svc._parse_toc_response(_fixture("toc"))

    assert result["chapters_count"] == 8
    assert result["has_subchapters"] is True
    assert result["toc"]["chapters"][0]["title"] == "Transitioning from Engineer to Manager"


def test_chapter_questions_json(svc):
    questions = svc._parse_chapter_questions_response(_fixture("chapter_questions"))

    assert len(questions) == 5
    for q in questions:
        assert q["question_text"].endswith("?")
        assert q["question_type"] and q["difficulty"] and q["help_text"]
