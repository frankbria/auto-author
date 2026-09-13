"""GLM Review runs exactly once, when a PR is ready for people to read (#607).

Two defaults were wrong in opposite directions, and fixing either alone makes the
other worse:

- `opened` fires for **drafts**, so a sizeable draft consumed a 35-minute /
  60-turn review of work explicitly not ready.
- `ready_for_review` was **not** in the trigger list, so a PR opened as a draft
  and later marked ready was *never* reviewed unless something else happened to
  push to it — silently, with no red check to notice.

Skipping drafts without adding `ready_for_review` would have turned the second
from "wasteful" into "never reviewed at all". They are one decision.

This guard is here because the failure is invisible: a workflow that does not run
leaves no mark on the PR, so a regression in either half shows up as reviews
quietly not happening rather than as anything failing. The `if:` expression is
also long enough that a future edit could drop a clause without anyone noticing.

Run: uvx --with pytest --with pyyaml pytest scripts/test_glm_review_draft_policy.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "glm-review.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    parsed = yaml.safe_load(WORKFLOW.read_text(encoding="utf8"))
    # PyYAML resolves the bare key `on:` to the boolean True (YAML 1.1), which is
    # a trap worth naming rather than working around silently.
    assert True in parsed or "on" in parsed, "no trigger block in the workflow"
    return parsed


@pytest.fixture(scope="module")
def triggers(workflow: dict) -> dict:
    return (workflow.get(True) or workflow["on"])["pull_request"]


@pytest.fixture(scope="module")
def condition(workflow: dict) -> str:
    return workflow["jobs"]["review"]["if"]


def test_the_workflow_parses_and_has_the_job_this_guard_is_about(
    triggers: dict, condition: str
) -> None:
    """Vacuity guard: every assertion below reads one of these two."""
    assert triggers.get("types"), "no `types:` on the pull_request trigger"
    assert "github.event.pull_request" in condition


def test_a_pr_marked_ready_is_reviewed(triggers: dict) -> None:
    """Without this, a draft-first PR is never reviewed, and nothing says so."""
    assert "ready_for_review" in triggers["types"], (
        "`ready_for_review` is missing, so a PR opened as a draft and later marked "
        "ready gets no review at all unless something else pushes to it (#607)"
    )


def test_a_draft_is_not_reviewed(condition: str) -> None:
    """A 35-minute review of work explicitly not ready."""
    normalised = " ".join(condition.split())
    assert "!github.event.pull_request.draft" in normalised, (
        "the draft guard is gone, so opening or pushing to a draft burns a full "
        "review of work that is not ready (#607)"
    )


def test_the_guards_that_predate_this_one_are_still_there(condition: str) -> None:
    """#270's fork guard and #605's bot guards share this expression.

    They are unrelated to #607 and easy to drop while editing a long `if:`; each
    exists because something went wrong once.
    """
    normalised = " ".join(condition.split())
    for clause, why in [
        (
            "github.event.pull_request.head.repo.full_name == github.repository",
            "fork PRs must never reach a run that binds ZHIPU_API_KEY (#270)",
        ),
        (
            "github.event.pull_request.user.type == 'User'",
            "bot-authored PRs went red without ever being reviewed (#519)",
        ),
        (
            "github.event.sender.type == 'User'",
            "claude-code-action keys off the pusher, not the author (#605)",
        ),
    ]:
        assert clause in normalised, f"missing clause: {why}"


def test_opened_and_synchronize_are_still_triggers(triggers: dict) -> None:
    """The draft fix must not narrow the ordinary path."""
    assert "opened" in triggers["types"]
    assert "synchronize" in triggers["types"]
