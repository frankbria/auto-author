"""Guard: no operator-network identifiers in tracked files (#554).

This repository is PUBLIC. #544 scrubbed *staging infrastructure* identifiers; this
is the adjacent category the cross-family review on #553 turned up — the
**maintainer's own network**. A postmortem pasted a `ufw allow from <prefix>/24
to any port 22` line, a dynamic residential IP named alongside its ISP, and a
dynamic-DNS hostname. None of that is a credential. It is a public description of
which prefix was granted SSH, whose ISP serves it, and a *live* DNS pointer that
still resolves today — an attack-surface and personal-privacy problem rather than
an infrastructure one.

**The rules below name no operator value, deliberately.** A denylist guard for
this category would have to embed the very strings it exists to keep out of the
repo, re-committing them in the file that forbids them. So every rule matches on
*shape and surrounding words* instead: a firewall grant, a dynamic-DNS vendor
domain, an address described as somebody's home connection.

A blanket public-IPv4 rule was considered and rejected in #553, and #554 confirmed
why: this repo's `frontend/public/*.svg` path data contains digit runs that parse
as IPv4, and there are ~88 tracked references to a decommissioned host. A rule
that noisy gets switched off, which is worse than not having it. Each rule here
requires an IP *plus* context, so none of that fires.
"""

import ipaddress
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SELF = "scripts/test_no_operator_network_identifiers.py"

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# A firewall grant naming a source address. This is the one that says something
# about the operator's network rather than about a machine.
UFW_GRANT = re.compile(r"(?:ufw\s+)?allow\s+from\s+(\d{1,3}(?:\.\d{1,3}){3})", re.I)

# Consumer dynamic-DNS providers. A hostname here is a live pointer at whatever
# connection it was set up for — it keeps resolving long after an IP goes stale.
#
# Naming vendors is not a disclosure: the secret in `<random>.<vendor>.com` is the
# subdomain, not the provider, and this is a general list of eight rather than a
# statement about anyone. The fixtures below use `abc123` for the same reason.
# Test samples must never carry a real operator value — an ISP name in a fixture
# reintroduces exactly what the rule removes.
DDNS = re.compile(
    r"\b[a-z0-9][a-z0-9-]*\.(?:glddns|ddns|dyndns|no-ip|noip|duckdns|afraid|"
    r"changeip|freedns)\.(?:com|net|org|info)\b",
    re.I,
)

# An address explicitly described as somebody's home/office connection.
PERSONAL = re.compile(r"\b(?:dynamic|home|office|residential|personal)\b[^\n]{0,40}\bip\b", re.I)

# How close that description must sit to the address. A whole-line AND is too
# loose: a CHANGELOG entry here is one 3000-character line, so prose *about* this
# guard ("a 14-month-old dynamic IP is near-certainly reassigned") would match a
# placeholder address mentioned paragraphs away. The relationship the rule means
# is proximity — "the dynamic IP (x.x.x.x)" — not co-occurrence.
PERSONAL_PROXIMITY = 60


def _is_public(text):
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_unspecified
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_link_local
    )


def _tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split("\n")
    for rel in out:
        if not rel or rel == SELF:
            continue
        path = REPO / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        yield rel, path


def _scan(predicate):
    """Yield `path:line -> line` for every tracked line the predicate accepts."""
    hits = []
    for rel, path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if predicate(line):
                hits.append(f"{rel}:{lineno}")
    return hits


def test_there_are_files_to_scan():
    """Without this, a broken `git ls-files` turns every rule below green.

    A guard that silently checks nothing is worse than no guard: the passing
    check is read as evidence that the thing it names cannot happen.
    """
    files = list(_tracked_text_files())
    assert len(files) > 50, f"only {len(files)} tracked files found — scan is broken"


def test_no_firewall_grant_names_a_source_address():
    hits = _scan(lambda ln: any(_is_public(m) for m in UFW_GRANT.findall(ln)))
    assert not hits, (
        "A firewall rule in a tracked file names a public source address:\n"
        + "\n".join(hits)
        + "\n\nThis is a public statement about which network was granted SSH, which "
        "is about the operator rather than about a server. Replace the address with "
        "`<operator-network>` and keep the line readable."
    )


def test_no_dynamic_dns_hostname():
    hits = _scan(lambda ln: bool(DDNS.search(ln)))
    assert not hits, (
        "A consumer dynamic-DNS hostname is present in a tracked file:\n"
        + "\n".join(hits)
        + "\n\nUnlike a stale IP this still resolves, so it is a live pointer at the "
        "connection it was set up for. Replace it with `<operator-ddns>`."
    )


def _personal_ip_on(line):
    """True when a public IP sits within PERSONAL_PROXIMITY chars of the description."""
    spans = [m.span() for m in PERSONAL.finditer(line)]
    if not spans:
        return False
    for m in IPV4.finditer(line):
        if not _is_public(m.group()):
            continue
        a, b = m.span()
        for x, y in spans:
            if max(a, x) - min(b, y) <= PERSONAL_PROXIMITY:
                return True
    return False


def test_no_public_ip_described_as_a_personal_connection():
    hits = _scan(_personal_ip_on)
    assert not hits, (
        "A public IP sits on a line describing it as a home/office/dynamic address:\n"
        + "\n".join(hits)
        + "\n\nThe address plus that description identifies the maintainer's own "
        "connection. Replace it with `<operator-ip>` and drop any ISP name beside it."
    )


@pytest.mark.parametrize(
    ("sample", "pattern", "rule"),
    [
        ("ufw allow from 203.0.113.42/24 to any port 22", UFW_GRANT, "firewall grant"),
        ("User has DDNS (abc123.glddns.com) but UFW is unreliable", DDNS, "dynamic-dns"),
        ("Attempted to use the home dynamic IP (203.0.113.7) - not stable", PERSONAL, "personal ip"),
    ],
)
def test_each_pattern_matches_the_shape_it_claims_to(sample, pattern, rule):
    """The rules are only meaningful if they fire on the real thing.

    Samples use RFC 5737 documentation addresses so the guard's own fixtures can
    never be a disclosure. Note these test the REGEX only — `_is_public` rejects
    documentation ranges, which is why the shape and the address check are pinned
    separately below rather than together. Without this, a regex typo would leave
    every rule above passing forever on a repo it no longer inspects.
    """
    assert pattern.search(sample), f"{rule!r} pattern no longer matches: {sample!r}"


@pytest.mark.parametrize(
    ("address", "public"),
    [
        ("8.8.8.8", True),          # a real routable address: the case that must fail the scan
        ("203.0.113.7", False),     # RFC 5737 TEST-NET-3, the documentation placeholder
        ("192.0.2.1", False),       # RFC 5737 TEST-NET-1
        ("10.0.0.5", False),        # RFC 1918
        ("127.0.0.1", False),
        ("0.0.0.0", False),         # `ufw ... from 0.0.0.0/0` means "anywhere", not a network
        ("169.254.1.1", False),     # link-local
        ("not.an.ip.x", False),
    ],
)
def test_only_routable_addresses_count_as_a_disclosure(address, public):
    """Documentation and private ranges must not trip the scan.

    This is what lets the rules above stay strict without going noisy: a doc
    example, an RFC 1918 address or `0.0.0.0/0` in a firewall snippet says
    nothing about anyone's network, and a guard that flagged them would be
    switched off within a week.
    """
    assert _is_public(address) is public
