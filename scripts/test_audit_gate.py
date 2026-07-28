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

    assert {f.id for f in parse_npm_audit(report)} == {"GHSA-bad"}
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


def test_parse_npm_audit_skips_via_without_advisory_url():
    report = _npm_report(
        x={"name": "x", "severity": "high", "via": [{"title": "no url", "severity": "high"}]}
    )

    assert parse_npm_audit(report) == []


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


def test_main_resolved_entries_do_not_fail_the_build(audit_files, capsys):
    pip, npm, baseline = audit_files
    baseline.write_text(
        json.dumps(
            {"pypi": {"PYSEC-1": "why"}, "npm": {"GHSA-1": "why", "GHSA-gone": "already fixed"}}
        )
    )

    rc = main(["--pip-audit", str(pip), "--npm-audit", str(npm), "--baseline", str(baseline)])

    assert rc == 0
    assert "GHSA-gone" in capsys.readouterr().out


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
