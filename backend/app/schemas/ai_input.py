"""Request bodies for the routes whose text ends up in a model prompt (#800).

The AI quota counts calls, not tokens, so the size of one call is bounded here:
a length cap on each field, a count cap on each list, and a total for a list of
answers, because fifty answers at the per-answer cap would still be 500,000
characters. Anything over is answered 422 before a model call is attempted.
"""

from typing import Annotated, Any, List, Optional

from pydantic import AfterValidator, BaseModel, Field

MAX_QA_PAIRS = 50  # as many questions as one chapter can be asked for
MAX_QUESTION_CHARS = 1000  # the cap a generated question already has
MAX_ANSWER_CHARS = 10_000
MAX_QA_TOTAL_CHARS = 100_000
# The transform and enhance calls allow 4,000 completion tokens, so a longer
# text could not come back whole anyway.
MAX_AI_CONTENT_CHARS = 20_000
MAX_WRITING_STYLE_CHARS = 100


class QuestionAnswer(BaseModel):
    question: str = Field(..., max_length=MAX_QUESTION_CHARS)
    answer: str = Field(..., max_length=MAX_ANSWER_CHARS)


def _within_total(pairs: List[QuestionAnswer]) -> List[QuestionAnswer]:
    total = sum(len(pair.question) + len(pair.answer) for pair in pairs)
    if total > MAX_QA_TOTAL_CHARS:
        raise ValueError(
            f"Questions and answers together are {total} characters; "
            f"the limit is {MAX_QA_TOTAL_CHARS}"
        )
    return pairs


QuestionAnswers = Annotated[
    List[QuestionAnswer], Field(max_length=MAX_QA_PAIRS), AfterValidator(_within_total)
]
AIContent = Annotated[str, Field(max_length=MAX_AI_CONTENT_CHARS)]


class SaveQuestionResponsesRequest(BaseModel):
    responses: QuestionAnswers = []


class GenerateTocRequest(BaseModel):
    question_responses: QuestionAnswers = []


class GenerateDraftRequest(BaseModel):
    question_responses: QuestionAnswers = []
    writing_style: Optional[str] = Field(None, max_length=MAX_WRITING_STYLE_CHARS)
    target_length: Any = 2000  # the route falls back to 2000 for anything unusable


class TransformStyleRequest(BaseModel):
    content: AIContent = ""
    target_style: str = ""


class EnhanceTextRequest(BaseModel):
    content: AIContent = ""
    enhancement_type: str = ""


class EnhanceTranscriptionRequest(BaseModel):
    content: AIContent = ""
