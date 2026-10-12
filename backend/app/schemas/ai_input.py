"""Request bodies for the routes whose text ends up in a model prompt (#800).

The AI quota counts calls, not tokens, so the size of one call is bounded here:
a length cap on each field, a count cap on each list, and a total for a list of
answers, because a full list at the per-answer cap would still be a million
characters. Anything over is answered 422 before a model call is attempted.
"""

from typing import Annotated, Any, List, Optional

from pydantic import AfterValidator, BaseModel, Field

MAX_QA_PAIRS = 100  # as many answers as one batch save takes
MAX_QUESTION_CHARS = 1000  # the cap a generated question already has
MAX_ANSWER_CHARS = 10_000
MAX_QA_TOTAL_CHARS = 100_000
# A rewrite comes back about as long as it went in, and the long-output class
# allows 8,000 completion tokens by default. Measured with the gpt-4o tokenizer,
# 5,000 words of English prose as the editor stores it is 33,000 characters and
# 5,900 tokens; 35,000 leaves the rewrite a quarter more room than its source (#801).
MAX_AI_CONTENT_CHARS = 35_000
MAX_WRITING_STYLE_CHARS = 100

# Text the book already stores goes into prompts as well, and some of it was
# stored without a limit, so it is cut to these where a prompt is built.
MAX_CHAPTER_TITLE_CHARS = 500
MAX_CHAPTER_DESCRIPTION_CHARS = 2000
# The ceiling for one model call, whatever road its text came by. Above the
# largest prompt the caps allow (a full list of answers plus its instructions).
MAX_PROMPT_CHARS = 150_000


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
