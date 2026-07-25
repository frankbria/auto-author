"""Real-Mongo tests for #336 — the chapter-question ``status`` filter must be
resolved BEFORE pagination.

``get_questions_for_chapter`` used to page the ``questions`` collection with the
``status`` filter absent from the query, then drop non-matching rows from the
already-sliced page in Python. Because ``skip``/``limit`` walked **raw**
documents, a client paging a filtered list silently skipped matching questions
it could never reach, pages came back short (or empty), and the three count
fields disagreed: ``total`` was the post-filter length of one page while
``pages``/``has_more`` derived from a count that ignored ``status`` entirely.

The fixture below deliberately **interleaves** statuses so that no page of the
raw ordering is homogeneous — that interleaving is what makes the old
filter-after-paginate behavior observable.
"""

import pytest
from bson import ObjectId

from app.db.base import get_collection
from app.db.questions import get_questions_for_chapter

pytestmark = pytest.mark.asyncio

BOOK = "book-336"
CH = "ch-336"
USER = "user-336"

# order -> response status ("none" = no response document at all).
# Interleaved on purpose: completed questions sit at orders 1,3,5,7 so any
# raw-ordered page of size 2 mixes matching and non-matching rows.
SEED = {
    1: "completed",
    2: "none",
    3: "completed",
    4: "draft",
    5: "completed",
    6: "none",
    7: "completed",
}
COMPLETED_ORDERS = [1, 3, 5, 7]
NOT_ANSWERED_ORDERS = [2, 6]
DRAFT_ORDERS = [4]


async def _seed_chapter() -> dict:
    """Seed the 7-question chapter. Returns {order: question_id}."""
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")

    ids_by_order = {}
    for order, status in sorted(SEED.items()):
        qid = ObjectId()
        await questions.insert_one({
            "_id": qid,
            "book_id": BOOK,
            "chapter_id": CH,
            "user_id": USER,
            "question_text": f"Question number {order} for the chapter?",
            "question_type": "plot",
            "difficulty": "easy",
            "category": "general",
            "order": order,
            "metadata": {"suggested_response_length": "short"},
        })
        ids_by_order[order] = str(qid)

        if status != "none":
            await responses.insert_one({
                "question_id": str(qid),
                "user_id": USER,
                "response_text": "an answer",
                "status": status,
            })

    return ids_by_order


async def _collect_pages(status: str, limit: int) -> tuple[list, list]:
    """Page through the filtered list the way a real client does — following
    ``pages`` — and return (all question ids seen, per-page reported totals)."""
    seen, totals = [], []
    first = await get_questions_for_chapter(
        BOOK, CH, USER, status=status, page=1, limit=limit
    )
    totals.append(first.total)
    seen.extend(q.id for q in first.questions)

    for page in range(2, first.pages + 1):
        result = await get_questions_for_chapter(
            BOOK, CH, USER, status=status, page=page, limit=limit
        )
        totals.append(result.total)
        seen.extend(q.id for q in result.questions)

    return seen, totals


# --- The acceptance-criteria test: >1 page + a status filter ----------------


async def test_completed_filter_across_multiple_pages_is_complete_and_disjoint(
    motor_reinit_db,
):
    """4 completed questions at limit=2 => exactly 2 full pages covering all 4.

    Under filter-after-paginate the same walk yields only the completed rows that
    happened to land in the first pages of the RAW ordering — orders 5 and 7 are
    unreachable — and every page reports ``total`` as its own post-filter length.
    """
    ids = await _seed_chapter()
    expected = [ids[o] for o in COMPLETED_ORDERS]

    seen, totals = await _collect_pages(status="completed", limit=2)

    # Complete: every completed question is reachable by paging.
    assert sorted(seen) == sorted(expected)
    # Non-overlapping: no question is served twice.
    assert len(seen) == len(set(seen))
    # Accurate total: the size of the FILTERED set, identical on every page.
    assert totals == [4, 4]


async def test_completed_filter_page_shape_and_ordering(motor_reinit_db):
    ids = await _seed_chapter()

    page1 = await get_questions_for_chapter(
        BOOK, CH, USER, status="completed", page=1, limit=2
    )
    page2 = await get_questions_for_chapter(
        BOOK, CH, USER, status="completed", page=2, limit=2
    )

    assert page1.pages == 2 and page1.has_more is True
    assert page2.pages == 2 and page2.has_more is False
    # Full pages — the old code returned 1 of 2 rows here.
    assert len(page1.questions) == 2 and len(page2.questions) == 2
    # Sorted by ``order`` across the page boundary.
    assert [q.order for q in page1.questions] == [1, 3]
    assert [q.order for q in page2.questions] == [5, 7]
    both_pages = page1.questions + page2.questions
    assert all(q.response_status == "completed" for q in both_pages)
    assert [q.id for q in page1.questions] == [ids[1], ids[3]]


async def test_not_answered_filter_never_yields_an_empty_page(motor_reinit_db):
    """Questions 2 and 6 are unanswered. At limit=1 the old code's first page
    paged raw order 1 (completed), filtered it away, and returned an EMPTY page
    while claiming 7 pages of results."""
    ids = await _seed_chapter()
    expected = [ids[o] for o in NOT_ANSWERED_ORDERS]

    seen, totals = await _collect_pages(status="not_answered", limit=1)

    assert sorted(seen) == sorted(expected)
    assert len(seen) == len(set(seen))
    assert totals == [2, 2]


async def test_draft_filter_returns_only_the_draft_question(motor_reinit_db):
    ids = await _seed_chapter()

    result = await get_questions_for_chapter(
        BOOK, CH, USER, status="draft", page=1, limit=2
    )

    assert [q.id for q in result.questions] == [ids[DRAFT_ORDERS[0]]]
    assert result.total == 1
    assert result.pages == 1
    assert result.has_more is False


async def test_status_filter_is_scoped_to_the_requesting_user(motor_reinit_db):
    """Another user's response on the same question must not make it match."""
    ids = await _seed_chapter()
    responses = await get_collection("question_responses")
    # Order 2 is unanswered for USER; give a different user a completed response.
    await responses.insert_one({
        "question_id": ids[2],
        "user_id": "someone-else",
        "response_text": "not mine",
        "status": "completed",
    })

    completed = await get_questions_for_chapter(
        BOOK, CH, USER, status="completed", page=1, limit=50
    )
    not_answered = await get_questions_for_chapter(
        BOOK, CH, USER, status="not_answered", page=1, limit=50
    )

    assert ids[2] not in [q.id for q in completed.questions]
    assert completed.total == 4
    assert ids[2] in [q.id for q in not_answered.questions]


# --- Regression pins on the unfiltered path --------------------------------


async def test_unfiltered_total_is_the_collection_count_not_the_page_length(
    motor_reinit_db,
):
    """``total`` must describe the result set, not the slice. The old code
    returned ``len(page)``, so a 7-question chapter at limit=3 reported
    ``total=3`` alongside ``pages=3`` — two numbers that cannot both be right."""
    await _seed_chapter()

    result = await get_questions_for_chapter(BOOK, CH, USER, page=1, limit=3)

    assert len(result.questions) == 3
    assert result.total == 7
    assert result.pages == 3
    assert result.has_more is True


async def test_unfiltered_paging_still_covers_every_question(motor_reinit_db):
    ids = await _seed_chapter()

    seen, _ = await _collect_pages(status=None, limit=3)

    assert sorted(seen) == sorted(ids.values())
    assert len(seen) == len(set(seen))


async def test_category_filter_composes_with_status(motor_reinit_db):
    """The status id-set must narrow the SAME query the other filters build on,
    not replace it."""
    ids = await _seed_chapter()
    questions = await get_collection("questions")
    await questions.update_one(
        {"_id": ObjectId(ids[1])}, {"$set": {"category": "character"}}
    )

    result = await get_questions_for_chapter(
        BOOK, CH, USER, status="completed", category="character", page=1, limit=50
    )

    assert [q.id for q in result.questions] == [ids[1]]
    assert result.total == 1


async def test_unknown_status_value_is_ignored_as_before(motor_reinit_db):
    """Characterization pin, not a fix: the endpoint does not validate ``status``,
    and an unrecognised value has always fallen through to an unfiltered result.
    Tightening that to a 422 is a separate breaking change (out of scope for
    #336); this pins the behavior so the id-set rewrite doesn't silently turn it
    into 'matches nothing'."""
    await _seed_chapter()

    result = await get_questions_for_chapter(
        BOOK, CH, USER, status="bogus", page=1, limit=50
    )

    assert len(result.questions) == 7
    assert result.total == 7
