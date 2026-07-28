#!/usr/bin/env python3
"""Supply-chain audit gate (#342).

Consumes `pip-audit --format=json` and `npm audit --json` output and fails only
on advisories that are **not** already recorded in `security-baseline.json`.

Why a baseline instead of a bare `npm audit --audit-level=high`: the tree
already carried ~50 advisories when this gate landed (pillow, starlette,
python-multipart, postcss, sharp, ...), all needing major bumps. A plain gate
would have failed every PR from day one and been switched off within a week. The
baseline makes the existing backlog explicit and reviewable while still failing
CI the moment something *new* appears.

To adopt a new advisory into the baseline (i.e. accept it as known debt), add
its ID with a reason — or regenerate wholesale with --write-baseline.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

# npm severity ladder, lowest first. pip-audit reports no severity (PYSEC
# records frequently omit one), so every Python advisory counts.
NPM_SEVERITIES = ["info", "low", "moderate", "high", "critical"]

ECOSYSTEMS = ("pypi", "npm")

BASELINE_COMMENT = (
    "Known-and-accepted advisories as of #342. CI fails on anything NOT listed here, "
    "so this file is the repo's dependency-debt ledger, not an ignore-list to grow "
    "casually. Shrink it: each entry names its package and fix version. Regenerate "
    "wholesale with: python scripts/audit_gate.py --pip-audit <json> --npm-audit <json> "
    "--baseline security-baseline.json --write-baseline"
)


@dataclass(frozen=True)
class Finding:
    ecosystem: str
    id: str
    package: str
    severity: str
    fix: str


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Both tools report an advisory once per resolution path. Keep first seen."""
    seen: dict[tuple[str, str], Finding] = {}
    for f in findings:
        seen.setdefault((f.ecosystem, f.id), f)
    return list(seen.values())


def parse_pip_audit(report: dict) -> list[Finding]:
    findings = [
        Finding(
            ecosystem="pypi",
            id=vuln["id"],
            package=dep.get("name", "?"),
            severity="unknown",
            fix=", ".join(vuln.get("fix_versions") or []),
        )
        for dep in report.get("dependencies", [])
        for vuln in dep.get("vulns", [])
    ]
    return _dedupe(findings)


def _npm_advisory_id(via: dict, package: str) -> str:
    """Identify an npm advisory, never returning empty.

    Preference order is GHSA id, then npm's numeric `source`. An advisory we
    cannot identify still gets an id, because the alternative — dropping it —
    turns an unrecognised advisory into a passing build. Fail loud beats fail
    silent for a gate whose whole job is catching the unexpected.
    """
    url = via.get("url") or ""
    if "/advisories/" in url:
        return url.rstrip("/").rsplit("/", 1)[-1]
    if via.get("source"):
        return f"npm-source-{via['source']}"
    return f"npm-unidentified-{package}"


def parse_npm_audit(report: dict, min_severity: str = "high") -> list[Finding]:
    floor = NPM_SEVERITIES.index(min_severity)
    findings = []
    for package, entry in report.get("vulnerabilities", {}).items():
        for via in entry.get("via", []):
            # A string means "vulnerable via this other package"; the advisory
            # itself is recorded on that package, so skip it here.
            if not isinstance(via, dict):
                continue
            severity = via.get("severity", "")
            # Only a severity we recognise AND that sits below the floor is
            # skippable. Missing or unfamiliar severities are reported, so a
            # schema change cannot quietly filter advisories out of the gate.
            if severity in NPM_SEVERITIES and NPM_SEVERITIES.index(severity) < floor:
                continue
            findings.append(
                Finding(
                    ecosystem="npm",
                    id=_npm_advisory_id(via, package),
                    package=package,
                    severity=severity or "unknown",
                    fix="yes" if entry.get("fixAvailable") else "",
                )
            )
    return _dedupe(findings)


def load_baseline(path: Path) -> dict[str, dict[str, str]]:
    if not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text())
    return {eco: data[eco] for eco in ECOSYSTEMS if eco in data}


def evaluate(
    findings: list[Finding],
    baseline: dict[str, dict[str, str]],
    scanned_ecosystems: set[str] | None = None,
) -> tuple[list[Finding], list[tuple[str, str]]]:
    """Split findings into (not-in-baseline, baseline entries no longer seen).

    `scanned_ecosystems` must say which ecosystems were actually audited. Only
    claim an entry is resolved if we scanned its ecosystem — otherwise a
    pypi-only run would report every npm entry as fixed. It cannot be inferred
    from the findings: an ecosystem that came back completely clean produces no
    findings, yet that is exactly when its whole baseline section is prunable.
    """
    unbaselined = [f for f in findings if f.id not in baseline.get(f.ecosystem, {})]

    if scanned_ecosystems is None:
        scanned_ecosystems = {f.ecosystem for f in findings}
    live = {(f.ecosystem, f.id) for f in findings}
    resolved = [
        (eco, vuln_id)
        for eco, entries in baseline.items()
        if eco in scanned_ecosystems
        for vuln_id in entries
        if (eco, vuln_id) not in live
    ]
    return unbaselined, resolved


def _read(path: str | None, required_key: str) -> dict:
    """Load an audit report, failing closed if it lacks its top-level key.

    A killed or network-starved audit tool can leave behind valid JSON that
    simply has no results. Treating that as "no vulnerabilities" would turn a
    broken gate into a green check, so an absent key is an error rather than an
    empty scan. A genuinely clean run still emits the key (with an empty value).
    """
    if not path:
        return {}
    report = json.loads(Path(path).read_text())
    if required_key not in report:
        raise ValueError(
            f"{path}: missing expected key '{required_key}' — audit output looks truncated"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pip-audit", help="pip-audit --format=json output")
    parser.add_argument("--npm-audit", help="npm audit --json output")
    parser.add_argument("--baseline", required=True, help="security-baseline.json")
    parser.add_argument(
        "--min-severity",
        default="high",
        choices=NPM_SEVERITIES,
        help="npm severity floor (default: high). Python advisories always count.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Overwrite the baseline with everything currently found, then exit 0.",
    )
    args = parser.parse_args(argv)

    try:
        # JSONDecodeError is a ValueError, so malformed and truncated both land here.
        findings = parse_pip_audit(_read(args.pip_audit, "dependencies"))
        findings += parse_npm_audit(_read(args.npm_audit, "vulnerabilities"), args.min_severity)
    except (ValueError, OSError) as exc:
        print(f"FAIL — could not read audit output: {exc}")
        return 1

    scanned = {eco for eco, arg in (("pypi", args.pip_audit), ("npm", args.npm_audit)) if arg}

    if args.write_baseline:
        out: dict[str, object] = {"_comment": BASELINE_COMMENT}
        buckets: dict[str, dict[str, str]] = {eco: {} for eco in ECOSYSTEMS}
        out.update(buckets)
        for f in sorted(findings, key=lambda f: (f.ecosystem, f.id)):
            buckets[f.ecosystem][f.id] = f"{f.package}; fix: {f.fix or 'none available'}"
        Path(args.baseline).write_text(json.dumps(out, indent=2) + "\n")
        print(f"Wrote {sum(len(v) for v in buckets.values())} entries to {args.baseline}")
        return 0

    unbaselined, resolved = evaluate(findings, load_baseline(Path(args.baseline)), scanned)

    print(f"Scanned {len(findings)} advisories against {args.baseline}\n")

    if resolved:
        print("Resolved — prune these from the baseline:")
        for eco, vuln_id in sorted(resolved):
            print(f"  [{eco}] {vuln_id}")
        print()

    if not unbaselined:
        print(f"PASS — no new advisories ({len(findings)} known, already in the baseline).")
        return 0

    print(f"New advisories not in the baseline ({len(unbaselined)}):")
    for f in sorted(unbaselined, key=lambda f: (f.ecosystem, f.id)):
        print(f"  [{f.ecosystem}] {f.id}  {f.package}  severity={f.severity}  fix={f.fix or '-'}")
    print(
        "\nFAIL — fix these, or add each ID to the baseline with a reason "
        "if it is accepted debt."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
