# Demo — #554 Scrub the operator's own network from a public repo

**Date:** 2026-09-06 · **Branch:** `feature/554-scrub-operator-network`

The issue supplied a five-location table. **It was wrong in both directions**, so the scan was
redone from scratch rather than worked through as a checklist. That is the substance of this
document.

---

## The sweep

```bash
git grep -hoE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | sort | uniq -c | sort -rn
```

Eight distinct non-private IPv4-shaped strings across tracked files, classified by reading the
line each sits on:

| | count | what it actually is | in scope? |
|---|---:|---|---|
| A | 88 | the decommissioned ClawCloud host | no — see below |
| B, F, G | 1 each | **not IP addresses** — coordinate runs in `frontend/public/{window,next,globe}.svg` path data | no |
| C | 1 | the operator's dynamic residential IP, named beside its ISP | **yes** |
| D | 1 | the `/24` prefix granted SSH in a `ufw` rule | **yes** |
| E | 1 | an address in a webhook access log — **AWS eu-west-1, i.e. Clerk's own egress** | yes, but not for the stated reason |
| H | 1 | `1.2.3.4` — the canonical documentation placeholder | **no, nothing to scrub** |

## Where the issue was wrong

**Over-reported, twice.**

`tasks/lessons.md` was listed as disclosing "client IP in a uvicorn access-log excerpt". The value
is `1.2.3.4`. It is a placeholder and was already one. No change made.

`docs/fixes/2025-11-22-clerk-webhook-nginx-fix.md:20` was listed as "client IP in a verbatim
access-log excerpt". That address resolves to AWS eu-west-1 — it is **Clerk's webhook sender**, not the
operator's connection, so it is not the category this issue is about. Scrubbed anyway, because a
third party's egress address in a verbatim log is noise with no documentary value, but the
rationale is corrected here so the next reader is not misled about what was exposed.

**Under-reported, and this is the one that matters.**

`docs/INCIDENT-2025-10-19-firewall-lockout.md:47` carries a **consumer dynamic-DNS hostname**. The
issue's table does not list it. It is the most exposing line in the file, and by a clear margin:

> Everything else in that document is a snapshot from 2025-10-19. A dynamic residential IP from
> fourteen months ago has almost certainly been reassigned. **A DDNS hostname still resolves** —
> it is a live pointer at whatever connection it was set up for, today, for anyone who reads the
> repo.

The issue's own severity note leans on staleness ("near-certainly reassigned", "a provider that
has since been retired"). That argument does not apply to the item it missed.

Line `:160` also names the ISP a second time; the table lists only `:46`.

## What changed

| file:line | before | after |
|---|---|---|
| `INCIDENT…:6` | former provider's prod host | `` `<former-prod-host>` `` |
| `INCIDENT…:21` | `ufw allow from <prefix>/24 to any port 22` | `` `<operator-network>/24` `` |
| `INCIDENT…:46` | ISP name + dynamic IP | "a dynamic residential IP (`<operator-ip>`)" |
| `INCIDENT…:47` | DDNS hostname | "a dynamic-DNS hostname (`<operator-ddns>`)" |
| `INCIDENT…:160` | ISP name | "residential ISPs" |
| `clerk-webhook-nginx-fix…:20` | Clerk's AWS egress IP | `<clerk-webhook-source>` |
| `tasks/lessons.md` | — | **unchanged**, the value was already `1.2.3.4` |

Verified gone repo-wide, not just at the listed lines:

Each scrubbed value was grepped for by its literal across all tracked files, and all four came
back with no match. **The commands are not reproduced here with their arguments filled in** — a
verification block that pastes the values would reintroduce them in the document claiming they
are gone, and would falsify its own result on the next run:

| value | result |
|---|---|
| the residential IP, and its `/24` prefix | no match |
| the dynamic-DNS hostname | no match |
| the ISP name | no match |
| the Clerk egress address | no match |

To re-run it, take the four literals from this branch's parent commit
(`git show HEAD~1:docs/INCIDENT-2025-10-19-firewall-lockout.md`) and `git grep -F` each against
the current tree.

## The one thing deliberately not done

**87 of the 88 references to the decommissioned host remain.** The issue asked for `:6` to be
replaced with `<former-prod-host>`, and it was — but that is cosmetic consistency within one
document, **not a reduction in exposure**, and it should not be read as one. Scrubbing 1 of 88 is
theatre; the honest options are all or none.

None is defensible here: the machine is decommissioned, at a provider that has been retired, and
the address appears mostly in `archive/` and `claudedocs/` historical documents that CLAUDE.md
treats as read-only. All 88 would be a large mechanical diff across historical files for an
address that routes to nothing. **If that trade should go the other way, it is a separate
decision** — flagged on the issue rather than silently made here.

## The guard

`scripts/test_no_operator_network_identifiers.py`, in the `Security Audit` job. Three rules, each
requiring an IP **plus** context: a firewall grant naming a source address, a consumer
dynamic-DNS hostname, and a public IP on a line describing it as a home/office/dynamic address.

**No rule names an operator value.** A denylist for this category would have to embed the very
strings it exists to keep out of the repo, re-committing them in the file that forbids them. The
fixtures use RFC 5737 documentation addresses.

A blanket public-IPv4 rule stays rejected, and the sweep above is the evidence: it would fire on
three SVG files and 88 references to a dead host. A check that noisy gets switched off.

### Mutation checks (guard staged first)

| probe | result |
|---|---|
| `ufw allow from <real /24> to any port 22` | ❌ `test_no_firewall_grant_names_a_source_address` |
| a `<subdomain>.<ddns-vendor>.com` hostname | ❌ `test_no_dynamic_dns_hostname` |
| "home dynamic IP (`<real ip>`)" | ❌ `test_no_public_ip_described_as_a_personal_connection` |
| the same `ufw` line with an RFC 5737 address | ✅ passes — documentation examples must not trip it |
| SVG path data with IPv4-shaped digit runs | ✅ passes — the false positive that killed the blanket rule |
| the same description with the address paragraphs away | ✅ passes — see *proximity* below |
| `1.2.3.4` in an access-log excerpt | ✅ passes — no personal-connection wording near it |
| `git ls-files` repointed at nothing | ❌ `test_there_are_files_to_scan` |

The must-not-fire rows matter as much as the must-fire ones. A guard that only proves it *fires* has not
shown it is usable; one that fires on documentation examples and SVG coordinates gets disabled,
at which point it protects nothing while still reading as protection.

**The guard caught me writing this document, and that found a real bug in it.** The first draft
of the CHANGELOG entry below restated the Clerk egress address verbatim while describing the
scrub — re-committing, in the changelog, a value the same commit removes. That is the failure the
guard's docstring warns about, arriving immediately and from the direction I was not watching.

Fixing the text then exposed a genuine flaw in the third rule. It ANDed *an IP anywhere on the
line* with *a personal-connection phrase anywhere on the line*, and a CHANGELOG entry in this repo
is a single 3000-character line — so prose **about** the guard ("a 14-month-old dynamic IP is
near-certainly reassigned") matched the `1.2.3.4` placeholder mentioned paragraphs earlier. The
rule now requires the two within 60 characters, which is the relationship it always meant: *"the
dynamic IP (x.x.x.x)"*, not mere co-occurrence. Both new must-not-fire rows above pin that.

Worth stating plainly, because it cuts against the reflex: **the fix was to tighten the rule, not
to allowlist the file.** An exclusion for `docs/CHANGELOG.md` would have made this green in one
line and left the rule wrong for every other long-line file.

**And it happened a third time, in this same file, past both the guard and me.** The
verification block above originally pasted the grep commands with their arguments — reintroducing
the `/24` prefix and the ISP name in the document asserting they were gone, which also made the
claim self-falsifying: a fresh `git grep` would now match this file. Caught by
`codex review --base main`, not by the guard.

**The guard could not have caught it, and that is worth knowing.** The prefix was written as
three octets, which no IPv4 pattern matches, and the ISP name is a bare word no shape rule can
distinguish from prose. Shape-based rules catch shapes; a *partial* value and a proper noun both
slip through. So the guard lowers the floor — it stops the obvious paste — but the review step is
load-bearing for this category, and the pattern is specific: **the highest-risk place to
reintroduce a scrubbed value is the document explaining the scrub.** Three separate attempts in
one commit, all in prose about the work rather than in the work itself.

**A fourth instance, found while fixing the third.** The guard's own *fixture* named the real
ISP — `("Attempted to use Cox dynamic IP …")` — so the file forbidding the disclosure contained
it. Changed to "the home dynamic IP". A test sample must never carry a real operator value, which
is now stated in the module comment.

The DDNS vendor name does stay, in the rule's pattern and one fixture, and that is deliberate:
the secret in `<random>.<vendor>.com` is the subdomain, not the provider. The list names eight
consumer providers, so it is a general pattern rather than a statement about anyone — and the
rule cannot work without naming what it matches.

**The guard's own fixture test caught a second subtlety.** The first draft asserted the three rules
end-to-end using RFC 5737 sample addresses — and failed, because `_is_public()` correctly rejects
documentation ranges. Right behaviour, wrong fixture. The assertions are now split: one test pins
the regex *shapes*, another pins which addresses count as routable at all
(`8.8.8.8` yes; `203.0.113.7`, `192.0.2.1`, `10.0.0.5`, `0.0.0.0`, `169.254.1.1` no).

## Acceptance criteria

| Criterion | Evidence | |
|---|---|---|
| Replace with `<operator-network>` / `<client-ip>` / `<former-prod-host>`, docs still readable | Table above; six replacements across two files | ✅ |
| Remove the ISP name where it sits alongside an address | Both occurrences (`:46`, `:160`) — the issue listed one | ✅ |
| Decide whether `test_no_staging_identifiers.py` should grow a rule | **No** — kept separate. That guard is a hostname-shape rule with an exact-value allowlist; these are context rules with no allowlist. Merging them would blur two different matching strategies into one file | ✅ |
| A narrower rule "may be worth it"; a blanket one is not | Built the narrow one, three rules; blanket rule stays rejected with the sweep as evidence | ✅ |
| History rewriting out of scope | Not done. Same reasoning as #544 — the values are in every clone of a public repo | ✅ |
