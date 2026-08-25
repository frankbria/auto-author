"""Guards for .github/dependabot.yml.

Dependabot's `uv` ecosystem parsed backend/requirements.txt — a generated export of
uv.lock — as a manifest. Transitive deps exist only there, so a transitive bump
produced a PR editing the export alone: it changed nothing installed and failed the
lock/export sync gate in tests.yml (#512, upstream dependabot-core#13912).
`exclude-paths` hides the export so only pyproject.toml/uv.lock are ever bumped.

The second test catches the one way that fix breaks silently: an exclude-paths glob
is relative to the entry's `directory`, so a repo-relative path matches nothing and
Dependabot carries on opening the no-op PRs with the config looking correct.
"""

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
UPDATES = yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text())["updates"]


def test_uv_ecosystem_excludes_the_generated_requirements_export():
    uv = [e for e in UPDATES if e["package-ecosystem"] == "uv" and e["directory"] == "/backend"]
    assert uv, "no uv entry for /backend in dependabot.yml"
    assert "requirements.txt" in uv[0].get("exclude-paths", []), (
        "backend/requirements.txt is a generated export of uv.lock. Without it in "
        "exclude-paths, Dependabot opens transitive-dependency PRs that edit only "
        "the export — unmergeable no-ops that fail the Security Audit sync gate."
    )


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(e, id=f"{e['package-ecosystem']}{e['directory']}")
        for e in UPDATES
        if e.get("exclude-paths")
    ],
)
def test_exclude_paths_are_relative_to_the_entry_directory(entry):
    base = REPO / entry["directory"].lstrip("/")
    for pattern in entry["exclude-paths"]:
        assert any(base.glob(pattern)), (
            f"exclude-paths pattern {pattern!r} matches nothing under {base}. "
            "Patterns are relative to the entry's `directory`, not the repo root."
        )
