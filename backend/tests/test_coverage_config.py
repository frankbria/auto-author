"""What ``.coveragerc`` leaves out of the coverage count is what it means to (#841).

Its exclusion patterns are regular expressions searched for in each line. The
bare pattern ``pass`` was meant for a line that says only ``pass``, and it
matched every line with "pass" anywhere in it: "bypass" among them. A matching
``def`` line takes its whole body out of the count, so the validator that keeps
BYPASS_AUTH out of production, 29 lines, was never measured, and coverage could
not have said that its tests had stopped running it.

Coverage is asked directly, through its own configuration and parser, which
lines it leaves out.
"""

from pathlib import Path

import coverage
import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"


@pytest.fixture(scope="module")
def left_out():
    """Every app file's lines that coverage leaves out of the count, by path."""
    cov = coverage.Coverage(config_file=str(BACKEND / ".coveragerc"), data_file=None)
    cov.load()

    def lines(path: Path) -> set[int]:
        return set(cov.analysis2(str(path))[2])

    return lines


def test_no_line_about_the_auth_bypass_is_left_out(left_out):
    offenders = []
    for path in sorted(APP.rglob("*.py")):
        text = path.read_text().splitlines()
        offenders += [
            f"{path.relative_to(BACKEND)}:{n}: {text[n - 1].strip()[:60]}"
            for n in sorted(left_out(path))
            if "bypass" in text[n - 1].lower()
        ]
    assert offenders == []


def test_the_bypass_validator_is_measured(left_out):
    path = APP / "core" / "config.py"
    text = path.read_text().splitlines()
    [start] = [n for n, line in enumerate(text, 1) if "def validate_bypass_auth" in line]

    assert {n for n in left_out(path) if start <= n <= start + 60} == set()


def test_a_line_that_says_only_pass_is_still_left_out(left_out):
    # What the pattern was for: a placeholder body, here an empty subclass.
    path = APP / "models" / "book.py"
    text = path.read_text().splitlines()
    bare = [n for n, line in enumerate(text, 1) if line.strip() == "pass"]

    assert bare, "no bare `pass` left in models/book.py to check the pattern against"
    assert set(bare) <= left_out(path)
