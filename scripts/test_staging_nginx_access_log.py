"""scripts/staging-nginx-access-log.sh against a stand-in nginx tree (#1223).

The script edits nginx on a box shared with other apps, so what it must NOT do
matters as much as what it does: touch the api vhost, touch a second file, stack
a second access_log, or leave a config that fails `nginx -t`.

Run: uvx --with pytest pytest scripts/test_staging_nginx_access_log.py -q
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "staging-nginx-access-log.sh"

SITE_CONF = """\
server {
    listen 80;
    server_name dev.autoauthor.app;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name dev.autoauthor.app; # the frontend
    location / {
        proxy_pass http://127.0.0.1:3002;
    }
}

server {
    listen 443 ssl;
    server_name api.dev.autoauthor.app;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
"""

OTHER_APP = """\
server {
    listen 443 ssl;
    server_name other.example.com;
    access_log /var/log/nginx/other.access.log;
}
"""


@pytest.fixture
def box(tmp_path):
    etc = tmp_path / "nginx"
    (etc / "sites-available").mkdir(parents=True)
    (etc / "sites-enabled").mkdir()
    (etc / "conf.d").mkdir()
    (etc / "sites-available" / "auto-author").write_text(SITE_CONF)
    (etc / "sites-enabled" / "auto-author").symlink_to(etc / "sites-available" / "auto-author")
    (etc / "sites-enabled" / "other").write_text(OTHER_APP)
    logs = tmp_path / "log"
    logs.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # nginx stand-in: records its arguments; `-t` fails when nginx_t_fails exists.
    (bin_dir / "nginx").write_text(
        f'#!/usr/bin/env bash\necho "$*" >> {tmp_path}/nginx-calls\n'
        f'if [ "$1" = -t ] && [ -e {tmp_path}/nginx_t_fails ]; then echo "test failed"; exit 1; fi\n'
    )
    (bin_dir / "nginx").chmod(0o755)
    return tmp_path


def run(box, *args):
    env = {
        "PATH": os.environ["PATH"],
        "NO_SUDO": "1",
        "NGINX_DIR": str(box / "nginx"),
        "LOG_FILE": str(box / "log" / "dev.autoauthor.app.access.log"),
        "BACKUP_DIR": str(box / "backups"),
        "NGINX": str(box / "bin" / "nginx"),
    }
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30)


def conf(box):
    return (box / "nginx" / "sites-available" / "auto-author").read_text()


def nginx_calls(box):
    path = box / "nginx-calls"
    return path.read_text().split("\n")[:-1] if path.exists() else []


def access_lines(box):
    return [line for line in conf(box).splitlines() if "access_log" in line]


def test_dry_run_reports_the_change_and_changes_nothing(box):
    result = run(box, "dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert conf(box) == SITE_CONF
    assert "+    access_log " in result.stdout
    assert "Dry run: nothing changed." in result.stdout
    assert nginx_calls(box) == ["-t"]
    assert not (box / "backups").exists()


def test_apply_logs_both_site_blocks_and_not_the_api(box):
    result = run(box, "apply")

    assert result.returncode == 0, result.stdout + result.stderr
    log = box / "log" / "dev.autoauthor.app.access.log"
    lines = conf(box).splitlines()
    for i, line in enumerate(lines):
        if "server_name dev.autoauthor.app" in line:
            assert lines[i + 1] == f"    access_log {log};"
        if "server_name api.dev.autoauthor.app" in line:
            assert "access_log" not in lines[i + 1]
    assert len(access_lines(box)) == 2
    # Written through the symlink: sites-enabled still points at the edited file.
    assert (box / "nginx" / "sites-enabled" / "auto-author").is_symlink()
    assert (box / "nginx" / "sites-enabled" / "other").read_text() == OTHER_APP
    # The current config is tested before anything is written, then the new one, then reload.
    assert nginx_calls(box) == ["-t", "-t", "-s reload"]
    backups = list((box / "backups").iterdir())
    assert len(backups) == 1 and backups[0].read_text() == SITE_CONF


def test_apply_twice_changes_nothing_the_second_time(box):
    run(box, "apply")
    once = conf(box)

    result = run(box, "apply")

    assert result.returncode == 0
    assert "Already enabled" in result.stdout
    assert conf(box) == once


def test_a_failing_nginx_test_puts_the_original_back_and_does_not_reload(box):
    (box / "nginx_t_fails").touch()

    result = run(box, "apply")

    assert result.returncode != 0
    assert conf(box) == SITE_CONF
    assert "-s reload" not in nginx_calls(box)


def test_an_existing_access_log_is_left_for_a_human(box):
    site = box / "nginx" / "sites-available" / "auto-author"
    site.write_text(SITE_CONF.replace("# the frontend\n", "\n    access_log off;\n"))
    before = site.read_text()

    result = run(box, "apply")

    assert result.returncode != 0
    assert "left for a human" in result.stdout
    assert site.read_text() == before


@pytest.mark.parametrize("where", ["sites-enabled/copy", "conf.d/copy.conf"])
def test_two_files_naming_the_site_stop_it(box, where):
    (box / "nginx" / where).write_text(SITE_CONF)

    result = run(box, "apply")

    assert result.returncode != 0
    assert "found 2" in result.stderr
    assert conf(box) == SITE_CONF


def test_no_file_naming_the_site_stops_it(box):
    (box / "nginx" / "sites-enabled" / "auto-author").unlink()

    result = run(box, "dry-run")

    assert result.returncode != 0
    assert "found 0" in result.stderr


def test_verify_finds_this_runs_request_and_nothing_else(box):
    log = box / "log" / "dev.autoauthor.app.access.log"
    log.write_text('1.2.3.4 - - [26/Nov/2026] "GET /auth/sign-in HTTP/2.0" 200 1 "-" "auto-author-1223-check-42"\n')

    assert run(box, "verify", "auto-author-1223-check-42").returncode == 0
    assert run(box, "verify", "auto-author-1223-check-43").returncode == 1
    assert run(box, "verify", "auto-author-1223-check-42; id").returncode == 2


def test_an_unknown_mode_is_refused(box):
    assert run(box, "remove").returncode == 2
    assert conf(box) == SITE_CONF
