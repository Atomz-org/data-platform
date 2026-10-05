"""DORA evidence: the matrix is well-formed, every input shape is read, the
patch policy is arithmetic, and the audit never reports a pass it did not earn.

  unverified is not pass       a missing tool, a missing scan or a missing
                                 ledger reads `unverified`, counts against
                                 `pass_with_gaps`, and never as `pass`

  out of scope is declared     an article or an entity is N/A only with a
                                 reason and an owner, and the reason is printed

  the matrix cites the chain   the audit is itself a recorded action carrying
                                 the matrix's SHA-256
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from typer.testing import CliRunner

from pf import cli
from pf.aidf.dora import ocsf, sbom
from pf.aidf.dora.audit import TOOL_AUDIT, run_audit
from pf.aidf.dora.mapping import CHECK_KINDS, load_mapping, validate_mapping
from pf.provenance import actions, report

TODAY = date(2026, 9, 28)


# --------------------------------------------------------------- mapping --

def test_statutory_matrix_is_well_formed() -> None:
    m = load_mapping()
    assert validate_mapping(m) == []
    assert {a.id for a in m.articles} >= {"5", "6", "8", "9", "10", "12", "17", "24", "25", "28", "RTS-10", "RTS-16"}
    assert all(c.kind in CHECK_KINDS for c in m.checks())
    assert set(m.kinds) == set(CHECK_KINDS), "every kind the matrix may use is documented"
    ids = [c.id for c in m.checks()]
    assert len(ids) == len(set(ids))


def test_every_prowler_check_maps_every_cloud() -> None:
    """A cloud-scoped check names prefixes for all four clouds; a check scoped
    to one provider (`scope: [github]`) names that provider and nothing else."""
    for c in load_mapping().checks():
        if c.kind != "prowler":
            continue
        scope = c.spec.get("scope")
        if scope:
            assert all(c.prefixes_for(p) for p in scope), f"{c.id} scoped to {scope} but names no prefixes for it"
            assert not any(c.prefixes_for(p) for p in ("aws", "azure", "gcp", "kubernetes")), f"{c.id} is scoped"
            continue
        for provider in ("aws", "azure", "gcp", "kubernetes"):
            assert c.prefixes_for(provider), f"{c.id} has no {provider} check prefixes"


# ------------------------------------------------------------------ OCSF --
OCSF = [
    {"status_code": "FAIL", "severity": "High", "cloud": {"provider": "aws"},
     "finding_info": {"title": "IAM root MFA"}, "unmapped": {"check_id": "iam_root_mfa_enabled",
                                                              "compliance": {"CIS-1.5": ["1.5"]}},
     "resources": [{"uid": "arn:aws:iam::1:root"}]},
    {"status_code": "PASS", "severity": "Medium", "cloud": {"provider": "aws"},
     "unmapped": {"check_id": "cloudtrail_multi_region_enabled"}},
    {"status_code": "FAIL", "severity": "Low", "cloud": {"provider": "aws"},
     "unmapped": {"check_id": "ec2_securitygroup_default_restrict_traffic"}},
    {"status": "FAIL", "severity_id": 5, "provider": "aws", "check_id": "backup_plans_exist"},
]


def test_ocsf_array_and_ndjson_read_the_same(tmp_path: Path) -> None:
    arr = tmp_path / "a.ocsf.json"
    arr.write_text(json.dumps(OCSF))
    nd = tmp_path / "b.ocsf.json"
    nd.write_text("\n".join(json.dumps(x) for x in OCSF) + "\n")
    a, b = ocsf.load_findings(arr), ocsf.load_findings(nd)
    assert [f.check_id for f in a] == [f.check_id for f in b]
    assert a[0].failed and a[0].severity == "HIGH" and a[0].provider == "aws" and a[0].resource.startswith("arn:")
    assert a[3].severity == "CRITICAL", "severity_id is understood when severity is absent"
    s = ocsf.summarise(a)
    assert s["total"] == 4 and s["fail"] == 3 and s["fail_high"] == 1 and s["fail_critical"] == 1 and s["pass"] == 1


# ------------------------------------------------------------------ SBOM --
TRIVY = {"Results": [{"Target": "uv.lock", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2026-0001", "PkgName": "requests", "InstalledVersion": "2.31", "FixedVersion": "2.32",
     "Severity": "CRITICAL", "PublishedDate": "2026-09-01T00:00:00Z"},
    {"VulnerabilityID": "CVE-2026-0002", "PkgName": "urllib3", "InstalledVersion": "1.26", "FixedVersion": "",
     "Severity": "HIGH", "PublishedDate": "2026-01-01T00:00:00Z"},
    {"VulnerabilityID": "CVE-2026-0003", "PkgName": "pyyaml", "InstalledVersion": "6.0", "FixedVersion": "6.1",
     "Severity": "MEDIUM", "PublishedDate": "2026-09-20T00:00:00Z"},
    {"VulnerabilityID": "CVE-2026-0004", "PkgName": "jinja2", "InstalledVersion": "3.1", "FixedVersion": "3.2",
     "Severity": "HIGH", "PublishedDate": "2026-09-27T00:00:00Z"},
]}]}

CDX = {"bomFormat": "CycloneDX", "specVersion": "1.5",
       "components": [{"bom-ref": "pkg:pypi/requests@2.31", "name": "requests", "version": "2.31"}],
       "vulnerabilities": [{"id": "CVE-2026-0001", "published": "2026-09-01T00:00:00Z",
                            "ratings": [{"severity": "critical"}],
                            "affects": [{"ref": "pkg:pypi/requests@2.31", "versions": [{"version": "2.32", "status": "unaffected"}]}]}]}


def test_trivy_and_cyclonedx_parse(tmp_path: Path) -> None:
    t = tmp_path / "trivy.json"
    t.write_text(json.dumps(TRIVY))
    c = tmp_path / "bom.cdx.json"
    c.write_text(json.dumps(CDX))
    tv = sbom.load_vulnerabilities(t)
    cv = sbom.load_vulnerabilities(c)
    assert len(tv) == 4 and tv[0].fixable and not tv[1].fixable
    assert len(cv) == 1 and cv[0].id == "CVE-2026-0001" and cv[0].fixed == "2.32" and cv[0].severity == "CRITICAL"


def test_patch_policy_is_arithmetic(tmp_path: Path) -> None:
    t = tmp_path / "trivy.json"
    t.write_text(json.dumps(TRIVY))
    vulns = sbom.load_trivy(t)
    seven = {"critical": 0, "high": 7, "medium": 30, "low": 90}
    policy = sbom.PatchPolicy.from_config({"severity": ["CRITICAL", "HIGH"], "ignore_unfixed": True,
                                           "grace_days": seven})
    v = sbom.assess(vulns, policy, TODAY)
    assert [x.id for x in v.blocking] == ["CVE-2026-0001"], "critical, fixable, 27 days old, zero grace"
    assert [x.id for x in v.unfixed] == ["CVE-2026-0002"], "high but unfixable: tracked, not blocked"
    assert {x.id for x in v.advisory} == {"CVE-2026-0003", "CVE-2026-0004"}, "medium is advisory; high inside 7d grace"
    assert v.ok is False

    # An exception moves it out of blocking; an expired one puts it back and is itself reported.
    excepted = sbom.PatchPolicy.from_config({"grace_days": seven, "exceptions": [
        {"id": "CVE-2026-0001", "reason": "not reachable", "owner": "a@b.c", "expires": "2027-01-01"}]})
    assert sbom.assess(vulns, excepted, TODAY).ok
    expired = sbom.PatchPolicy.from_config({"grace_days": seven, "exceptions": [
        {"id": "CVE-2026-0001", "reason": "not reachable", "owner": "a@b.c", "expires": "2026-01-01"}]})
    e = sbom.assess(vulns, expired, TODAY)
    assert not e.ok and [x.id for x in e.expired_exceptions] == ["CVE-2026-0001"]

    # Zero tolerance — the platform floor: a high inside a 7-day window blocks when the window is 0.
    zero = sbom.PatchPolicy.from_config({})
    assert {x.id for x in sbom.assess(vulns, zero, TODAY).blocking} == {"CVE-2026-0001", "CVE-2026-0004"}


def test_unknown_publish_date_is_outside_every_window() -> None:
    v = sbom.Vulnerability("CVE-X", "p", "1", "2", "HIGH", published=None)
    assert sbom.assess([v], sbom.PatchPolicy(grace_days={"high": 365}), TODAY).blocking == [v]


# ----------------------------------------------------------------- audit --

@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("gate.yaml", "gate.capabilities.yaml", "loop-constraints.md", "LOOP.md", "vendor.lock.json"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)
    (tmp_path / "platform" / "hooks").mkdir(parents=True)
    (tmp_path / "platform" / "hooks" / "pre_commit.sh").write_text("#!/bin/sh\n")
    (tmp_path / "platform" / "src" / "pf" / "vendor").mkdir(parents=True)
    (tmp_path / "platform" / "src" / "pf" / "vendor" / "registry.yaml").write_text("version: 1\n")
    (tmp_path / ".memory").mkdir()
    (tmp_path / ".memory" / "MEMORY.md").write_text("# memory\n")
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    for name in ("loop-observations.yml", "bot-findings.yml", "platform-tests.yml", "ai-governance.yml",
                 "dora.yml", "vendor-pins.yml"):
        shutil.copy(REPO_ROOT / ".github" / "workflows" / name, wf / name)
    pdir = tmp_path / "groups" / "g" / "projects" / "p"
    (pdir / "governance").mkdir(parents=True)
    (pdir / "governance" / "policy.yaml").write_text("policies: []\n")
    (pdir / "kg").mkdir()
    (pdir / "kg" / "graph.json").write_text('{"nodes": [], "edges": []}')
    (tmp_path / "groups" / "g" / "ontology").mkdir()
    (tmp_path / "groups" / "g" / "notify.yaml").write_text("version: 1\n")
    (tmp_path / "groups" / "g" / "air.yaml").write_text("version: 1\nbaseline: []\naccepted: []\n")
    monkeypatch.setenv("PF_AGENT", "test-agent")
    return tmp_path


def _overlay(repo: Path, doc: dict) -> None:
    (repo / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml").write_text(yaml.safe_dump(doc))


def _check(rep, check_id: str):
    for a in rep.articles:
        for c in a.checks:
            if c.check_id == check_id:
                return c
    raise KeyError(check_id)


def test_audit_with_nothing_installed_is_gaps_not_pass(repo: Path) -> None:
    rep = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    assert rep.overall in ("pass_with_gaps", "fail")
    assert _check(rep, "dora-8-asset-inventory").status == "unverified"
    assert _check(rep, "dora-7-sbom").status == "unverified"
    assert _check(rep, "rts-16-branch-protection").status == "unverified"
    assert _check(rep, "dora-5-owner").status == "fail", "no owner declared"
    assert _check(rep, "dora-6-air-baseline").status == "fail", "empty baseline is a gap, not a pass"
    assert _check(rep, "dora-8-graph").status == "pass"
    assert _check(rep, "dora-24-suite").status == "pass"
    assert _check(rep, "rts-16-commit-gate").status == "pass"
    counts = rep.counts()
    assert counts["unverified"] > 0 and counts["pass"] > 0


def test_audit_writes_matrix_and_records_to_the_chain(repo: Path) -> None:
    rep = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    out = repo / "groups" / "g" / "projects" / "p" / "governance" / "dora"
    assert (out / "matrix.json").exists() and (out / "matrix.md").exists()
    doc = json.loads((out / "matrix.json").read_text())
    assert doc["action_id"] == rep.action_id and doc["matrix_sha256"] == rep.matrix_sha256
    st = actions(repo)[rep.action_id]
    assert st["execution"].payload["status"] == "ok" and rep.matrix_sha256 in st["execution"].payload["detail"]
    assert {r.tool for r in (st["intent"], st["decision"], st["execution"])} == {TOOL_AUDIT}
    md = (out / "matrix.md").read_text()
    assert "UNVERIFIED" in md and "never counted as a pass" in md
    assert report(repo).ok


def test_provenance_articles_read_the_ledger(repo: Path) -> None:
    first = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    assert _check(first, "dora-12-chain").status == "unverified", "an empty ledger is not evidence"
    second = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    assert _check(second, "dora-12-chain").status == "pass", "the first audit's own record is now evidence"
    assert _check(second, "dora-12-anchor").status == "fail", "never anchored"
    assert _check(second, "dora-11-kill-switch").status == "pass"


def test_aggregate_cli_audit_does_not_self_contaminate_provenance(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A family-wide audit shares one runtime ledger in the checkout.

    Recording the first entity would make the second entity treat that brand-new
    audit record as pre-existing provenance and fail on missing anchors. The CLI
    must leave aggregate audits as report-only runs.
    """
    (repo / "groups" / "g" / "air.yaml").write_text("version: 1\nbaseline: [AIR-DET-21]\naccepted: []\n")
    _overlay(repo, {"dora": {"owner": "risk@example.com"}})
    shutil.copytree(repo / "groups" / "g" / "projects" / "p", repo / "groups" / "g" / "projects" / "q")
    monkeypatch.chdir(repo)

    res = CliRunner().invoke(cli.app, ["dora", "audit", "g", "--no-run"])

    assert res.exit_code == 0, res.output
    assert "PASS_WITH_GAPS g/p" in res.output
    assert "PASS_WITH_GAPS g/q" in res.output
    assert report(repo).records == 0, "aggregate mode must not record shared-ledger evidence"


def test_ingested_prowler_findings_fail_the_right_article(repo: Path, tmp_path: Path) -> None:
    _overlay(repo, {"dora": {"provider": "aws", "owner": "risk@example.com"}})
    f = tmp_path / "findings.ocsf.json"
    f.write_text(json.dumps(OCSF))
    rep = run_audit(repo, "g", "p", ocsf=f, run_tools=False, today=TODAY)
    assert _check(rep, "dora-9-iam").status == "fail" and "iam_root_mfa_enabled" in _check(rep, "dora-9-iam").detail
    assert _check(rep, "dora-10-logging").status == "pass", "cloudtrail passed"
    assert _check(rep, "dora-9-network").status == "pass", "a LOW failure is below the HIGH threshold"
    assert _check(rep, "dora-11-backups").status == "fail", "severity_id 5 is critical"
    assert _check(rep, "dora-5-owner").status == "pass"
    assert rep.prowler["gate"] == "fail" and "critical" in rep.prowler["breached"]
    assert rep.overall == "fail" and rep.exit_code == 1


def test_ingested_vulnerabilities_judge_the_patch_window(repo: Path, tmp_path: Path) -> None:
    v = tmp_path / "trivy.json"
    v.write_text(json.dumps(TRIVY))
    rep = run_audit(repo, "g", "p", vulns=v, run_tools=False, today=TODAY)
    c = _check(rep, "rts-10-patch-window")
    assert c.status == "fail" and "CVE-2026-0001" in c.detail
    assert _check(rep, "dora-13-vuln-feed").status == "pass"
    assert rep.sbom["blocking"][0]["id"] == "CVE-2026-0001"
    assert "CVE-2026-0001" in (repo / "groups" / "g" / "projects" / "p" / "governance" / "dora" / "matrix.md").read_text()

    # Excepting the critical is not enough: the floor is zero tolerance on
    # High too, and CVE-2026-0004 is High, fixable and one day old. Both need
    # a dated, owned exception before the window reads clean.
    _overlay(repo, {"dora": {"sbom": {"exceptions": [
        {"id": "CVE-2026-0001", "reason": "unreachable", "owner": "a@b.c", "expires": "2027-01-01"}]}}})
    rep2 = run_audit(repo, "g", "p", vulns=v, run_tools=False, today=TODAY)
    assert _check(rep2, "rts-10-patch-window").status == "fail"
    assert "CVE-2026-0004" in _check(rep2, "rts-10-patch-window").detail
    _overlay(repo, {"dora": {"sbom": {"exceptions": [
        {"id": "CVE-2026-0001", "reason": "unreachable", "owner": "a@b.c", "expires": "2027-01-01"},
        {"id": "CVE-2026-0004", "reason": "template never rendered from user input", "owner": "a@b.c",
         "expires": "2026-12-01"}]}}})
    rep3 = run_audit(repo, "g", "p", vulns=v, run_tools=False, today=TODAY)
    assert _check(rep3, "rts-10-patch-window").status == "pass"
    assert _check(rep3, "rts-10-patch-window").counts["excepted"] == 2


def test_article_opt_out_is_printed_with_its_reason(repo: Path) -> None:
    _overlay(repo, {"dora": {"articles": {"28": {"applies": False, "reason": "no third-party ICT provider",
                                                  "owner": "risk@example.com"}}}})
    rep = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    art = next(a for a in rep.articles if a.id == "28")
    assert art.status == "not_applicable" and all(c.status == "not_applicable" for c in art.checks)
    assert "no third-party ICT provider" in rep.to_markdown()


def test_out_of_scope_entity_is_not_applicable_not_pass(repo: Path) -> None:
    _overlay(repo, {"dora": {"in_scope": False, "out_of_scope_reason": "not a financial entity", "owner": "a@b.c"}})
    rep = run_audit(repo, "g", "p", run_tools=False, today=TODAY)
    assert rep.overall == "not_applicable" and rep.exit_code == 0
    assert all(a.status == "not_applicable" for a in rep.articles)
    assert "not a financial entity" in rep.to_markdown()


def test_matrix_json_carries_no_floats(repo: Path) -> None:
    rep = run_audit(repo, "g", "p", run_tools=False, today=TODAY)

    def walk(x):
        if isinstance(x, float):
            raise AssertionError("float in the matrix")
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        if isinstance(x, list):
            for v in x:
                walk(v)
    walk(rep.to_dict())


def test_generated_evidence_is_denied_to_hand_edits() -> None:
    from pf.loops.gate import check_path

    r = check_path("groups/g/projects/p/governance/dora/matrix.json", REPO_ROOT)
    assert r.blocked and "denylist" in r.rule
    assert not check_path("groups/g/projects/p/governance/aidf.yaml", REPO_ROOT).blocked
    assert check_path("groups/g/projects/p/governance/aidf.yaml", REPO_ROOT).verdict == "warn", "impact first"


# ------------------------------------------------- parity with pinned Prowler --
PROWLER_DORA = REPO_ROOT / "vendor" / "prowler" / "prowler" / "compliance" / "dora_2022_2554.json"


def test_requirement_ids_come_from_the_framework_when_present(repo: Path, tmp_path: Path) -> None:
    """A finding stamped with DORA-Art9 lands on Article 9 whatever its check id;
    without the stamp the prefixes decide."""
    _overlay(repo, {"dora": {"provider": "aws", "owner": "risk@example.com"}})
    stamped = [{"status_code": "FAIL", "severity": "High", "cloud": {"provider": "aws"},
                "unmapped": {"check_id": "some_new_check_nobody_prefixed",
                             "compliance": {"DORA-2022/2554": ["DORA-Art9"]}}}]
    f = tmp_path / "stamped.ocsf.json"
    f.write_text(json.dumps(stamped))
    rep = run_audit(repo, "g", "p", ocsf=f, run_tools=False, today=TODAY)
    iam = _check(rep, "dora-9-iam")
    assert iam.status == "fail" and iam.counts["mapped_by"] == 1
    assert _check(rep, "dora-10-logging").status == "unverified", "not stamped for Art. 10, no prefix match"


@pytest.mark.skipif(not PROWLER_DORA.exists(), reason="vendor/prowler not checked out")
def test_named_requirements_exist_in_the_pinned_framework() -> None:
    """`kind: parity` in the vendor registry, made a check: every DORA-Art id the
    matrix names is one the pinned Prowler framework defines, the framework file
    is the one `defaults.yaml` requests, and its name is what `cites("dora")`
    matches on."""
    from pf.aidf.config import defaults

    fw = json.loads(PROWLER_DORA.read_text(encoding="utf-8"))
    ids = {r["id"] for r in fw["requirements"]}
    named = {req for c in load_mapping().checks() for req in c.requirements}
    assert named and named <= ids, sorted(named - ids)
    assert defaults()["dora"]["prowler"]["compliance"] == PROWLER_DORA.stem
    assert "dora" in fw["framework"].lower()
    providers = {p for r in fw["requirements"] for p in (r.get("checks") or {})}
    assert {"aws", "azure", "gcp"} <= providers, "the prefix fallback must stay for providers the framework lacks"
    assert "kubernetes" not in providers, "kubernetes has no DORA checks upstream; the mapping's k8s prefixes are the only route"


@pytest.mark.skipif(not PROWLER_DORA.exists(), reason="vendor/prowler not checked out")
def test_prefixes_name_real_check_namespaces() -> None:
    """Every check-id prefix in the matrix names a service Prowler actually has,
    so a typo cannot quietly match nothing forever."""
    from pf.aidf.dora.mapping import PROVIDERS

    services = REPO_ROOT / "vendor" / "prowler" / "prowler" / "providers"
    for c in load_mapping().checks():
        if c.kind != "prowler":
            continue
        for provider in PROVIDERS:
            have = {p.name for p in (services / provider / "services").iterdir() if p.is_dir()}
            for prefix in c.prefixes_for(provider):
                if prefix.startswith("r2_"):
                    continue  # the platform's own R2 scan, not a Prowler service
                svc = prefix.split("_", 1)[0]
                assert svc in have, f"{c.id}: {provider} prefix {prefix!r} names no service"


# ------------------------------------------------ several providers, one audit --

def test_each_finding_is_judged_by_its_own_provider(repo: Path, tmp_path: Path) -> None:
    """A gcp scan and a github scan ingested together: the github finding lands
    on the RTS Art. 16 posture check by its own provider, the gcp one on Art. 9
    by its DORA stamp, and the report names both."""
    _overlay(repo, {"dora": {"provider": "gcp", "extra_providers": ["github"], "owner": "risk@example.com"}})
    gcp = tmp_path / "gcp.ocsf.json"
    gcp.write_text(json.dumps([{"status_code": "FAIL", "severity": "High", "cloud": {"provider": "gcp"},
                                "unmapped": {"check_id": "iam_sa_no_administrative_privileges",
                                             "compliance": {"DORA-2022/2554": ["DORA-Art9"]}}}]))
    gh = tmp_path / "github.ocsf.json"
    gh.write_text(json.dumps([
        {"status_code": "FAIL", "severity": "High", "cloud": {"provider": "github"},
         "unmapped": {"check_id": "repository_default_branch_requires_signed_commits"}},
        {"status_code": "PASS", "severity": "Medium", "cloud": {"provider": "github"},
         "unmapped": {"check_id": "organization_members_mfa_required"}},
    ]))
    rep = run_audit(repo, "g", "p", ocsf=[gcp, gh], run_tools=False, today=TODAY)
    assert rep.provider == "gcp, github"
    posture = _check(rep, "rts-16-github-posture")
    assert posture.status == "fail" and "signed_commits" in posture.detail and posture.counts["mapped_by"] == 0
    iam = _check(rep, "dora-9-iam")
    assert iam.status == "fail" and iam.counts["matched"] == 2, "the stamped gcp finding plus the github MFA check"
    assert _check(rep, "dora-8-asset-inventory").status == "unverified"
    assert {k.split(":")[0] for k in rep.tools} >= {"prowler", "trivy"} or any(k.startswith("prowler:") for k in rep.tools)


def test_extra_providers_only_grow_and_are_validated(tmp_path: Path) -> None:
    from pf.aidf.config import load
    from pf.aidf.dora.mapping import PROVIDERS

    root = tmp_path
    (root / "groups" / "g" / "projects" / "p" / "governance").mkdir(parents=True)
    (root / "platform").mkdir()
    (root / "groups" / "g" / "aidf.yaml").write_text(yaml.safe_dump({"dora": {"extra_providers": ["github"]}}))
    (root / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml").write_text(
        yaml.safe_dump({"dora": {"provider": "gcp", "extra_providers": ["cloudflare"]}}))
    cfg = load(root, "g", "p")
    assert cfg.providers == ["gcp", "github", "cloudflare"], "the cloud first, then every extra, none dropped"
    assert set(cfg.providers) <= set(PROVIDERS)
    assert "github" in PROVIDERS and "cloudflare" in PROVIDERS


# ------------------------------------------------------------------ R2 scan --
def _cf(responses: dict[str, object]):
    """A fake Cloudflare API: path -> result. Missing paths answer 404-shaped."""
    calls: list[str] = []

    def fetch(path: str) -> dict:
        calls.append(path)
        if path in responses:
            return {"success": True, "errors": [], "result": responses[path]}
        return {"success": False, "errors": [{"code": 404, "message": "not found"}], "result": None}

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def test_r2_scan_judges_every_bucket() -> None:
    from pf.aidf.dora import r2

    acct = "a" * 32
    fetch = _cf({
        f"/accounts/{acct}/r2/buckets": {"buckets": [
            {"name": "data-platform", "location": "WEUR", "creation_date": "2026-09-01T00:00:00Z"},
            {"name": "scratch", "location": "auto", "creation_date": "2026-09-20T00:00:00Z"},
        ]},
        f"/accounts/{acct}/r2/buckets/data-platform/domains/managed": {"enabled": False},
        f"/accounts/{acct}/r2/buckets/data-platform/domains/custom": {"domains": [{"domain": "art.example.com", "minTLS": "1.2"}]},
        f"/accounts/{acct}/r2/buckets/data-platform/cors": {"rules": [{"allowed": {"origins": ["https://app.example.com"]}}]},
        f"/accounts/{acct}/r2/buckets/data-platform/lifecycle": {"rules": [{"id": "expire-old", "enabled": True}]},
        f"/accounts/{acct}/r2/buckets/scratch/domains/managed": {"enabled": True},
        f"/accounts/{acct}/r2/buckets/scratch/domains/custom": {"domains": []},
        f"/accounts/{acct}/r2/buckets/scratch/cors": {"rules": [{"allowed": {"origins": ["*"]}}]},
        f"/accounts/{acct}/r2/buckets/scratch/lifecycle": {"rules": []},
    })
    findings = r2.scan(acct, fetch)
    by = {(f["resources"][0]["name"], f["unmapped"]["check_id"]): f["status_code"] for f in findings}
    assert by[("data-platform", "r2_bucket_inventoried")] == "PASS"
    assert by[("data-platform", "r2_bucket_public_access_disabled")] == "PASS"
    assert by[("data-platform", "r2_bucket_custom_domain_tls_secure")] == "PASS"
    assert by[("data-platform", "r2_bucket_cors_not_wildcard")] == "PASS"
    assert by[("data-platform", "r2_bucket_lifecycle_configured")] == "PASS"
    assert by[("scratch", "r2_bucket_public_access_disabled")] == "FAIL", "r2.dev enabled: world-readable"
    assert by[("scratch", "r2_bucket_cors_not_wildcard")] == "FAIL"
    assert by[("scratch", "r2_bucket_lifecycle_configured")] == "FAIL"
    assert ("scratch", "r2_bucket_custom_domain_tls_secure") not in by, "no custom domain, no verdict about one"
    assert all(f["cloud"]["provider"] == "cloudflare" for f in findings)
    assert r2.summary(findings) == {"buckets": 2, "pass": 6, "fail": 3, "manual": 0}
    assert "Bearer" not in json.dumps(findings)


def test_r2_scan_reports_not_hides_an_unreadable_call() -> None:
    from pf.aidf.dora import r2

    acct = "b" * 32
    fetch = _cf({f"/accounts/{acct}/r2/buckets": {"buckets": [{"name": "x"}]}})  # every sub-call 404s
    findings = r2.scan(acct, fetch)
    by = {f["unmapped"]["check_id"]: f["status_code"] for f in findings}
    assert by["r2_bucket_public_access_disabled"] == "MANUAL", "unreadable is not a pass"
    assert "r2_bucket_cors_not_wildcard" not in by and "r2_bucket_lifecycle_configured" not in by


def test_r2_scan_refuses_without_the_account_listing() -> None:
    from pf.aidf.dora import r2

    with pytest.raises(r2.R2AccessError):
        r2.scan("c" * 32, _cf({}))


def test_r2_account_id_is_derived_from_the_artefact_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    from pf.aidf.dora import r2

    monkeypatch.delenv("DORA_CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("PF_ARTIFACTS_ENDPOINT", f"https://{'d' * 32}.r2.cloudflarestorage.com")
    assert r2.account_id_from_env() == "d" * 32
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "e" * 32)
    assert r2.account_id_from_env() == "e" * 32


def test_r2_findings_flow_into_the_audit(repo: Path, tmp_path: Path) -> None:
    from pf.aidf.dora import r2

    acct = "f" * 32
    fetch = _cf({
        f"/accounts/{acct}/r2/buckets": {"buckets": [{"name": "data-platform"}]},
        f"/accounts/{acct}/r2/buckets/data-platform/domains/managed": {"enabled": True},
        f"/accounts/{acct}/r2/buckets/data-platform/domains/custom": {"domains": []},
        f"/accounts/{acct}/r2/buckets/data-platform/cors": {"rules": []},
        f"/accounts/{acct}/r2/buckets/data-platform/lifecycle": {"rules": [{"id": "keep-400d"}]},
    })
    out = r2.write_ocsf(r2.scan(acct, fetch), tmp_path / "r2.ocsf.json")
    _overlay(repo, {"dora": {"extra_providers": ["cloudflare"], "owner": "risk@example.com"}})
    rep = run_audit(repo, "g", "p", ocsf=[out], run_tools=False, today=TODAY)
    assert _check(rep, "dora-9-iam").status == "fail", "a public r2.dev bucket is an access-control failure"
    assert _check(rep, "dora-12-r2-retention").status == "pass"
    assert _check(rep, "dora-8-asset-inventory").status == "pass", "the inventory finding exercises Art. 8"
    assert rep.provider == "cloudflare"


# ----------------------------------------------- the shape Prowler 5 really writes --
REAL_PROWLER_5 = {
    "activity_name": "Create", "class_name": "Detection Finding",
    "status_code": "FAIL", "status": "New", "severity": "Critical", "severity_id": 5,
    "status_detail": "Organization Atomz-org does not require members to have two-factor authentication enabled.",
    "metadata": {"event_code": "organization_members_mfa_required", "product": {"name": "Prowler"}, "version": "1.4.0"},
    "finding_info": {"uid": "prowler-github-organization_members_mfa_required-Atomz-org-Atomz-org-Atomz-org",
                     "title": "Organization requires members to have two-factor authentication enabled"},
    "cloud": {"account": {"name": "Atomz-org", "uid": "Atomz-org"}, "provider": "github", "region": "Atomz-org"},
    "resources": [{"uid": "313147314", "name": "Atomz-org", "type": "NotDefined", "region": "Atomz-org"}],
    "unmapped": {"provider": "github", "compliance": {"CIS-1.2.0": ["1.3.4", "1.3.5"]}, "categories": []},
}


def test_prowler_5_output_shape_is_read_correctly() -> None:
    """Captured from a real `prowler github` run of 2026-09-28: no
    `unmapped.check_id`, the check name in `metadata.event_code`, a composite
    `finding_info.uid`, the readable resource in `resources[].name`. The first
    parser fell back to the uid and no prefix could match."""
    f = ocsf.normalise(REAL_PROWLER_5)
    assert f.check_id == "organization_members_mfa_required"
    assert f.provider == "github" and f.failed and f.severity == "CRITICAL"
    assert f.resource == "Atomz-org"
    assert f.cites("cis") and not f.cites("dora")
    # And the uid fallback, for a producer that writes neither field:
    stripped = {**REAL_PROWLER_5, "metadata": {}, "unmapped": {"provider": "github"}}
    assert ocsf.normalise(stripped).check_id.startswith("organization_members_mfa_required")


def test_real_github_finding_lands_on_article_9(repo: Path, tmp_path: Path) -> None:
    f = tmp_path / "gh.ocsf.json"
    f.write_text(json.dumps([REAL_PROWLER_5]))
    _overlay(repo, {"dora": {"extra_providers": ["github"], "owner": "risk@example.com"}})
    rep = run_audit(repo, "g", "p", ocsf=[f], run_tools=False, today=TODAY)
    iam = _check(rep, "dora-9-iam")
    assert iam.status == "fail" and "organization_members_mfa_required" in iam.detail
