"""Guards for .github/dependabot.yml.

`exclude-paths` once hid backend/requirements.txt from the uv ecosystem, which parsed
that generated export as a manifest (#512, upstream dependabot-core#13912). #534 deleted
the export outright, so the exclusion and the test pinning it went with it — there is no
longer a generated file to hide. The relativity guard below stays: it is not specific to
that entry, and an exclude-paths glob is relative to its entry's `directory`, so a
repo-relative path silently matches nothing while the config still looks correct.
"""

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
UPDATES = yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text())["updates"]


def test_the_generated_requirements_export_stays_deleted():
    """#534 deleted backend/requirements.txt, which removed every other tripwire.

    The sync-gate CI step, the `exclude-paths` entry and the test pinning it all
    went with the file, so nothing else would notice it coming back. It comes back
    the moment someone runs the `uv export` command still quoted in CHANGELOG and
    demo entries — and Dependabot's uv ecosystem would parse it as a manifest
    again, reviving #512's unmergeable transitive-only PRs with no failing check
    to say so. uv.lock is the only dependency source; there is nothing to export.
    """
    assert not (REPO / "backend" / "requirements.txt").exists(), (
        "backend/requirements.txt is back. It is a generated export of uv.lock that "
        "nothing installs from — the Dockerfile, CI and the deploy all run `uv sync`. "
        "#534 deleted it because keeping it in sync cost a manual `uv export` on every "
        "backend dependency PR, and because the dependency graph counted it as a "
        "second manifest (duplicate advisories) while Dependabot parsed it as one "
        "(#512). Delete it again rather than restoring the gate."
    )


# Parametrized over entries that declare `exclude-paths`. Since #534 removed the
# only one, this collects as a single skip — deliberately: the guard self-arms the
# day an exclusion returns, which is exactly when the directory-relative footgun
# below matters again.
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

# github-actions ships no runtime code, and its bumps are one-line tag moves where
# a major (v3 -> v4) is the ordinary case, not the risky one — so grouping majors
# there is the point rather than a hazard.
#
# Deliberately a denylist, not an allowlist of {npm, uv}: a future ecosystem —
# `docker`, say, where a grouped base-image major is exactly the kind of change
# that should be read on its own — must be covered the day it is added, not the
# day someone remembers to extend this set. Unknown ecosystems fail closed.
_EXEMPT_FROM_MAJOR_RULE = {"github-actions"}


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
        if e["package-ecosystem"] not in _EXEMPT_FROM_MAJOR_RULE
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


# #556: better-auth 1.6.26 -> 1.7.1 rode into main as one line of a 26-package
# grouped PR and made the app a total auth outage on deploy. 1.7 added a required
# `account.issuer` and keys accounts on (issuer, accountId), so every credential
# row written by 1.6 stopped matching and sign-in, password reset and password
# change all returned 401. No CI check could have caught it: the E2E suite creates
# its users fresh and accounts created on 1.7 work fine, so only a database
# holding pre-1.7 accounts reproduces it.
#
# The minor/patch filter guarding the group above is not protection here —
# better-auth ships credential-lookup and schema changes under semver minor.
_MUST_ARRIVE_ALONE = "better-auth"


@pytest.mark.parametrize(
    ("directory", "name", "group"),
    [
        pytest.param(e["directory"], name, group, id=f"{e['directory']}:{name}")
        for e in UPDATES
        if e["package-ecosystem"] == "npm"
        for name, group in (e.get("groups") or {}).items()
        # better-auth is a production dependency, so a dev-typed group cannot
        # reach it however broad its patterns are — same carve-out the major
        # rule above makes, for the same reason.
        if group.get("dependency-type") != "development"
    ],
)
def test_better_auth_is_never_grouped(directory, name, group):
    """No npm group may match better-auth, so its bumps always arrive on their own.

    A `patterns: ["*"]` group matches it unless `exclude-patterns` says otherwise;
    checking only the prod group would miss a future group that also catches it.
    """
    patterns = group.get("patterns") or []
    excluded = group.get("exclude-patterns") or []
    matches = any(p == "*" or p == _MUST_ARRIVE_ALONE for p in patterns)
    if not matches:
        pytest.skip(f"group {name!r} cannot match {_MUST_ARRIVE_ALONE}")
    assert _MUST_ARRIVE_ALONE in excluded, (
        f"npm group {name!r} in {directory} matches {_MUST_ARRIVE_ALONE} and does not "
        f"exclude it, so its next bump can ride in with the rest of the batch. That is "
        f"exactly how #556 landed — a minor bump of the auth library, invisible in a "
        f"26-package diff, that locked out every existing account on deploy. Add "
        f'`exclude-patterns: ["{_MUST_ARRIVE_ALONE}"]` to this group.'
    )
