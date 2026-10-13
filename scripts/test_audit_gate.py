"""Tests for the supply-chain audit gate (#342).

Run standalone (the gate is not part of the app package, so it stays out of the
backend coverage denominator):

    uvx --with pytest pytest scripts/test_audit_gate.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from audit_gate import (  # noqa: E402
    Finding,
    evaluate,
    load_baseline,
    main,
    parse_npm_audit,
    parse_pip_audit,
)


# --- pip-audit parsing -------------------------------------------------------


def test_parse_pip_audit_extracts_each_vuln():
    report = {
        "dependencies": [
            {
                "name": "pillow",
                "version": "11.3.0",
                "vulns": [
                    {"id": "PYSEC-2026-2255", "fix_versions": ["12.3.0"]},
                    {"id": "PYSEC-2026-3451", "fix_versions": ["12.3.0"]},
                ],
            },
            {"name": "fastapi", "version": "0.139.0", "vulns": []},
        ]
    }

    findings = parse_pip_audit(report)

    assert {f.id for f in findings} == {"PYSEC-2026-2255", "PYSEC-2026-3451"}
    assert all(f.ecosystem == "pypi" for f in findings)
    assert findings[0].package == "pillow"
    assert findings[0].fix == "12.3.0"


def test_parse_pip_audit_handles_no_fix_version():
    report = {"dependencies": [{"name": "x", "version": "1", "vulns": [{"id": "PYSEC-1"}]}]}

    assert parse_pip_audit(report)[0].fix == ""


def test_parse_pip_audit_dedupes_repeated_ids():
    """pip-audit lists a package once per resolution path, so the same advisory
    can appear twice (observed for pyasn1/starlette)."""
    report = {
        "dependencies": [
            {"name": "starlette", "version": "0.47.2", "vulns": [{"id": "PYSEC-2026-161"}]},
            {"name": "starlette", "version": "0.47.2", "vulns": [{"id": "PYSEC-2026-161"}]},
        ]
    }

    assert len(parse_pip_audit(report)) == 1


# --- npm audit parsing -------------------------------------------------------


def _npm_report(**vulns):
    return {"auditReportVersion": 2, "vulnerabilities": vulns}


def test_parse_npm_audit_extracts_ghsa_from_advisory_url():
    report = _npm_report(
        postcss={
            "name": "postcss",
            "severity": "high",
            "via": [
                {
                    "source": 1104189,
                    "name": "postcss",
                    "title": "PostCSS has XSS",
                    "url": "https://github.com/advisories/GHSA-qx2v-qp2m-jg93",
                    "severity": "high",
                }
            ],
        }
    )

    findings = parse_npm_audit(report)

    assert len(findings) == 1
    assert findings[0].id == "GHSA-qx2v-qp2m-jg93"
    assert findings[0].ecosystem == "npm"
    assert findings[0].package == "postcss"
    assert findings[0].severity == "high"


def test_parse_npm_audit_ignores_string_via_entries():
    """A string in `via` means "vulnerable through this other package" — the
    advisory itself is recorded on that package, so counting it here would
    double-report."""
    report = _npm_report(
        **{
            "react-router-dom": {
                "name": "react-router-dom",
                "severity": "high",
                "via": ["react-router"],
            }
        }
    )

    assert parse_npm_audit(report) == []


def test_parse_npm_audit_filters_below_threshold():
    report = _npm_report(
        low_pkg={
            "name": "low_pkg",
            "severity": "low",
            "via": [{"url": "https://github.com/advisories/GHSA-low", "severity": "low"}],
        },
        mid_pkg={
            "name": "mid_pkg",
            "severity": "moderate",
            "via": [{"url": "https://github.com/advisories/GHSA-mid", "severity": "moderate"}],
        },
        bad_pkg={
            "name": "bad_pkg",
            "severity": "critical",
            "via": [{"url": "https://github.com/advisories/GHSA-bad", "severity": "critical"}],
        },
    )

    # The default floor is moderate since #820; it was high, which hid GHSA-mid.
    assert {f.id for f in parse_npm_audit(report)} == {"GHSA-mid", "GHSA-bad"}
    assert {f.id for f in parse_npm_audit(report, min_severity="high")} == {"GHSA-bad"}
    assert {f.id for f in parse_npm_audit(report, min_severity="low")} == {
        "GHSA-low",
        "GHSA-mid",
        "GHSA-bad",
    }


def test_parse_npm_audit_dedupes_advisory_across_packages():
    """npm reports the same advisory once per install path (postcss appears
    under both `postcss` and `next/node_modules/postcss`)."""
    advisory = {"url": "https://github.com/advisories/GHSA-dup", "severity": "high"}
    report = _npm_report(
        a={"name": "a", "severity": "high", "via": [advisory]},
        b={"name": "b", "severity": "high", "via": [advisory]},
    )

    assert len(parse_npm_audit(report)) == 1


def test_parse_npm_audit_empty_report():
    assert parse_npm_audit(_npm_report()) == []


def test_parse_npm_audit_falls_back_to_source_id_without_a_url():
    """An advisory object with no `url` must NOT vanish — dropping it would be a
    false green. npm always carries a numeric `source`, so key off that."""
    report = _npm_report(
        x={
            "name": "x",
            "severity": "critical",
            "via": [{"source": 123456, "title": "RCE", "severity": "critical"}],
        }
    )

    findings = parse_npm_audit(report)

    assert [f.id for f in findings] == ["npm-source-123456"]


def test_parse_npm_audit_keeps_an_unidentifiable_advisory():
    """No url and no source: still must not disappear. It surfaces with a
    package-derived id so the gate fails loudly instead of silently passing."""
    report = _npm_report(x={"name": "x", "severity": "high", "via": [{"severity": "high"}]})

    findings = parse_npm_audit(report)

    assert len(findings) == 1
    assert "unidentified" in findings[0].id
    assert findings[0].package == "x"


def test_parse_npm_audit_keeps_advisories_with_missing_severity():
    """Absent severity must fail loud, not be treated as below the floor."""
    report = _npm_report(
        x={"name": "x", "severity": "high", "via": [{"url": ".../advisories/GHSA-x"}]}
    )

    assert [f.id for f in parse_npm_audit(report)] == ["GHSA-x"]


def test_parse_npm_audit_keeps_advisories_with_unrecognised_severity():
    report = _npm_report(
        x={
            "name": "x",
            "severity": "high",
            "via": [{"url": ".../advisories/GHSA-x", "severity": "apocalyptic"}],
        }
    )

    assert [f.id for f in parse_npm_audit(report)] == ["GHSA-x"]


# --- evaluation --------------------------------------------------------------


def _finding(id_, ecosystem="npm"):
    return Finding(ecosystem=ecosystem, id=id_, package="p", severity="high", fix="")


def test_evaluate_flags_unbaselined_findings():
    baseline = {"npm": {"GHSA-known": "tracked"}}

    unbaselined, resolved = evaluate([_finding("GHSA-known"), _finding("GHSA-new")], baseline)

    assert [f.id for f in unbaselined] == ["GHSA-new"]
    assert resolved == []


def test_evaluate_reports_resolved_baseline_entries():
    baseline = {"npm": {"GHSA-known": "tracked", "GHSA-fixed": "already bumped"}}

    unbaselined, resolved = evaluate([_finding("GHSA-known")], baseline)

    assert unbaselined == []
    assert resolved == [("npm", "GHSA-fixed")]


def test_evaluate_keeps_ecosystems_separate():
    """A pypi ID must not be silenced by an identically-named npm entry."""
    baseline = {"npm": {"SHARED-ID": "npm only"}}

    unbaselined, _ = evaluate([_finding("SHARED-ID", ecosystem="pypi")], baseline)

    assert [f.id for f in unbaselined] == ["SHARED-ID"]


def test_evaluate_reports_stale_entries_when_an_ecosystem_goes_fully_clean():
    """The happy ending — every npm advisory fixed. Inferring "scanned" from the
    findings would report nothing here, silently stranding 53 dead entries."""
    baseline = {"npm": {"GHSA-fixed": "was debt"}}

    _, resolved = evaluate([], baseline, scanned_ecosystems={"npm"})

    assert resolved == [("npm", "GHSA-fixed")]


def test_evaluate_does_not_report_unscanned_ecosystems_as_resolved():
    baseline = {"npm": {"GHSA-untouched": "still debt"}}

    _, resolved = evaluate([], baseline, scanned_ecosystems={"pypi"})

    assert resolved == []


def test_evaluate_tolerates_missing_ecosystem_key():
    unbaselined, resolved = evaluate([_finding("GHSA-new")], {})

    assert [f.id for f in unbaselined] == ["GHSA-new"]
    assert resolved == []


# --- baseline loading --------------------------------------------------------


def test_load_baseline_missing_file_is_empty(tmp_path):
    assert load_baseline(tmp_path / "nope.json") == {}


def test_load_baseline_reads_ecosystem_maps(tmp_path):
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"npm": {"GHSA-a": "why"}, "pypi": {"PYSEC-b": "why"}}))

    assert load_baseline(path) == {"npm": {"GHSA-a": "why"}, "pypi": {"PYSEC-b": "why"}}


def test_load_baseline_ignores_comment_keys(tmp_path):
    """`_comment` documents the file for humans; it is not an ecosystem."""
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"_comment": "read me", "npm": {"GHSA-a": "why"}}))

    assert load_baseline(path) == {"npm": {"GHSA-a": "why"}}


# --- end to end --------------------------------------------------------------


@pytest.fixture
def audit_files(tmp_path):
    pip = tmp_path / "pip.json"
    npm = tmp_path / "npm.json"
    baseline = tmp_path / "baseline.json"
    pip.write_text(
        json.dumps(
            {"dependencies": [{"name": "pillow", "version": "11.3.0", "vulns": [{"id": "PYSEC-1"}]}]}
        )
    )
    npm.write_text(
        json.dumps(
            _npm_report(
                postcss={
                    "name": "postcss",
                    "severity": "high",
                    "via": [
                        {"url": "https://github.com/advisories/GHSA-1", "severity": "high"}
                    ],
                }
            )
        )
    )
    return pip, npm, baseline


def test_main_passes_when_everything_is_baselined(audit_files, capsys):
    pip, npm, baseline = audit_files
    baseline.write_text(json.dumps({"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": "why"}}))

    rc = main(["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)])

    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_main_fails_on_a_new_advisory(audit_files, capsys):
    pip, npm, baseline = audit_files
    baseline.write_text(json.dumps({"pypi": {"PYSEC-1": "why"}}))

    rc = main(["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "GHSA-1" in out
    assert "PYSEC-1" not in out.split("New advisories")[1]


def test_main_a_resolved_entry_fails_the_build_until_it_is_pruned(audit_files, capsys):
    """#821. It used to be reported and passed. An entry for an advisory that is gone stays an
    exemption for that id: the day a downgrade brings the advisory back, the gate says nothing."""
    pip, npm, baseline = audit_files
    baseline.write_text(
        json.dumps(
            {"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": "why", "GHSA-gone": "already fixed"}}
        )
    )

    rc = main(["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "GHSA-gone" in out and "prune" in out.lower()
    assert "PASS" not in out


def test_main_an_entry_for_an_ecosystem_that_was_not_scanned_is_not_called_resolved(audit_files, capsys):
    pip, _, baseline = audit_files
    baseline.write_text(json.dumps({"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": "why"}}))

    rc = main(["--pip-audit", str(pip), "--baseline", str(baseline)])

    assert rc == 0, capsys.readouterr().out


@pytest.mark.parametrize("reason", ["", "   ", None, 7, ["a list is not a reason"]])
def test_main_an_entry_without_a_reason_fails_the_build(audit_files, capsys, reason):
    """#821. An id with nothing beside it is an ignore-list. The reason is what lets the next
    reader decide whether the entry still holds."""
    pip, npm, baseline = audit_files
    baseline.write_text(json.dumps({"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": reason}}))

    rc = main(["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "GHSA-1" in out and "reason" in out.lower()
    assert "PASS" not in out


def test_main_a_reason_is_required_even_for_an_ecosystem_that_was_not_scanned(audit_files, capsys):
    pip, _, baseline = audit_files
    baseline.write_text(json.dumps({"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": ""}}))

    rc = main(["--pip-audit", str(pip), "--baseline", str(baseline)])

    assert rc == 1
    assert "GHSA-1" in capsys.readouterr().out


def test_main_runs_with_only_one_ecosystem(tmp_path, capsys):
    pip = tmp_path / "pip.json"
    pip.write_text(json.dumps({"dependencies": []}))

    rc = main(["--pip-audit", str(pip), "--baseline", str(tmp_path / "absent.json")])

    assert rc == 0


def test_main_rejects_a_truncated_pip_report(tmp_path, capsys):
    """A crashed/killed audit tool can leave valid-JSON-but-empty output. Passing
    that would be a false green, so the gate fails closed."""
    bad = tmp_path / "pip.json"
    bad.write_text("{}")

    rc = main(["--pip-audit", str(bad), "--baseline", str(tmp_path / "b.json")])

    assert rc == 1
    assert "missing expected key" in capsys.readouterr().out


def test_main_rejects_a_truncated_npm_report(tmp_path, capsys):
    bad = tmp_path / "npm.json"
    bad.write_text('{"auditReportVersion": 2}')

    rc = main(["--npm-audit", str(bad), "--baseline", str(tmp_path / "b.json")])

    assert rc == 1
    assert "missing expected key" in capsys.readouterr().out


def test_main_accepts_a_genuinely_clean_report(tmp_path, capsys):
    """A clean audit still carries its top-level key — that must pass, not trip
    the fail-closed guard."""
    pip = tmp_path / "pip.json"
    npm = tmp_path / "npm.json"
    pip.write_text(json.dumps({"dependencies": []}))
    npm.write_text(json.dumps({"vulnerabilities": {}}))

    rc = main(
        ["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(tmp_path / "b.json")]
    )

    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_main_write_baseline_emits_current_findings(audit_files, tmp_path):
    pip, npm, baseline = audit_files

    rc = main(
        [
            "--pip-audit",
            str(pip),
            "--npm-audit",
            str(npm),
            "--baseline",
            str(baseline),
            "--write-baseline",
        ]
    )

    assert rc == 0
    written = json.loads(baseline.read_text())
    assert "PYSEC-1" in written["pypi"]
    assert "GHSA-1" in written["npm"]


def test_writing_the_baseline_keeps_the_reasons_already_written_and_invents_none(audit_files, capsys):
    """#821. It used to overwrite every entry with "<package>; fix: …": the reasons someone had
    written were lost, and what replaced them was not a reason. A new entry is written with no
    reason, which the gate then refuses until a person supplies one."""
    pip, npm, baseline = audit_files
    baseline.write_text(json.dumps({"_comment": "the ledger", "pypi": {"PYSEC-1": "test-only, see #1"}, "npm": {}}))
    args = ["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)]

    assert main(args + ["--write-baseline"]) == 0

    written = json.loads(baseline.read_text())
    assert written["_comment"] == "the ledger"
    assert written["pypi"] == {"PYSEC-1": "test-only, see #1"}
    assert written["npm"] == {"GHSA-1": ""}
    capsys.readouterr()
    assert main(args) == 1
    assert "GHSA-1" in capsys.readouterr().out


# --- the severity floor (#820) -----------------------------------------------
#
# The floor was `high`, so a moderate advisory in the frontend's tree was never
# reported: not baselined with a reason, not a failure, simply unseen. dompurify's
# DOM XSS (low) and fast-uri (moderate) both sat below it until Dependabot moved
# them. The gate now starts at `moderate`.

REPO = Path(__file__).resolve().parent.parent


def _npm_file(tmp_path, **severity_by_id):
    """An `npm audit --json` document with one advisory per keyword: GHSA_x="moderate"."""
    npm = tmp_path / "npm.json"
    npm.write_text(
        json.dumps(
            _npm_report(
                **{
                    f"package-{ghsa}": {
                        "name": f"package-{ghsa}",
                        "severity": severity,
                        "via": [{"url": f"https://github.com/advisories/{ghsa}", "severity": severity}],
                    }
                    for ghsa, severity in severity_by_id.items()
                }
            )
        )
    )
    return npm


def test_a_moderate_advisory_fails_the_gate_without_any_flag(tmp_path, capsys):
    npm = _npm_file(tmp_path, GHSA_moderate="moderate")
    baseline = tmp_path / "baseline.json"

    rc = main(["--npm-audit", str(npm), "--baseline", str(baseline)])

    assert rc == 1
    assert "GHSA_moderate" in capsys.readouterr().out


def test_a_low_advisory_is_still_below_the_floor(tmp_path, capsys):
    npm = _npm_file(tmp_path, GHSA_low="low", GHSA_info="info")
    baseline = tmp_path / "baseline.json"

    rc = main(["--npm-audit", str(npm), "--baseline", str(baseline)])

    assert rc == 0
    assert "GHSA_low" not in capsys.readouterr().out


def test_writing_the_baseline_keeps_its_moderate_entries(tmp_path):
    """The file's own header says to regenerate it with --write-baseline. Written at a floor
    above the one CI checks at, it would drop every moderate entry and CI would fail on them."""
    npm = _npm_file(tmp_path, GHSA_moderate="moderate", GHSA_high="high")
    baseline = tmp_path / "baseline.json"

    main(["--npm-audit", str(npm), "--baseline", str(baseline), "--write-baseline"])

    assert set(json.loads(baseline.read_text())["npm"]) == {"GHSA_moderate", "GHSA_high"}


def _gate_command_in_ci():
    import yaml

    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "tests.yml").read_text())
    scripts = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps") or []
        if "audit_gate.py" in str(step.get("run", "")) and "--npm-audit" in str(step.get("run", ""))
    ]
    assert len(scripts) == 1, f"expected one step that runs the gate on npm's report, found {len(scripts)}"
    return scripts[0]


def test_ci_runs_the_gate_at_the_moderate_floor():
    import re

    floors = re.findall(r"--min-severity[ =](\S+)", _gate_command_in_ci())

    assert floors == ["moderate"], f"the gate in tests.yml runs with floors {floors}"


def test_every_entry_in_the_real_baseline_says_why():
    """An id with no reason is an ignore-list. The reason is what lets the next reader prune it."""
    baseline = json.loads((REPO / "security-baseline.json").read_text())
    entries = {**baseline.get("pypi", {}), **baseline.get("npm", {})}

    assert entries, "the baseline is empty; this guard is vacuous"
    for advisory, reason in entries.items():
        assert isinstance(reason, str) and len(reason) > 40, f"{advisory}: {reason!r}"
