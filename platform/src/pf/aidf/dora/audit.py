"""The DORA audit for one entity: run what can run, read what was run
elsewhere, judge every check in the statutory matrix, write the evidence.

Three kinds of input, so the same audit works on a laptop with nothing
installed, in CI with Trivy, and against a Prowler run done in the entity's
own cloud account:

    run_tools=True   Prowler and Trivy are invoked if they are on PATH and the
                     entity names a provider; otherwise those checks read
                     `unverified`
    ocsf=..., vulns=..., sbom=...   files produced elsewhere are ingested and
                     judged exactly as a live run would be
    live=True        repository settings are read through `gh`; without it,
                     `rts-16-branch-protection` is `unverified`

Every check ends in one of four states, and the difference between the last two
is the reason this module exists:

    pass            the evidence was produced and it holds
    fail            the evidence was produced and it does not
    unverified      the check could not run here — a missing tool, no scan, no
                    ledger. Never rendered as a pass.
    not_applicable  the entity declared the article out of scope, with a
                    reason and an owner, in aidf.yaml

The matrix is written to `governance/dora/` beside the inputs it was judged
from, and the run is recorded to the provenance chain with the matrix's SHA-256,
so a report can be shown to have existed, unchanged, at the time it claims.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pf.aidf.config import AidfConfig, _get, load
from pf.aidf.dora import ocsf as ocsf_mod
from pf.aidf.dora import sbom as sbom_mod
from pf.aidf.dora.mapping import Check, Mapping, load_mapping
from pf.provenance import action as provenance_action
from pf.provenance import anchors as prov_anchors
from pf.provenance import is_revoked
from pf.provenance import report as prov_report

TOOL_AUDIT = "aidf.dora"
STATUSES = ("pass", "fail", "unverified", "not_applicable")
_SEV_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFORMATIONAL": 0}


@dataclass
class CheckResult:
    check_id: str
    kind: str
    description: str
    status: str
    detail: str = ""
    evidence: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.check_id, "kind": self.kind, "description": self.description, "status": self.status,
                "detail": self.detail, "evidence": self.evidence, "counts": self.counts}


@dataclass
class ArticleResult:
    id: str
    label: str
    title: str
    requirement: str
    applies: bool
    reason: str
    checks: list[CheckResult]

    @property
    def status(self) -> str:
        if not self.applies:
            return "not_applicable"
        states = {c.status for c in self.checks}
        if "fail" in states:
            return "fail"
        if "unverified" in states:
            return "unverified"
        return "pass"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "title": self.title, "requirement": self.requirement,
                "applies": self.applies, "reason": self.reason, "status": self.status,
                "checks": [c.to_dict() for c in self.checks]}


@dataclass
class AuditReport:
    group: str
    project: str
    generated_at: str
    provider: str
    in_scope: bool
    articles: list[ArticleResult] = field(default_factory=list)
    prowler: dict[str, Any] = field(default_factory=dict)
    sbom: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, str] = field(default_factory=dict)
    out_dir: str = ""
    action_id: str = ""
    matrix_sha256: str = ""

    @property
    def overall(self) -> str:
        if not self.in_scope:
            return "not_applicable"
        states = [a.status for a in self.articles if a.applies]
        if "fail" in states or self.prowler.get("gate") == "fail":
            return "fail"
        if "unverified" in states:
            return "pass_with_gaps"
        return "pass"

    @property
    def exit_code(self) -> int:
        return 1 if self.overall == "fail" else 0

    def counts(self) -> dict[str, int]:
        out = dict.fromkeys(STATUSES, 0)
        for a in self.articles:
            for c in a.checks:
                out[c.status] = out.get(c.status, 0) + 1
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "regulation": "Regulation (EU) 2022/2554 (DORA); RTS (EU) 2024/1774",
            "group": self.group, "project": self.project, "generated_at": self.generated_at,
            "provider": self.provider, "in_scope": self.in_scope, "overall": self.overall,
            "counts": self.counts(), "tools": self.tools, "inputs": self.inputs,
            "prowler": self.prowler, "sbom": self.sbom, "provenance": self.provenance,
            "articles": [a.to_dict() for a in self.articles],
            "action_id": self.action_id, "matrix_sha256": self.matrix_sha256,
        }

    def to_markdown(self) -> str:
        mark = {"pass": "PASS", "fail": "FAIL", "unverified": "UNVERIFIED", "not_applicable": "N/A"}
        lines = [
            f"# DORA evidence matrix — {self.group}/{self.project}",
            "",
            f"Regulation (EU) 2022/2554 with RTS (EU) 2024/1774 · generated {self.generated_at}",
            "",
            "| | |", "|---|---|",
            f"| overall | **{self.overall.upper()}** |",
            f"| in scope | {'yes' if self.in_scope else 'no'} |",
            f"| provider | {self.provider or '— (no infrastructure scan)'} |",
        ]
        for k, v in self.tools.items():
            lines.append(f"| {k} | {v} |")
        c = self.counts()
        lines.append(f"| checks | {c['pass']} pass · {c['fail']} fail · {c['unverified']} unverified · "
                     f"{c['not_applicable']} n/a |")
        if self.action_id:
            lines.append(f"| provenance | action `{self.action_id[:12]}…`, "
                         f"matrix sha256 `{self.matrix_sha256[:16]}…` |")
        lines += ["", "## Articles", "", "| article | requirement | status | evidence |", "|---|---|---|---|"]
        for a in self.articles:
            if not a.applies:
                lines.append(f"| {a.label} {a.title} | {a.requirement} | N/A | {a.reason} |")
                continue
            ev = "<br>".join(f"{mark[ch.status]} `{ch.check_id}` — {ch.detail or ch.description}" for ch in a.checks)
            lines.append(f"| {a.label} {a.title} | {a.requirement} | **{mark[a.status]}** | {ev} |")
        if self.sbom.get("blocking"):
            lines += ["", "## Blocking vulnerabilities (RTS Art. 10)", "",
                      "| id | package | installed | fixed | severity | published |", "|---|---|---|---|---|---|"]
            for v in self.sbom["blocking"][:50]:
                lines.append(f"| {v['id']} | {v['package']} | {v['installed']} | {v['fixed']} | "
                             f"{v['severity']} | {v['published']} |")
        if self.prowler.get("summary"):
            s = self.prowler["summary"]
            summary = (f"{s.get('total', 0)} findings · {s.get('fail', 0)} failing "
                       f"({s.get('fail_critical', 0)} critical, {s.get('fail_high', 0)} high, "
                       f"{s.get('fail_medium', 0)} medium)")
            lines += ["", "## Infrastructure findings (Prowler)", "", summary]
        footer = ("_unverified_ means the check could not run here; it is never counted as a pass. "
                  "`pf dora audit --help` says how to supply each input.")
        lines += ["", footer, ""]
        return "\n".join(lines)


# ------------------------------------------------------------------- runner --
def _sub(template: str, group: str, project: str) -> str:
    return template.replace("{group}", group).replace("{project}", project)


class _Inputs:
    """Everything the checks read, gathered once."""

    def __init__(self) -> None:
        self.findings: list[ocsf_mod.Finding] | None = None
        self.vulns: list[sbom_mod.Vulnerability] | None = None
        self.sbom_path: Path | None = None
        self.prov: Any = None
        self.prov_error = ""
        self.tools: dict[str, str] = {}
        self.files: dict[str, str] = {}
        self.prowler_note = ""


def _run_prowler(provider: str, cfg: AidfConfig, out_dir: Path, inputs: _Inputs) -> None:
    exe = shutil.which("prowler")
    if not exe:
        inputs.tools["prowler"] = "not installed"
        return
    fw = str((cfg.dora.get("prowler") or {}).get("compliance") or "")
    args = [exe, provider]
    try:
        listed = subprocess.run([exe, provider, "--list-compliance"], capture_output=True, text=True,
                                timeout=120, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        listed = ""
    if fw and fw in listed:
        args += ["--compliance", fw]
    else:
        inputs.prowler_note = f"framework {fw!r} not listed by this Prowler for {provider}; findings mapped by check id"
    stem = f"prowler_{provider}"
    args += ["-M", "json-ocsf", "-o", str(out_dir), "-F", stem, "--ignore-exit-code-3"]
    extra = (cfg.dora.get("prowler") or {}).get("extra_args") or []
    args += [str(x) for x in extra]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=3600, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        inputs.tools["prowler"] = f"failed: {exc}"
        return
    if proc.returncode not in (0, 3):
        inputs.tools["prowler"] = f"exit {proc.returncode}: {proc.stderr.strip()[-300:]}"
        return
    files = sorted(out_dir.glob(f"{stem}*.ocsf.json"))
    if not files:
        inputs.tools["prowler"] = "ran, but wrote no OCSF file"
        return
    inputs.findings = ocsf_mod.load_findings(files[-1])
    inputs.files["ocsf"] = str(files[-1])
    inputs.tools["prowler"] = f"ran ({len(inputs.findings)} findings)"


def _run_trivy(root: Path, out_dir: Path, cfg: AidfConfig, inputs: _Inputs) -> None:
    if not sbom_mod.trivy_available():
        inputs.tools["trivy"] = "not installed"
        return
    try:
        inputs.sbom_path = sbom_mod.generate_sbom(root, out_dir / "sbom.cdx.json")
        scan = sbom_mod.scan(root, out_dir / "vulnerabilities.json", sbom=inputs.sbom_path)
    except (OSError, subprocess.SubprocessError) as exc:
        inputs.tools["trivy"] = f"failed: {str(exc)[-300:]}"
        return
    if scan is not None:
        inputs.vulns = sbom_mod.load_vulnerabilities(scan)
        inputs.files["vulnerabilities"] = str(scan)
    if inputs.sbom_path is not None:
        inputs.files["sbom"] = str(inputs.sbom_path)
    inputs.tools["trivy"] = f"ran ({len(inputs.vulns or [])} vulnerabilities)"


def _branch_protection(root: Path) -> tuple[str, str]:
    """(status, detail) from `gh api`; unverified without gh or a token."""
    gh = shutil.which("gh")
    if not gh:
        return "unverified", "gh not available"
    try:
        repo = subprocess.run([gh, "repo", "view", "--json", "nameWithOwner,defaultBranchRef", "-q",
                               '.nameWithOwner + " " + .defaultBranchRef.name'],
                              cwd=str(root), capture_output=True, text=True, timeout=60, check=False)
        if repo.returncode != 0:
            return "unverified", repo.stderr.strip()[-200:] or "gh repo view failed"
        name, branch = repo.stdout.split()
        prot = subprocess.run([gh, "api", f"repos/{name}/branches/{branch}/protection"],
                              cwd=str(root), capture_output=True, text=True, timeout=60, check=False)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return "unverified", str(exc)[-200:]
    if prot.returncode != 0:
        return "fail", f"{branch} has no branch protection ({prot.stderr.strip()[-120:]})"
    try:
        doc = json.loads(prot.stdout)
    except ValueError:
        return "unverified", "unreadable protection payload"
    problems = []
    if not doc.get("required_pull_request_reviews"):
        problems.append("no required pull request review")
    if not doc.get("required_status_checks"):
        problems.append("no required status checks")
    if (doc.get("allow_force_pushes") or {}).get("enabled"):
        problems.append("force pushes allowed")
    return ("fail", "; ".join(problems)) if problems else ("pass", f"{branch}: PR review, status checks, no force push")


# -------------------------------------------------------------- the checks --
def _judge(check: Check, *, root: Path, cfg: AidfConfig, inputs: _Inputs, live: bool, today: date) -> CheckResult:
    kind = check.kind
    res = CheckResult(check.id, kind, check.description, "unverified")

    if kind == "file":
        rel = _sub(str(check.spec.get("path", "")), cfg.group, cfg.project)
        p = root / rel
        res.evidence = [rel]
        res.status = "pass" if p.exists() else "fail"
        res.detail = f"`{rel}` {'present' if p.exists() else 'missing'}"

    elif kind == "declaration":
        key = str(check.spec.get("key", ""))
        val = _get(cfg.doc, key)
        res.status = "pass" if val else "fail"
        res.detail = f"{key} = {val!r}" if val else f"{key} is not set in aidf.yaml"
        res.evidence = list(cfg.layers)

    elif kind == "workflow":
        wf = root / ".github" / "workflows" / str(check.spec.get("file", ""))
        needle = str(check.spec.get("contains", ""))
        res.evidence = [str(wf.relative_to(root))] if wf.exists() else []
        if not wf.exists():
            res.status, res.detail = "fail", f"{wf.name} missing"
        elif needle and needle not in wf.read_text(encoding="utf-8"):
            res.status, res.detail = "fail", f"{wf.name} does not run `{needle}`"
        else:
            res.status, res.detail = "pass", f"{wf.name}" + (f" runs `{needle}`" if needle else " present")

    elif kind == "air":
        import yaml

        baseline: set[str] = set()
        seen: list[str] = []
        for p in (root / "groups" / cfg.group / "air.yaml",
                  root / "groups" / cfg.group / "projects" / cfg.project / "air.yaml"):
            if p.exists():
                seen.append(str(p.relative_to(root)))
                try:
                    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                except yaml.YAMLError:
                    doc = {}
                baseline.update(str(x) for x in (doc.get("baseline") or []))
        res.evidence = seen
        if not seen:
            res.status, res.detail = "fail", "no air.yaml for this entity"
        elif not baseline:
            res.status = "fail"
            res.detail = "air.yaml baseline is empty — `pf air baseline --suggest` proposes what already passes"
        else:
            res.status, res.detail = "pass", f"{len(baseline)} control(s) committed; `pf air gate` blocks a regression"
        res.counts = {"controls": len(baseline)}

    elif kind == "provenance":
        aspect = str(check.spec.get("aspect", "integrity"))
        rep = inputs.prov
        if rep is None:
            res.detail = inputs.prov_error or "ledger unreadable"
        elif rep.records == 0:
            res.detail = "no ledger in this checkout (runtime state; see `pf provenance export`)"
        elif aspect == "integrity":
            fails = [f for f in rep.findings if f.level == "fail"]
            res.status = "pass" if rep.intact and not fails else "fail"
            if res.status == "pass":
                res.detail = f"{rep.records} records hash-linked, {rep.actions_total} actions complete"
            else:
                res.detail = "; ".join(f.detail for f in fails)[:300] or f"{len(rep.breaks)} break(s)"
            res.counts = {"records": rep.records, "actions": rep.actions_total, "breaks": len(rep.breaks)}
        elif aspect == "anchors":
            ok = [a for a in prov_anchors(root) if a.status in ("ok", "pending")]
            res.counts = {"anchors": len(ok), "unanchored_records": rep.unanchored}
            if ok:
                res.status = "pass"
                res.detail = f"{len(ok)} anchor(s); {rep.unanchored} record(s) since the last"
            else:
                res.status = "fail"
                res.detail = "never anchored — `pf provenance anchor` where the ledger lives"
        elif aspect == "revocation":
            stopped, why = is_revoked(root)
            res.status = "pass"
            res.detail = f"kill switch {'ENGAGED: ' + why if stopped else 'armed, not engaged'}; honoured before INTENT"
            res.evidence = ["platform/tests/gate/test_provenance.py", "pf provenance revoke"]
        res.evidence = res.evidence or ["pf provenance verify"]

    elif kind == "trivy":
        aspect = str(check.spec.get("aspect", "policy"))
        if aspect == "sbom":
            if inputs.sbom_path and Path(inputs.sbom_path).exists():
                res.status, res.detail = "pass", f"CycloneDX BOM at {inputs.sbom_path}"
                res.evidence = [str(inputs.sbom_path)]
            else:
                res.detail = f"no SBOM ({inputs.tools.get('trivy', 'trivy not run')})"
        elif aspect == "scan":
            if inputs.vulns is not None:
                res.status, res.detail = "pass", f"{len(inputs.vulns)} vulnerabilities scanned"
                res.evidence = [inputs.files.get("vulnerabilities", "")]
            else:
                res.detail = f"no scan ({inputs.tools.get('trivy', 'trivy not run')})"
        else:
            if inputs.vulns is None:
                res.detail = f"no scan ({inputs.tools.get('trivy', 'trivy not run')})"
            else:
                pv = sbom_mod.assess(inputs.vulns, sbom_mod.PatchPolicy.from_config(cfg.dora.get("sbom") or {}), today)
                res.counts = {"blocking": len(pv.blocking), "advisory": len(pv.advisory), "excepted": len(pv.excepted),
                              "unfixed": len(pv.unfixed), "expired_exceptions": len(pv.expired_exceptions)}
                if pv.blocking:
                    res.status = "fail"
                    ids = ", ".join(v.id for v in pv.blocking[:5])
                    res.detail = f"{len(pv.blocking)} fixable vulnerability(ies) past their window: {ids}"
                elif pv.expired_exceptions:
                    res.status = "fail"
                    expired = ", ".join(e.id for e in pv.expired_exceptions[:5])
                    res.detail = f"{len(pv.expired_exceptions)} exception(s) expired: {expired}"
                else:
                    res.status = "pass"
                    res.detail = (f"{len(inputs.vulns)} scanned, none past its window "
                                  f"({len(pv.excepted)} excepted, {len(pv.unfixed)} unfixed)")
                res.evidence = [inputs.files.get("vulnerabilities", "")]

    elif kind == "prowler":
        if inputs.findings is None:
            res.detail = (f"no Prowler scan ({inputs.tools.get('prowler', 'no provider declared')})")
        else:
            thr = str((cfg.dora.get("prowler") or {}).get("severity_threshold") or "high").upper()
            prefixes = check.prefixes_for(cfg.provider) if cfg.provider else []
            keys = check.compliance_keys or ["dora"]
            wanted = set(check.requirements)
            # The framework's own mapping when the scan carried it (a run with
            # `--compliance dora_2022_2554` stamps every finding with the
            # DORA-Art ids it evidences); the check-id prefixes otherwise.
            by_requirement = [f for f in inputs.findings
                              if wanted and any(f.requirements(k) & wanted for k in keys)]
            matched = by_requirement or [f for f in inputs.findings
                                         if prefixes and any(f.check_id.startswith(p) for p in prefixes)]
            failing = [f for f in matched if f.failed and _SEV_RANK.get(f.severity, 0) >= _SEV_RANK.get(thr, 3)]
            # `mapped_by` is 1 when the framework's own requirement ids did the
            # mapping and 0 when the prefixes did — the report says which.
            res.counts = {"matched": len(matched), "failing": len(failing), "mapped_by": 1 if by_requirement else 0}
            res.evidence = [inputs.files.get("ocsf", "")]
            if failing:
                res.status = "fail"
                names = ", ".join(sorted({f.check_id for f in failing})[:4])
                res.detail = f"{len(failing)} failing check(s) ≥ {thr}: {names}"
            elif matched:
                res.status = "pass"
                res.detail = f"{len(matched)} check(s) exercised, none failing ≥ {thr}"
            else:
                res.detail = "scan ran but exercised none of this article's checks"
                if inputs.prowler_note:
                    res.detail += f" ({inputs.prowler_note})"

    elif kind == "live_github":
        if live:
            res.status, res.detail = _branch_protection(root)
        else:
            res.detail = "run with --live to read repository settings"
        res.evidence = ["gh api repos/{owner}/{repo}/branches/{default}/protection"]

    else:
        res.status, res.detail = "fail", f"unknown check kind {kind!r}"
    return res


def run_audit(
    root: Path,
    group: str,
    project: str,
    *,
    config: AidfConfig | None = None,
    mapping: Mapping | None = None,
    provider: str | None = None,
    ocsf: Path | None = None,
    vulns: Path | None = None,
    sbom: Path | None = None,
    out_dir: Path | None = None,
    run_tools: bool = True,
    live: bool = False,
    today: date | None = None,
    record: bool = True,
    scan_root: Path | None = None,
) -> AuditReport:
    root = Path(root)
    cfg = config or load(root, group, project)
    if provider is not None:
        cfg = AidfConfig(group, project, {**cfg.doc, "dora": {**cfg.dora, "provider": provider}}, cfg.layers)
    m = mapping or load_mapping()
    today = today or datetime.now(UTC).date()
    out_dir = out_dir or (root / "groups" / group / "projects" / project / "governance" / "dora")
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = _Inputs()
    # -- gather
    if ocsf is not None:
        inputs.findings = ocsf_mod.load_findings(ocsf)
        inputs.files["ocsf"] = str(ocsf)
        inputs.tools["prowler"] = f"ingested {Path(ocsf).name} ({len(inputs.findings)} findings)"
    elif run_tools and cfg.provider and cfg.in_scope:
        _run_prowler(cfg.provider, cfg, out_dir, inputs)
    else:
        inputs.tools["prowler"] = "skipped (no provider declared)" if not cfg.provider else "skipped"

    if sbom is not None:
        inputs.sbom_path = Path(sbom)
        inputs.files["sbom"] = str(sbom)
    if vulns is not None:
        inputs.vulns = sbom_mod.load_vulnerabilities(vulns)
        inputs.files["vulnerabilities"] = str(vulns)
        inputs.tools["trivy"] = f"ingested {Path(vulns).name} ({len(inputs.vulns)} vulnerabilities)"
    elif run_tools and cfg.in_scope:
        _run_trivy(scan_root or root, out_dir, cfg, inputs)
    else:
        inputs.tools.setdefault("trivy", "skipped")

    try:
        inputs.prov = prov_report(root)
    except Exception as exc:  # noqa: BLE001 — an unreadable ledger is a finding, not a crash
        inputs.prov_error = f"{type(exc).__name__}: {exc}"[:200]

    # -- judge
    report = AuditReport(group, project, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), cfg.provider, cfg.in_scope,
                         tools=inputs.tools, inputs=inputs.files, out_dir=str(out_dir))
    for art in m.articles:
        applies, reason = cfg.article_applies(art.id)
        if not cfg.in_scope:
            applies, reason = False, str(cfg.dora.get("out_of_scope_reason") or "entity declared out of DORA scope")
        if applies:
            checks = [_judge(c, root=root, cfg=cfg, inputs=inputs, live=live, today=today) for c in art.checks]
        else:
            checks = [CheckResult(c.id, c.kind, c.description, "not_applicable", reason) for c in art.checks]
        report.articles.append(ArticleResult(art.id, art.label, art.title, art.requirement, applies, reason, checks))

    if inputs.findings is not None:
        s = ocsf_mod.summarise(inputs.findings)
        fail_on = (cfg.dora.get("prowler") or {}).get("fail_on") or {}
        breached = [sev for sev in ("critical", "high", "medium")
                    if int(fail_on.get(sev, 0) or 0) and s.get(f"fail_{sev}", 0) >= int(fail_on[sev])]
        report.prowler = {"summary": s, "gate": "fail" if breached else "pass", "breached": breached,
                          "note": inputs.prowler_note}
    if inputs.vulns is not None:
        pv = sbom_mod.assess(inputs.vulns, sbom_mod.PatchPolicy.from_config(cfg.dora.get("sbom") or {}), today)
        report.sbom = pv.to_dict()
    if inputs.prov is not None:
        report.provenance = {"records": inputs.prov.records, "actions": inputs.prov.actions_total,
                             "intact": inputs.prov.intact, "unanchored": inputs.prov.unanchored,
                             "ok": inputs.prov.ok}

    # -- write, then record
    body = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    report.matrix_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    (out_dir / "matrix.json").write_text(body + "\n", encoding="utf-8")
    (out_dir / "matrix.md").write_text(report.to_markdown(), encoding="utf-8")

    if record:
        counts = report.counts()
        with provenance_action(root, tool=TOOL_AUDIT, target=f"{group}/{project}",
                               summary=f"DORA audit: {report.overall}", group=group, project=project) as a:
            a["detail"] = (f"{report.overall}; {counts['pass']} pass, {counts['fail']} fail, "
                           f"{counts['unverified']} unverified; matrix sha256 {report.matrix_sha256}")
            report.action_id = a["action_id"]
        # The matrix names its own action id; rewrite it so the file and the
        # chain cite each other. The hash recorded in the chain is of the
        # matrix *before* the id was written in, and the JSON says which.
        doc = report.to_dict()
        doc["matrix_sha256_covers"] = "this document with action_id and matrix_sha256 empty"
        (out_dir / "matrix.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / "matrix.md").write_text(report.to_markdown(), encoding="utf-8")
    return report
