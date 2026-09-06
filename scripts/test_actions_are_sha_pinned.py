"""Guard: every `uses:` in an active workflow is pinned to a commit SHA (#518).

A major tag is mutable. The upstream owner — or anyone who compromises that
account — can repoint `v4` at arbitrary code, and every subsequent run executes
it with no diff, no PR and no notification. `build-images.yml` is where that
matters most: `docker/login-action` receives the registry token and
`build-push-action` publishes the images `deploy-staging-containers.yml` later
pulls and runs on the box, so a repointed tag is a direct path from an upstream
compromise to a malicious image running on staging.

The repo already accepted this argument once, for the reusable workflow that
receives `ZHIPU_API_KEY` (`glm-review.yml`). This makes it the rule instead of a
one-off, because the inconsistency is the bug: a pin that only some workflows
follow gets un-followed by the next workflow someone adds.

**A version tag is not a weaker pin, it is not a pin.** `actions/setup-node@v7.0.0`
looks specific and is exactly as mutable as `@v7` — a full semver tag can be
force-moved to a different commit just the same. Only the 40-character SHA is
immutable, which is why the rule below tests for that and nothing else.

Dependabot updates SHA pins and rewrites the trailing version comment, so this
costs no ongoing manual work; `.github/dependabot.yml` already covers
`github-actions` at `/`. The trade is that its PRs become SHA diffs rather than
tag diffs, making the release notes in the PR body the primary review artifact.
"""

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"

# `uses:` value up to the first whitespace or `#`, so the trailing version
# comment does not become part of the reference.
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
SHA_PINNED = re.compile(r"@[0-9a-f]{40}$")

# BOTH extensions. GitHub runs `.yml` and `.yaml` alike, so globbing only `.yml`
# would leave a silent bypass: a future workflow named `.yaml` executes with the
# repo's credentials while passing a check that never looked at it. Every file
# here happens to be `.yml` today, which is exactly why the omission would not
# have shown up as a failure.
#
# The two `.disabled` PM2 files (#520) are excluded because they never execute,
# so pinning them would be theatre. Renaming one back to a live extension to
# reactivate it is exactly when it must be pinned, and that rename is what puts
# it in scope here.
def _workflow_files():
    return sorted(
        p for ext in ("*.yml", "*.yaml") for p in WORKFLOWS.glob(ext)
    )


def _uses_refs(path):
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        m = USES.match(line)
        if m:
            yield lineno, m.group(1)


def test_there_are_workflows_to_check():
    """Without this, a rename or a moved directory turns every test below green.

    A guard that silently checks nothing is worse than no guard, because the
    passing check is read as evidence.
    """
    files = _workflow_files()
    assert files, f"no workflow files found under {WORKFLOWS}"
    refs = [r for f in files for r in _uses_refs(f)]
    assert refs, "workflow files exist but none declares `uses:` — parser is broken"


@pytest.mark.parametrize(
    "path", _workflow_files(), ids=lambda p: p.name
)
def test_every_action_is_pinned_to_a_commit_sha(path):
    offenders = []
    for lineno, ref in _uses_refs(path):
        # A local composite action lives in this repo and moves only by commit
        # here, so it has nothing to pin to.
        if ref.startswith("./"):
            continue
        if not SHA_PINNED.search(ref):
            offenders.append(f"{path.name}:{lineno} -> {ref}")
    assert not offenders, (
        "Action reference is not pinned to a 40-character commit SHA:\n"
        + "\n".join(offenders)
        + "\n\nA tag — including a full `vX.Y.Z` one — is mutable and can be "
        "repointed upstream at any time, silently. Resolve the tag and pin the "
        "commit, keeping the version in a trailing comment so Dependabot can "
        "update both:\n"
        "  gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object.sha,.object.type'\n"
        "If `.object.type` is `tag` the reference is ANNOTATED and that sha is the "
        "tag object, not the commit — dereference it with "
        "`gh api repos/<owner>/<repo>/git/tags/<sha> --jq .object.sha` before "
        "pinning. (codecov/codecov-action is annotated; most others are not.)\n"
        "  uses: owner/repo@<40-char-sha> # v1.2.3"
    )


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_every_pin_carries_a_version_comment(path):
    """A bare SHA is secure but unreadable, and Dependabot rewrites the comment.

    Without it nobody can tell at a glance whether a pin is current, and a
    reviewer cannot sanity-check a bump without resolving the hash by hand.
    """
    missing = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        m = USES.match(line)
        if not m or not SHA_PINNED.search(m.group(1)):
            continue
        if not re.search(r"#\s*v?\d", line):
            missing.append(f"{path.name}:{lineno} -> {m.group(1)}")
    assert not missing, (
        "SHA-pinned action has no version comment:\n"
        + "\n".join(missing)
        + "\n\nAdd `# vX.Y.Z` after the pin. Dependabot keeps it in sync."
    )


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_parses_as_yaml(path):
    """The pins are applied by rewriting `uses:` lines; a bad edit shows up here."""
    yaml.safe_load(path.read_text())
