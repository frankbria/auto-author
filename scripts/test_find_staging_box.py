"""The staging workflows find the box even after the tailnet's DNS name changes.

On 2026-11-06 the deploy failed with "Could not resolve hostname" on every
attempt: the box was online in the tailnet under the same machine name, but the
STAGING_TS_HOST secret still held the full MagicDNS name under the tailnet's
old suffix. scripts/find-staging-box.sh keeps a resolvable host as it is and
otherwise picks the one online peer with that machine name from the netmap.

Run: uvx --with pytest --with pyyaml pytest scripts/test_find_staging_box.py -q
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "find-staging-box.sh"
WORKFLOWS = REPO / ".github" / "workflows"

# Placeholders in documentation ranges, not real tailnet names or addresses.
OLD = "stagingbox.tail-old.ts.net"


def _peer(dns, ips, online=True):
    return {"DNSName": dns + ".", "TailscaleIPs": ips, "Online": online}


def _run(tmp_path, host, peers, resolves):
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"Peer": {str(i): p for i, p in enumerate(peers)}}))
    env = dict(os.environ, RESOLVE="true" if resolves else "false", TAILSCALE_STATUS_JSON=str(status))
    return subprocess.run(["bash", str(SCRIPT), host], env=env, capture_output=True, text=True)


def test_a_host_that_resolves_is_used_as_configured(tmp_path):
    r = _run(tmp_path, OLD, [], resolves=True)
    assert r.returncode == 0
    assert r.stdout.strip() == OLD
    assert "warning" not in r.stderr


def test_an_unresolvable_host_falls_back_to_the_peer_with_its_machine_name(tmp_path):
    peers = [
        _peer("stagingbox.tail-new.ts.net", ["100.64.0.7", "fd7a:115c:a1e0::7"]),
        _peer("laptop.tail-new.ts.net", ["100.64.0.9"]),
    ]
    r = _run(tmp_path, OLD, peers, resolves=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "100.64.0.7"
    assert "::warning::" in r.stderr and "STAGING_TS_HOST" in r.stderr


def test_the_machine_name_matches_case_insensitively(tmp_path):
    r = _run(tmp_path, "StagingBox.tail-old.ts.net", [_peer("stagingbox.tail-new.ts.net", ["100.64.0.7"])], resolves=False)
    assert r.stdout.strip() == "100.64.0.7"


@pytest.mark.parametrize(
    "peers",
    [
        [],
        [_peer("stagingbox.tail-new.ts.net", ["100.64.0.7"], online=False)],
        [_peer("stagingbox.tail-new.ts.net", ["100.64.0.7"]), _peer("stagingbox.other.ts.net", ["100.64.0.8"])],
        [_peer("stagingbox2.tail-new.ts.net", ["100.64.0.7"])],
    ],
    ids=["no-peer", "offline", "two-peers", "prefix-is-not-a-match"],
)
def test_anything_but_one_online_match_stops_the_job(tmp_path, peers):
    r = _run(tmp_path, OLD, peers, resolves=False)
    assert r.returncode != 0
    assert r.stdout == ""
    assert "::error::" in r.stderr


def test_no_host_configured_stops_the_job(tmp_path):
    r = _run(tmp_path, "", [], resolves=False)
    assert r.returncode != 0


# Every workflow that SSHes to the box, so a new one can't skip the resolver.
SSHING = sorted(p.name for p in WORKFLOWS.glob("*.yml") if re.search(r"\b(ssh|scp) -i ", p.read_text()))


def test_the_sshing_workflows_are_found():
    assert {"deploy-staging-containers.yml", "sync-staging-env.yml", "set-staging-billing.yml"} <= set(SSHING)


@pytest.mark.parametrize("workflow", SSHING)
def test_the_workflows_ssh_to_the_found_address_only(workflow):
    text = (WORKFLOWS / workflow).read_text()
    assert "scripts/find-staging-box.sh" in text
    assert 'STAGING_BOX=' in text and '>> "$GITHUB_ENV"' in text
    # Every ssh/scp target is the found address, never the raw secret.
    assert not re.search(r"@\$\{\{\s*secrets\.(STAGING_TS_HOST|HOST)", text), workflow
    assert len(re.findall(r'@"\$STAGING_BOX"', text)) >= 2, workflow
