"""Guard: no live staging infrastructure identifiers in tracked files (#544).

This repository is PUBLIC. #544 found a database username sitting in one string
with its managed-cluster hostname — no password (that was masked), but half a
credential plus the name of a specific principal to attack, with the discovery
step removed. Scrubbing the working tree does not remove it from history, so the
value of this guard is preventing the NEXT one, not undoing that one.

Deliberately narrow, because a noisy rule gets deleted: this repo already removed
`detect-private-key` from pre-commit for false positives. So the pattern is a
managed-cluster hostname (`*.mongodb.net`), which has no legitimate reason to be
literal in a public repo, and every known documentation example is allowlisted
below by its exact value rather than by a fuzzy "looks like a placeholder" rule.

The staging host's *IP* is deliberately NOT matched. #544 calibrated it as close
to zero marginal risk (`dev.autoauthor.app` resolves to it), and a public-IPv4
rule would fire on version strings, RFC 5737 test addresses and the 88 tracked
references to the previous provider's now-dead host — the exact noise that gets a
check switched off.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Documentation examples that are allowed to contain a mongodb.net hostname.
# Exact hostnames, so a REAL cluster appearing in these same files still fails.
ALLOWED_HOSTS = {
    # The #211 test-db-guard fixture and its demo. Obviously synthetic, and the
    # fixture's whole job is to be a remote srv URI the guard must refuse.
    "cluster0.abcde.mongodb.net",
}

ATLAS = re.compile(r"\b[a-z0-9][a-z0-9-]*\.[a-z0-9-]+\.mongodb\.net\b", re.I)
SKIP_PREFIXES = ("frontend/playwright-report/", "frontend/tests/e2e/staging/playwright-report-staging/")


def _tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split("\n")
    for rel in out:
        if not rel or rel.startswith(SKIP_PREFIXES) or rel == "scripts/test_no_staging_identifiers.py":
            continue
        p = REPO / rel
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        yield rel, p


def test_no_live_cluster_hostname_in_tracked_files():
    offenders = []
    for rel, path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for host in ATLAS.findall(line):
                if host.lower() not in ALLOWED_HOSTS:
                    offenders.append(f"{rel}:{lineno} -> {host}")
    assert not offenders, (
        "A managed-cluster hostname is present in a tracked file of a PUBLIC repo.\n"
        + "\n".join(offenders)
        + "\n\nReplace it with `<cluster-host>` (and any username with `<db-user>`). "
        "If it is genuinely a documentation example, add the exact hostname to "
        "ALLOWED_HOSTS above with a comment saying which file it serves. Do not "
        "widen the pattern -- the point is that a real cluster name cannot pass."
    )


@pytest.mark.parametrize("host", sorted(ALLOWED_HOSTS))
def test_allowlisted_hosts_are_still_referenced(host):
    """An allowlist entry that no longer matches anything is a latent hole.

    It would silently permit that exact hostname forever. If this fails, the
    example moved or was deleted -- drop the entry rather than keeping it.
    """
    hits = subprocess.run(
        ["git", "grep", "-lF", host], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    assert hits, f"ALLOWED_HOSTS entry {host!r} matches no tracked file; remove it."
