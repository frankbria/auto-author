"""The staging deploy logs in to ghcr.io itself, on every run, without leaking the token.

On 2026-11-03 every pull on the box failed with `error from registry: denied`
although both packages are public: the box's saved ghcr.io login held a token
that no longer worked, and docker sends a saved login rather than pulling
anonymously. So "Pull and start" now gives docker a fresh, empty config
directory for the run, logs it in with the job's own GITHUB_TOKEN and deletes
it when the script ends. The box's own config (shared with other apps on that
box) is never read or written, so a stale login there cannot break a deploy and
this deploy cannot clobber someone else's login.

The token travels on ssh's stdin into `docker login --password-stdin`, so it is
never part of a command line (visible in `ps` and in the job log) or of the
box's shell history.

Run: uvx --with pytest --with pyyaml pytest scripts/test_deploy_registry_login.py -q
"""

import os
import re
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / ".github" / "workflows" / "deploy-staging-containers.yml"
TOKEN = "ghs_FAKEtokenFAKEtokenFAKEtoken0123"
STALE = '{"auths": {"ghcr.io": {"auth": "c3RhbGU6c3RhbGU="}}}\n'


def _workflow():
    return yaml.safe_load(DEPLOY.read_text())


def _step(name):
    return next(s for s in _workflow()["jobs"]["deploy"]["steps"] if s.get("name") == name)


def test_the_job_may_read_packages_and_write_nothing():
    perms = _workflow()["permissions"]
    assert perms == {"contents": "read", "packages": "read"}


def test_the_token_reaches_the_step_only_as_a_variable():
    step = _step("Pull and start")
    assert step["env"]["GHCR_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert "GITHUB_TOKEN" not in step["run"], "the token expression is pasted into the script"


def _run(tmp_path, login_works=True):
    box, stubs, home = tmp_path / "box", tmp_path / "bin", tmp_path / "home"
    for d in (box, stubs, home / ".docker"):
        d.mkdir(parents=True)
    (home / ".docker" / "config.json").write_text(STALE)
    log, ssh_log = tmp_path / "log", tmp_path / "ssh-args"
    # ssh: record its arguments (apart from docker's log: the script spans lines), then run the command it is handed on a stand-in
    # for the box, passing its stdin through as the real ssh does.
    (stubs / "ssh").write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> {ssh_log}\n'
        f'cmd="${{@: -1}}"; cd {box} && HOME={home} bash -c "${{cmd//\\/opt\\/auto-author/{box}}}"\n'
    )
    (stubs / "docker").write_text(
        "#!/usr/bin/env bash\n"
        f'printf "docker config=%s args=%s\\n" "${{DOCKER_CONFIG:-unset}}" "$*" >> {log}\n'
        'if [ "$1" = login ]; then\n'
        f'  printf "stdin=%s\\n" "$(cat)" >> {log}\n'
        f'  {"" if login_works else "exit 1"}\n'
        '  printf \'{"auths":{"ghcr.io":{"auth":"x"}}}\' > "${DOCKER_CONFIG:-$HOME/.docker}/config.json"\n'
        "fi\n"
    )
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    script = re.sub(r"\$\{\{[^}]*\}\}", "box", _step("Pull and start")["run"])
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        env={
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "HOME": str(tmp_path),
            "IMAGE_TAG": "sha-3931169",
            "GHCR_TOKEN": TOKEN,
            "GHCR_USER": "frankbria",
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return result, log.read_text().splitlines(), ssh_log.read_text(), home


def test_each_run_logs_in_with_the_token_on_stdin_and_leaves_nothing(tmp_path):
    result, lines, ssh_args, home = _run(tmp_path)
    assert result.returncode == 0, result.stderr

    commands = [line for line in lines if line.startswith("docker ")]
    assert TOKEN not in ssh_args, "the token is on ssh's command line"
    assert not any(TOKEN in line for line in commands), "the token is on docker's command line"
    assert TOKEN not in result.stdout + result.stderr, "the token is in the job log"

    login = next(i for i, line in enumerate(lines) if "args=login" in line)
    assert "--password-stdin" in lines[login] and "ghcr.io" in lines[login]
    assert lines[login + 1] == f"stdin={TOKEN}"

    pull = next(i for i, line in enumerate(lines) if line.endswith(" pull"))
    assert login < pull, "the pull ran before the login"

    configs = {line.split()[1] for line in commands}
    assert len(configs) == 1, "docker did not use one config for the whole run"
    (config,) = configs
    config = config.removeprefix("config=")
    assert config != "unset" and not config.startswith(str(home)), "docker used the box's own config"
    assert not Path(config).exists(), "the run's login was left on the box"
    assert (home / ".docker" / "config.json").read_text() == STALE, "the box's own login was changed"


def test_a_failed_login_still_pulls_anonymously(tmp_path):
    result, lines, _, home = _run(tmp_path, login_works=False)
    assert result.returncode == 0, result.stderr
    assert any(line.endswith(" pull") for line in lines), "a failed login stopped the deploy"
    pulls = [line for line in lines if line.endswith(" pull")]
    assert "unset" not in pulls[0] and str(home) not in pulls[0], "the pull fell back to the stale login"
    assert (home / ".docker" / "config.json").read_text() == STALE
