"""Two PRs appending to the changelog on the same day do not conflict (#661).

`docs/CHANGELOG.md` groups entries under `### YYYY-MM-DD`, newest-first within
the day, so every PR inserts at the same line. With more than one PR open, every
merge makes every other open PR conflict on this file — eight times in a single
session, all positional, all mechanical, none semantic.

`.gitattributes` sets `merge=union` for that file: git's built-in "keep both
sides" driver, which produces exactly what a human resolution produces here.

This test is not a check that a line exists in a config file — grep would do that
and would prove nothing about whether git honours it. It builds a throwaway repo,
copies **this repo's** `.gitattributes` into it, and reproduces the case: two
branches each inserting an entry under the same date heading. Delete the
`docs/CHANGELOG.md merge=union` line and this test fails with a real conflict.

The companion guard is `test_changelog_headings.py`, which covers the *other*
half — a resolution that appends a second `### <date>` section instead of merging
into the first. Union merging cannot produce that, but a hand resolution can, and
one reached `main` that way before either guard existed.

Run: uvx --with pytest pytest scripts/test_changelog_merge.py -q
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

HEADING = "### 2026-09-12"
BASE = f"# Changelog\n\n{HEADING}\n\n- base entry\n"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )


def insert_entry(repo: Path, label: str) -> None:
    """Insert an entry the way every PR does: newest-first, under the heading."""
    changelog = repo / "docs" / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf8")
    assert text.count(f"{HEADING}\n\n") == 1
    changelog.write_text(
        text.replace(f"{HEADING}\n\n", f"{HEADING}\n\n- {label} entry\n\n", 1),
        encoding="utf8",
    )


def build_two_prs(tmp_path: Path, *, with_driver: bool) -> Path:
    """A repo with `main` and `feature` each adding an entry under one heading.

    `with_driver` copies this repo's real `.gitattributes` in, so the test cannot
    pass against a stand-in — and its absence is what the anti-vacuity case needs.
    It is written on the **base** commit, because git reads merge attributes from
    the tree being rebased onto, not from the commits being replayed.
    """
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "guard@example.invalid")
    git(repo, "config", "user.name", "guard")

    if with_driver:
        shutil.copy(GITATTRIBUTES, repo / ".gitattributes")
    (repo / "docs" / "CHANGELOG.md").write_text(BASE, encoding="utf8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    git(repo, "checkout", "-qb", "feature")
    insert_entry(repo, "FEATURE")
    git(repo, "commit", "-qam", "feature")

    git(repo, "checkout", "-q", "main")
    insert_entry(repo, "MAIN")
    git(repo, "commit", "-qam", "main")

    git(repo, "checkout", "-q", "feature")
    return repo


def test_the_fixture_reproduces_the_case_this_guard_is_about(tmp_path: Path) -> None:
    """Anti-vacuity: with no merge driver, the same fixture must conflict.

    A fixture that cannot conflict would make the assertion below pass whatever
    `.gitattributes` says — which is the failure mode #613 was about.
    """
    repo = build_two_prs(tmp_path, with_driver=False)
    result = git(repo, "rebase", "main")

    assert result.returncode != 0, "the fixture no longer reproduces a conflict"
    assert "CONFLICT" in result.stdout + result.stderr
    assert "<<<<<<<" in (repo / "docs" / "CHANGELOG.md").read_text(encoding="utf8")


def test_two_prs_appending_on_the_same_day_rebase_without_conflict(
    tmp_path: Path,
) -> None:
    repo = build_two_prs(tmp_path, with_driver=True)
    result = git(repo, "rebase", "main")

    assert result.returncode == 0, (
        "rebasing one changelog entry onto another conflicted. Is "
        "`docs/CHANGELOG.md merge=union` still in .gitattributes? (#661)\n"
        f"{result.stdout}\n{result.stderr}"
    )

    merged = (repo / "docs" / "CHANGELOG.md").read_text(encoding="utf8")
    assert "<<<<<<<" not in merged
    # Both entries survive, under the one heading — the point of the driver.
    assert "- MAIN entry" in merged
    assert "- FEATURE entry" in merged
    assert merged.count(HEADING) == 1
