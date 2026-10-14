"""Guard: operator docs do not describe the retired PM2 deploy as live (#846).

The docs said no workflow writes the staging box's `.env` after
`sync-staging-env.yml` began writing `MONGODB_URI` into it (the #537 trap), and
pointed at a `.yml.disabled` rollback that #656 deleted. The changelog, the
archive and dated demo records describe the past and are left alone.
"""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SELF = "scripts/test_deploy_docs_current.py"
STALE = ["No workflow writes", "no workflow writes", "yml.disabled"]


def test_no_doc_describes_the_retired_deploy_as_live():
    args = ["git", "grep", "-n", "-F"]
    for phrase in STALE:
        args += ["-e", phrase]
    args += ["--", ":!docs/CHANGELOG.md", ":!archive", ":!docs/demos", f":!{SELF}"]
    found = subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout
    assert found == "", f"stale deploy docs:\n{found}"


def test_pm2_template_is_gone():
    assert not (REPO / "ecosystem.config.template.js").exists()
