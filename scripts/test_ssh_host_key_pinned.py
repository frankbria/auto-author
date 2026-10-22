"""Guard: workflows that SSH to the box verify its pinned host key (#859)."""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def _sshing_workflows():
    return [wf for wf in WORKFLOWS.glob("*.yml") if re.search(r"\b(ssh|scp) -i ", wf.read_text())]


def test_no_workflow_trusts_an_unknown_host_key():
    workflows = _sshing_workflows()
    assert workflows, "no workflow SSHes to the box; this guard is vacuous"
    for wf in workflows:
        text = wf.read_text()
        assert not re.search(r"StrictHostKeyChecking=(accept-new|no)\b", text), wf.name
        assert "StrictHostKeyChecking=yes" in text, wf.name


def test_every_sshing_workflow_writes_the_pinned_known_hosts():
    for wf in _sshing_workflows():
        text = wf.read_text()
        assert "secrets.STAGING_KNOWN_HOSTS" in text, wf.name
        assert '"$STAGING_KNOWN_HOSTS" > ~/.ssh/known_hosts' in text, wf.name
