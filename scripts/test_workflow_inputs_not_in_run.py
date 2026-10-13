"""Guard: what a caller types never becomes part of a shell command (#816).

`${{ inputs.image_tag }}` sat inside the command the staging deploy runs over
SSH as root. GitHub pastes an expression into the script before any shell sees
it, so a dispatch with a tag of `x'; curl … | sh; '` was that command: anyone
who can dispatch the workflow could run anything on the box.

Two rules, both needed:

1. An input reaches a script only as an environment variable. The shell expands
   a variable as data; it never parses it as code.
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
CALLER_TEXT = re.compile(
    r"\$\{\{[^}]*\b(inputs|github\.event|github\.head_ref|github\.base_ref|github\.ref_name)\b[^}]*\}\}"
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


def _from_caller(env):
    """The variables in an `env:` mapping whose value is text the caller chose."""
    return {name for name, value in (env or {}).items() if CALLER_TEXT.search(str(value))}


def _caller_variables(path):
    """{job: {variable}} for every variable a caller's text reaches, set on the workflow, a job or a step."""
    doc = _load(path)
    found = {}
    for name, job in _jobs(path):
        variables = _from_caller(doc.get("env")) | _from_caller(job.get("env"))
        for step in job.get("steps") or []:
            variables |= _from_caller(step.get("env"))
        if variables:
            found[name] = variables
    return found


def test_the_pattern_sees_what_it_is_for():
    for hit in [
        "export IMAGE_TAG='${{ inputs.image_tag }}'",
        'echo "- Workers: ${{ github.event.inputs.staging_e2e_workers || \'1\' }}"',
        "git checkout ${{ github.head_ref }}",
        'echo "built from ${{ github.ref_name }}"',
        "git diff ${{ github.base_ref }}...",
        'echo "${{ github.event.pull_request.title }}"',
    ]:
        assert CALLER_TEXT.search(hit), hit
    for miss in [
        "${{ secrets.USER }}", "${{ job.status }}", "${{ github.event_name }}", "${{ matrix.app }}",
        "${{ github.sha }}", "${{ github.repository }}", "$IMAGE_TAG",
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


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_no_caller_text_is_pasted_into_a_script(path):
    pasted = [
        f"{job}: step {index} ({step.get('name', '?')}): {match.group(0)}"
        for job, body in _jobs(path)
        for index, step in enumerate(body.get("steps") or [])
        for match in CALLER_TEXT.finditer(str(step.get("run", "")))
    ]

    assert not pasted, "pass it through env: and check it first:\n" + "\n".join(pasted)


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
