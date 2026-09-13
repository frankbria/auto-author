"""Each date appears once in the changelog (#661).

`docs/CHANGELOG.md` groups entries under `### YYYY-MM-DD`, newest-first within
the day, so every PR inserts at the same line. With more than one PR open, every
merge makes every other open PR conflict on this file — six times across eight
PRs on 2026-09-12 alone.

The conflicts are positional, never semantic, and resolving them is mechanical.
The part that is *not* harmless is the silent failure: resolving one badly
appends a second `### <date>` section instead of merging into the first, and
nothing notices. That happened during #522 and reached `main`.

This guard covers that half. It does not address the conflicts themselves —
that is a convention choice (append-within-day, or one file per entry assembled
at release) recorded in #661 with the trade-offs, and deliberately left to a
human because it changes how everyone writes entries.

The tree carries 13 dates with a duplicated heading, 25 extra headings in all,
predating this guard. They are ledgered rather than merged: reordering historical
entries is a large, hard-to-review diff over text whose within-day order may
carry meaning, and the value here is stopping the *next* one. The ledger only
shrinks.

Run: uvx --with pytest pytest scripts/test_changelog_headings.py -q
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "docs" / "CHANGELOG.md"

DATE_HEADING = re.compile(r"^### (\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)

# Dates whose headings were already duplicated when this guard landed. Shrink by
# merging the sections; never extend to silence a new one.
KNOWN_DUPLICATES = {
    "2026-06-26",
    "2026-06-29",
    "2026-06-30",
    "2026-07-04",
    "2026-07-05",
    "2026-07-09",
    "2026-07-12",
    "2026-07-13",
    "2026-07-14",
    "2026-07-18",
    "2026-08-26",
}


def heading_counts() -> Counter[str]:
    return Counter(DATE_HEADING.findall(CHANGELOG.read_text(encoding="utf8")))


def test_the_changelog_is_findable_and_has_headings() -> None:
    """Vacuity guard: an empty match set makes every assertion below pass."""
    assert CHANGELOG.exists(), f"{CHANGELOG} not found"
    counts = heading_counts()
    assert len(counts) > 40, f"only {len(counts)} date headings — the pattern is probably broken"


def test_the_pattern_recognises_a_heading_and_rejects_near_misses() -> None:
    """Pins the regex to fixtures, so a typo cannot quietly green this file."""
    assert DATE_HEADING.findall("### 2026-09-12\n") == ["2026-09-12"]
    assert DATE_HEADING.findall("### 2026-09-12\n### 2026-09-12\n") == [
        "2026-09-12",
        "2026-09-12",
    ]
    # Not a date heading: wrong level, trailing text, or inline.
    assert DATE_HEADING.findall("## 2026-09-12\n") == []
    assert DATE_HEADING.findall("### 2026-09-12 hotfix\n") == []
    assert DATE_HEADING.findall("see ### 2026-09-12\n") == []


def test_no_new_date_has_more_than_one_heading() -> None:
    """A second `### <date>` is a botched conflict resolution, not a choice.

    Every entry for a day belongs in one section. Two sections for one date is
    what a bad merge leaves behind, and it is invisible in review because both
    halves look correct on their own.
    """
    duplicated = {date for date, n in heading_counts().items() if n > 1}
    unledgered = sorted(duplicated - KNOWN_DUPLICATES)

    assert unledgered == [], (
        f"{unledgered} each have more than one `### <date>` heading. "
        "Merge the sections rather than adding a second one — this is what a "
        "mis-resolved CHANGELOG conflict looks like (#661)."
    )


def test_the_ledger_holds_only_dates_that_are_still_duplicated() -> None:
    """Stale rows pre-authorise a duplicate rather than recording one."""
    duplicated = {date for date, n in heading_counts().items() if n > 1}
    stale = sorted(KNOWN_DUPLICATES - duplicated)

    assert stale == [], (
        f"{stale} are no longer duplicated — delete them from KNOWN_DUPLICATES. "
        "Leaving a fixed date ledgered means the next duplicate on that date passes."
    )
