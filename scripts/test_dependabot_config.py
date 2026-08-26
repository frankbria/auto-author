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


# Grouping guards (#517). Ungrouped, every package gets its own PR, and with
# branch protection's `strict: true` each merge flips the rest to BEHIND — the
# 2026-08-25 sweep cost ~2h20m and 9 CI runs to land 9 bumps. Worse, four PRs
# racing on .github/workflows/build-images.yml led Dependabot to self-close #504
# with a false "up-to-date now" while main still pinned @v3.

# github-actions ships no runtime code, and its bumps are one-line tag moves
# where a major (v3 -> v4) is the ordinary case, not the risky one — so grouping
# majors there is the point rather than a hazard. npm and uv do ship.
_SHIPS_RUNTIME_CODE = {"npm", "uv"}


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(e, id=f"{e['package-ecosystem']}{e['directory']}")
        for e in UPDATES
    ],
)
def test_every_ecosystem_groups_its_updates(entry):
    assert entry.get("groups"), (
        f"{entry['package-ecosystem']} {entry['directory']} has no `groups:`, so "
        "every bump opens its own PR. With required_status_checks.strict=true on "
        "main, each merge flips the others to BEHIND and forces a serial "
        "rebase -> full-CI -> merge loop (#517)."
    )


@pytest.mark.parametrize(
    ("ecosystem", "directory", "name", "group"),
    [
        pytest.param(e["package-ecosystem"], e["directory"], name, group,
                     id=f"{e['package-ecosystem']}{e['directory']}:{name}")
        for e in UPDATES
        if e["package-ecosystem"] in _SHIPS_RUNTIME_CODE
        for name, group in (e.get("groups") or {}).items()
        if group.get("dependency-type") != "development"
    ],
)
def test_shipping_groups_never_swallow_a_major(ecosystem, directory, name, group):
    """A group that can match a production dependency must exclude majors.

    Grouped PRs are cheap to merge and expensive to review or revert, which is
    the wrong trade for a bump that reaches users. The worked example is this
    repo's own `mongodb` 6.21.0 -> 7.5.0 (#507): it earned a solo PR and its own
    staging verification (#516), and folding it into a batch of lockfile bumps
    would have buried exactly the change worth reading.

    Omitting `update-types` entirely means "all types", so an unset value fails
    here too — that is the silent way this protection would be lost.
    """
    allowed = {"minor", "patch"}
    declared = group.get("update-types")
    assert declared is not None, (
        f"group {name!r} in {ecosystem} {directory} sets no `update-types`, which "
        "means every type including major. Restrict it to minor/patch, or mark "
        'the group `dependency-type: "development"` if it cannot reach users.'
    )
    assert set(declared) <= allowed, (
        f"group {name!r} in {ecosystem} {directory} groups {sorted(set(declared) - allowed)}. "
        "A production major must arrive as its own PR so it can be reviewed and "
        "reverted on its own."
    )
