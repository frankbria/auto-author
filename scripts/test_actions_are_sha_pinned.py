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

import os
import subprocess
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


# A download piped into a shell is the same hole as a floating tag, one step
# earlier (#819): `curl … | sh` runs whatever that address serves on the day,
# with the job's token and secrets, and leaves nothing to pin, diff or review.
# tests.yml installed uv that way in three jobs.
PIPED_INTO_A_SHELL = re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b")


def _jobs(path):
    return (yaml.safe_load(path.read_text()).get("jobs") or {}).items()


def _scripts(job):
    return [step["run"] for step in job.get("steps") or [] if isinstance(step.get("run"), str)]


def test_the_pattern_sees_a_piped_installer():
    for hit in [
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "curl -fsSL https://example.test/install | sudo bash -s -- --yes",
        "wget -qO- https://example.test/i.sh | bash",
    ]:
        assert PIPED_INTO_A_SHELL.search(hit), hit
    for miss in [
        "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ || true",
        "curl -s https://example.test/health | cut -c1-80",
        "echo done | shasum",
    ]:
        assert not PIPED_INTO_A_SHELL.search(miss), miss


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_no_workflow_pipes_a_download_into_a_shell(path):
    offenders = [
        f"{name}: {match.group(0)}"
        for name, job in _jobs(path)
        for script in _scripts(job)
        for match in PIPED_INTO_A_SHELL.finditer(script)
    ]

    assert not offenders, "install it with a pinned action instead:\n" + "\n".join(offenders)


def test_every_job_that_runs_uv_installs_it_with_the_setup_action():
    """So that removing the piped installer cannot leave a job relying on whatever uv a
    runner image happens to carry."""
    uses_uv = re.compile(r"(^|[\s;&|(])uv (sync|run|export|lock|python|pip|venv|tool|build)\b", re.M)
    checked = []
    for path in _workflow_files():
        for name, job in _jobs(path):
            if not any(uses_uv.search(script) for script in _scripts(job)):
                continue
            checked.append(f"{path.name}:{name}")
            actions = [step.get("uses", "") for step in job.get("steps") or []]
            assert any(a.startswith("astral-sh/setup-uv@") for a in actions), f"{path.name}: job {name} runs uv without setup-uv"

    assert len(checked) >= 4, f"only {checked} run uv; this guard is close to vacuous"


# One uv everywhere (#819 review). The image build pins uv in backend/Dockerfile,
# where Dependabot moves it by pull request. `setup-uv` without `version` installs
# whatever is newest that day, so CI would run a uv nobody reviewed. Each job
# reads the version out of the Dockerfile instead: one place to change, and a
# Dependabot bump of the image's uv moves CI's in the same pull request.
DOCKERFILE_UV = re.compile(r"^FROM astral/uv:([0-9][0-9.]*)@sha256:", re.M)


def _setup_uv_jobs():
    for path in _workflow_files():
        for name, job in _jobs(path):
            steps = job.get("steps") or []
            for index, step in enumerate(steps):
                if step.get("uses", "").startswith("astral-sh/setup-uv@"):
                    yield f"{path.name}:{name}", steps, index


def _read_version(script, cwd, tmp_path):
    """Run a job's `Read the pinned uv version` script in `cwd`; return its exit code and what it set."""
    out = tmp_path / "github_output"
    out.write_text("")
    code = subprocess.run(
        ["bash", "-e", "-c", script], cwd=cwd, env={"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(out)},
        capture_output=True, timeout=30,
    ).returncode
    return code, out.read_text().strip()


def test_every_setup_of_uv_installs_the_version_the_image_build_pins(tmp_path):
    pinned = DOCKERFILE_UV.search((REPO / "backend" / "Dockerfile").read_text())
    assert pinned, "backend/Dockerfile pins no uv version"
    found = list(_setup_uv_jobs())
    assert len(found) >= 4, f"only {[name for name, *_ in found]} set uv up; this guard is close to vacuous"

    for name, steps, index in found:
        assert steps[index]["with"].get("version") == "${{ steps.uv.outputs.version }}", f"{name}: uv's version floats"
        readers = [i for i, step in enumerate(steps) if step.get("id") == "uv"]
        assert readers and readers[0] < index, f"{name}: nothing reads the version before uv is set up"
        code, output = _read_version(steps[readers[0]]["run"], REPO, tmp_path)
        assert (code, output) == (0, f"version={pinned.group(1)}"), f"{name}: read {output!r}, exit {code}"


def test_a_dockerfile_that_pins_no_uv_stops_the_job_instead_of_installing_the_newest(tmp_path):
    """An empty `version` means "latest" to the action, which is the thing being prevented."""
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "Dockerfile").write_text("FROM python:3.13-slim AS base\nCOPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv\n")

    for name, steps, _ in _setup_uv_jobs():
        script = next(step["run"] for step in steps if step.get("id") == "uv")
        code, output = _read_version(script, tmp_path, tmp_path)
        assert code != 0 and output == "", f"{name}: exit {code}, set {output!r}"
