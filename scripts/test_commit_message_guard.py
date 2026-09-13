"""A commit message that says it does not close an issue must not close it.

GitHub's linked-issue parser matches `close|fixes|resolved #<n>` anywhere in a
commit message or PR body and does not parse negation. A disclaimer written to
*prevent* a closure therefore causes one. That is not hypothetical here: #676's
merge commit carried

    Does not close #584 — its condition is the rules back at `error`.

and closed #584, with 17 violations outstanding and all three rules still at
`warn`. The sentence written to stop it was the trigger.

`scripts/check-commit-message.sh` runs as a `commit-msg` hook. This pins its
behaviour on both sides: the shapes it must reject, and the ordinary messages it
must leave alone — a guard that rejects everything is as useless as one that
rejects nothing, and only the second half of that is obvious.

Limitation, stated rather than hidden: a PR **body** can close an issue too, and
no local hook sees that. This covers commit messages only.

Run: uvx --with pytest pytest scripts/test_commit_message_guard.py -q
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent / "check-commit-message.sh"


def check(message: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(message, encoding="utf8")
    return subprocess.run(
        [str(GUARD), str(path)], capture_output=True, text=True, check=False
    )


REJECTED = [
    # Wrapped between the negation and the keyword. Commit bodies wrap at ~72
    # columns and GitHub does not care about the wrap, so a line-based check
    # reads this as safe and the issue closes anyway. Found by the pre-PR
    # reviewer and reproduced against the previous version before fixing.
    "fix: x\n\nThis does not\nclose #123 yet.\n",
    "fix: y\n\nThe change here does not\n   resolve #7; upstream owns it.\n",
    # A `#`-prefixed line. `git commit -m` uses --cleanup=whitespace and keeps
    # comment lines, so skipping them is how the first cut of this guard passed
    # the very message that motivated it: a body opening "#676's merge commit
    # carried \"Does not close #584\"...".
    'fix: a\n\n#676\'s merge commit carried "Does not close #584 — its condition".\n',

    # The real one, verbatim from #676's merge commit.
    "feat(ci): ledger the backlog\n\nDoes not close #584 — its condition is the rules back at `error`.\n",
    "fix: something\n\nThis doesn't fix #12, it only documents it.\n",
    "chore: tidy\n\nWill not resolve #7 until upstream ships.\n",
    "docs: notes\n\nDoes NOT Close #1.\n",
    "fix: x\n\nThis does not fixes #99 — wording is deliberate.\n",
    # A colon between keyword and number is still a link on GitHub.
    "chore: y\n\nDoes not close: #42\n",
]

ACCEPTED = [
    # Deliberate closures must still be possible.
    "fix(lint): the last one\n\nCloses #584.\n",
    "fix: a\n\nFixes #12\n",
    # References without a keyword — the documented way to mention an issue.
    "feat(ci): ledger the backlog\n\n#584's close condition is the rules back at `error`.\n",
    "fix(lint): partial\n\nPartial progress on #584; 18 -> 17.\n",
    "fix(chapters): tabs (#672)\n\nPer #584, this is not a state-derivation problem.\n",
    # Negation with no issue number attached is ordinary prose.
    "fix: modal\n\nThis does not close the dialog when Escape is pressed.\n",
]


@pytest.mark.parametrize("message", REJECTED)
def test_a_negated_closing_keyword_is_rejected(message: str, tmp_path: Path) -> None:
    result = check(message, tmp_path)
    assert result.returncode != 0, f"guard accepted a message that would close an issue:\n{message}"
    assert "#" in result.stderr


@pytest.mark.parametrize("message", ACCEPTED)
def test_ordinary_messages_are_left_alone(message: str, tmp_path: Path) -> None:
    result = check(message, tmp_path)
    assert result.returncode == 0, (
        f"guard rejected an ordinary message:\n{message}\n{result.stderr}"
    )


def test_the_guard_is_executable_and_wired_into_pre_commit() -> None:
    """A hook nobody runs is a file. Check both halves of "installed".

    Parsed, not grepped. The first cut asserted `"commit-msg" in config`, which
    passes on `default_install_hook_types: [pre-commit, commit-msg]` several
    lines away — so retagging this hook to `stages: [manual]` left it green. It
    was caught by mutating the very thing it claimed to check, which is the only
    reason it is written this way.
    """
    import os

    import yaml

    assert os.access(GUARD, os.X_OK), f"{GUARD} is not executable"

    config = yaml.safe_load(
        (GUARD.parent.parent / ".pre-commit-config.yaml").read_text(encoding="utf8")
    )
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
        if hook.get("id") == "check-commit-message"
    ]
    assert len(hooks) == 1, "check-commit-message is not declared exactly once"
    assert hooks[0].get("stages") == ["commit-msg"], (
        f"hook runs at {hooks[0].get('stages')!r}; it must run at the commit-msg "
        "stage, where the message exists"
    )
    assert "commit-msg" in config["default_install_hook_types"], (
        "`pre-commit install` will not wire the commit-msg hook type"
    )
