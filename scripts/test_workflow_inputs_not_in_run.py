"""Guard: what a caller types never becomes part of a shell command (#816).

`${{ inputs.image_tag }}` sat inside the command the staging deploy runs over
SSH as root. GitHub pastes an expression into the script before any shell sees
it, so a dispatch with a tag of `x'; curl … | sh; '` was that command: anyone
who can dispatch the workflow could run anything on the box.

Two rules, both needed:

1. An input reaches a script only as an environment variable set on the job.
   The shell expands a variable as data; it never parses it as code. Anywhere
   else an expression could carry it towards a script (a `run:` block, a step's
   or the workflow's `env:`, a matrix, a job's outputs) it is refused.
2. The job's first step checks each such variable against a pattern and stops
   the job. Rule 1 alone is not enough for the deploy, whose script is a string
   handed to ssh: the *runner's* shell pastes `$IMAGE_TAG` into that string,
   and the box's shell then parses it.
"""

import os
import re
import subprocess

import pytest
import yaml

from test_actions_are_sha_pinned import _workflow_files

# Text chosen by whoever triggers the run: dispatch inputs, the event payload
# (titles, bodies, branch names) and the names of the branches involved.
# An expression runs to its closing `}}`; a single `}` inside it (`format('{0}', …)`)
# does not end it.
_INSIDE = r"(?:(?!\}\}).)*"
CALLER_TEXT = re.compile(
    r"\$\{\{" + _INSIDE + r"\b(inputs|github\.event|github\.(head_|base_)?ref(_name)?)\b" + _INSIDE + r"\}\}",
    re.S,
)

HOSTILE = ["", "$(id)", "`id`", "x'; id; '", 'x"; id; "', "x && id", "x | id", "x\nid", "x y"]

# job-in-workflow -> variable -> (values that must pass, values that must stop the job)
VALIDATED = {
    ("deploy-staging-containers.yml", "deploy"): {
        "IMAGE_TAG": (
            ["sha-3931169", "sha-" + "a1" * 20],
            ["staging", "latest", "sha-", "sha-39311", "sha-xyz1234", "SHA-3931169", "sha-3931169-staging",
             "sha-3931169'; id; '", "sha-3931169 && id", "sha-3931169\nid", "sha-3931169$(id)"],
        ),
    },
    ("e2e-staging-tests.yml", "e2e-staging"): {
        "STAGING_E2E_WORKERS": (["1", "2", "9"], ["0", "10", "-1", "1.5", "two", "1; id", "1\n2"]),
    },
    ("sync-staging-env.yml", "sync"): {
        "RECREATE": (["true", "false"], ["yes", "1", "True", "true; id", "true\nfalse"]),
    },
}


def _load(path):
    return yaml.safe_load(path.read_text())


def _jobs(path):
    return (_load(path).get("jobs") or {}).items()


def _strings(node, where=()):
    """Every string in a workflow, with where it sits: ("jobs", "deploy", "steps", 3, "run")."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, where + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _strings(value, where + (index,))
    elif isinstance(node, str):
        yield where, node


def _is_a_job_variable(where):
    return len(where) == 4 and where[0] == "jobs" and where[2] == "env"


def _never_reaches_a_shell(where):
    """Places whose value GitHub or an action reads, and no script does."""
    return (
        "concurrency" in where
        or where[-1] == "if"
        # An action's input. `script` is the one that is code: actions/github-script runs it.
        or (len(where) >= 2 and where[-2] == "with" and where[-1] != "script")
    )


def _caller_text(path):
    """(where, expression) for every expression in the workflow that carries text the caller chose."""
    return [(where, match.group(0)) for where, text in _strings(_load(path)) for match in CALLER_TEXT.finditer(text)]


def _caller_variables(path):
    """{job: {variable}} for every job variable filled from the caller's text."""
    found = {}
    for where, _ in _caller_text(path):
        if _is_a_job_variable(where):
            found.setdefault(where[1], set()).add(where[3])
    return found


def test_the_pattern_sees_what_it_is_for():
    for hit in [
        "export IMAGE_TAG='${{ inputs.image_tag }}'",
        'echo "- Workers: ${{ github.event.inputs.staging_e2e_workers || \'1\' }}"',
        "git checkout ${{ github.head_ref }}",
        'echo "built from ${{ github.ref_name }}"',
        "git diff ${{ github.base_ref }}...",
        'echo "building ${{ github.ref }}"',
        # A `}` inside the expression, before the name, must not end the match.
        "export IMAGE_TAG='${{ format('sha-{0}', inputs.image_tag) }}'",
        'echo "${{ github.event.pull_request.title }}"',
    ]:
        assert CALLER_TEXT.search(hit), hit
    for miss in [
        "${{ secrets.USER }}", "${{ job.status }}", "${{ github.event_name }}", "${{ matrix.app }}",
        "${{ github.sha }}", "${{ github.repository }}", "${{ github.ref_type }}", "$IMAGE_TAG",
        "${{ secrets.USER }} and then the word inputs.image_tag outside any expression",
    ]:
        assert not CALLER_TEXT.search(miss), miss


def test_there_is_something_to_guard():
    declared = [
        name
        for path in _workflow_files()
        for name in ((_load(path).get(True) or {}).get("workflow_dispatch") or {}).get("inputs") or {}
    ]
    scripts = [step for path in _workflow_files() for _, job in _jobs(path) for step in job.get("steps") or [] if "run" in step]

    assert {"image_tag", "staging_e2e_workers", "recreate"} <= set(declared), declared
    assert len(scripts) > 20, "few or no run: blocks were read; this guard is vacuous"


def test_the_places_are_sorted_as_intended():
    job = ("jobs", "deploy")
    for refused in [
        job + ("steps", 3, "run"),
        job + ("steps", 3, "env", "IMAGE_TAG"),  # would re-fill a variable the first step already checked
        ("env", "IMAGE_TAG"),
        job + ("strategy", "matrix", "tag", 0),  # then `${{ matrix.tag }}` in a script
        job + ("outputs", "tag"),  # then `${{ needs.deploy.outputs.tag }}` in another job's script
        job + ("steps", 3, "with", "script"),
        job + ("steps", 3, "shell"),
        job + ("container", "image"),
    ]:
        assert not _never_reaches_a_shell(refused) and not _is_a_job_variable(refused), refused
    for allowed in [
        ("concurrency", "group"),
        job + ("concurrency", "group"),
        job + ("if",),
        job + ("steps", 3, "if"),
        job + ("steps", 3, "with", "ref"),
    ]:
        assert _never_reaches_a_shell(allowed), allowed
    assert _is_a_job_variable(job + ("env", "IMAGE_TAG"))


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_caller_text_goes_nowhere_but_a_job_variable(path):
    misplaced = [
        ".".join(map(str, where)) + ": " + expression
        for where, expression in _caller_text(path)
        if not _is_a_job_variable(where) and not _never_reaches_a_shell(where)
    ]

    assert not misplaced, "set it as a variable on the job and check it first:\n" + "\n".join(misplaced)


def test_every_variable_a_caller_fills_is_in_the_table_below():
    found = {
        (path.name, job): variables for path in _workflow_files() for job, variables in _caller_variables(path).items()
    }

    assert found == {key: set(checks) for key, checks in VALIDATED.items()}


@pytest.mark.parametrize("workflow, job", VALIDATED, ids=lambda v: str(v))
def test_the_first_step_checks_them_and_cannot_be_skipped(workflow, job):
    path = next(p for p in _workflow_files() if p.name == workflow)
    first = dict(_jobs(path))[job]["steps"][0]

    assert "run" in first, "the first step must be the check, before any action runs"
    assert "if" not in first and "continue-on-error" not in first
    for variable in VALIDATED[(workflow, job)]:
        assert variable in first["run"], f"{variable} is not checked by the first step"


def _first_step_exit(workflow, job, variable, value):
    path = next(p for p in _workflow_files() if p.name == workflow)
    script = dict(_jobs(path))[job]["steps"][0]["run"]
    env = {"PATH": os.environ["PATH"], variable: value}
    return subprocess.run(["bash", "-euo", "pipefail", "-c", script], env=env, capture_output=True, timeout=30).returncode


CASES = [
    (workflow, job, variable, value, ok)
    for (workflow, job), checks in VALIDATED.items()
    for variable, (good, bad) in checks.items()
    # A value that passes with a command before or after it must not: a check
    # that is not anchored at both ends lets exactly that through.
    for value, ok in [(v, True) for v in good]
    + [(v, False) for v in bad + HOSTILE + [f"id; {good[0]}", f"{good[0]}; id", f"x{good[0]}", f"{good[0]}x"]]
]


@pytest.mark.parametrize("workflow, job, variable, value, ok", CASES, ids=lambda v: repr(v)[:40])
def test_the_check_lets_through_only_what_it_should(workflow, job, variable, value, ok):
    code = _first_step_exit(workflow, job, variable, value)

    assert (code == 0) is ok, f"{variable}={value!r} exited {code}"


DEPLOY = "deploy-staging-containers.yml"


@pytest.mark.parametrize("step_name", ["Pull and start", "Health check"])
def test_the_box_does_not_parse_the_tag_even_when_the_check_did_not_run(step_name, tmp_path):
    """A later step given `if: always()` would run after the check had failed, with the refused
    tag still in the variable. So the tag is also quoted for the box where it is handed to ssh."""
    path = next(p for p in _workflow_files() if p.name == DEPLOY)
    step = next(s for s in dict(_jobs(path))["deploy"]["steps"] if s.get("name") == step_name)
    box, stubs = tmp_path / "box", tmp_path / "bin"
    box.mkdir(), stubs.mkdir()
    # ssh: run the command it is handed, on a stand-in for the box.
    (stubs / "ssh").write_text(
        f'#!/usr/bin/env bash\ncmd="${{@: -1}}"; cd {box} && bash -c "${{cmd//\\/opt\\/auto-author/{box}}}"\n'
    )
    (stubs / "docker").write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$IMAGE_TAG" >> {box}/tags\n')
    (stubs / "curl").write_text("#!/usr/bin/env bash\nprintf 000\n")
    (stubs / "sleep").write_text("#!/usr/bin/env bash\n")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    script = re.sub(r"\$\{\{[^}]*\}\}", "box", step["run"])
    hostile = "sha-3931169'; touch pwned; echo '"

    subprocess.run(
        ["bash", "-e", "-c", script],
        env={"PATH": f"{stubs}:{os.environ['PATH']}", "HOME": str(tmp_path), "IMAGE_TAG": hostile},
        capture_output=True,
        timeout=60,
    )

    assert not (box / "pwned").exists(), "the tag was parsed as a command on the box"
    assert set((box / "tags").read_text().splitlines()) == {hostile}, "docker did not receive the tag as it was given"
