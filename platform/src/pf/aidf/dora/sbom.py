"""The software bill of materials and the patch policy that judges it.

RTS (EU) 2024/1774 Art. 10 asks two things of a financial entity: know what you
run, and patch it within a risk-based window. The first is a CycloneDX SBOM of
the dependency tree — `uv.lock` for the platform, plus any container image the
entity ships. The second is a vulnerability scan over that SBOM judged against
`dora.sbom` in the entity's resolved `aidf.yaml`:

    severity       which severities block (CRITICAL, HIGH by default)
    ignore_unfixed a vulnerability with no fix is tracked, not blocked on
    grace_days     how long a fixable vulnerability may stay unpatched
    exceptions     accepted vulnerabilities, each dated, owned and reasoned

Trivy is the scanner the platform drives, as a command, never imported: it is a
Go binary. Grype/Syft users get the same verdict by handing the audit a
CycloneDX file with a `vulnerabilities` array — the parser reads both shapes.

The verdict is a list of what blocks and a list of what is only reported, each
entry naming the package, the version, the fix and how long it has been open.
No score, no float: an auditor wants the CVE, not a number about it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0, "NEGLIGIBLE": 0, "INFORMATIONAL": 0}


@dataclass(frozen=True)
class Vulnerability:
    id: str
    package: str
    installed: str
    fixed: str  # "" when no fix is available
    severity: str
    published: date | None = None
    target: str = ""
    title: str = ""

    @property
    def fixable(self) -> bool:
        return bool(self.fixed)

    def age_days(self, today: date) -> int | None:
        return (today - self.published).days if self.published else None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "package": self.package, "installed": self.installed, "fixed": self.fixed,
                "severity": self.severity, "published": self.published.isoformat() if self.published else "",
                "target": self.target, "title": self.title}


@dataclass(frozen=True)
class Exception_:
    id: str
    reason: str
    owner: str
    expires: date

    def live(self, today: date) -> bool:
        return today <= self.expires


@dataclass(frozen=True)
class PatchPolicy:
    blocking_severities: tuple[str, ...] = ("CRITICAL", "HIGH")
    ignore_unfixed: bool = True
    grace_days: dict[str, int] = field(default_factory=lambda: {"critical": 0, "high": 0, "medium": 30, "low": 90})
    exceptions: tuple[Exception_, ...] = ()

    @classmethod
    def from_config(cls, sbom_cfg: dict[str, Any]) -> PatchPolicy:
        excs = []
        for e in sbom_cfg.get("exceptions") or []:
            exp = e.get("expires")
            if isinstance(exp, datetime):
                exp = exp.date()
            elif isinstance(exp, str):
                exp = date.fromisoformat(exp[:10])
            excs.append(Exception_(str(e["id"]), str(e["reason"]), str(e["owner"]), exp))
        base = cls()
        grace = dict(base.grace_days)
        grace.update({str(k).lower(): int(v) for k, v in (sbom_cfg.get("grace_days") or {}).items()})
        return cls(
            blocking_severities=tuple(str(s).upper() for s in (sbom_cfg.get("severity") or base.blocking_severities)),
            ignore_unfixed=bool(sbom_cfg.get("ignore_unfixed", base.ignore_unfixed)),
            grace_days=grace,
            exceptions=tuple(excs),
        )

    def grace_for(self, severity: str) -> int:
        return int(self.grace_days.get(severity.lower(), 0))


@dataclass
class PatchVerdict:
    blocking: list[Vulnerability] = field(default_factory=list)
    advisory: list[Vulnerability] = field(default_factory=list)
    excepted: list[tuple[Vulnerability, Exception_]] = field(default_factory=list)
    expired_exceptions: list[Exception_] = field(default_factory=list)
    unfixed: list[Vulnerability] = field(default_factory=list)
    scanned: int = 0

    @property
    def ok(self) -> bool:
        return not self.blocking

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "scanned": self.scanned,
            "blocking": [v.to_dict() for v in self.blocking],
            "advisory": [v.to_dict() for v in self.advisory],
            "excepted": [
                {**v.to_dict(), "exception": {"reason": e.reason, "owner": e.owner, "expires": e.expires.isoformat()}}
                for v, e in self.excepted
            ],
            "expired_exceptions": [
                {"id": e.id, "owner": e.owner, "expires": e.expires.isoformat()} for e in self.expired_exceptions
            ],
            "unfixed": [v.to_dict() for v in self.unfixed],
        }


def assess(vulns: list[Vulnerability], policy: PatchPolicy, today: date | None = None) -> PatchVerdict:
    """Apply the patch policy. Deterministic given `today`."""
    today = today or datetime.now(UTC).date()
    verdict = PatchVerdict(scanned=len(vulns))
    live = {e.id: e for e in policy.exceptions if e.live(today)}
    verdict.expired_exceptions = [e for e in policy.exceptions if not e.live(today)]
    for v in vulns:
        sev = v.severity.upper()
        if v.id in live:
            verdict.excepted.append((v, live[v.id]))
            continue
        if not v.fixable:
            verdict.unfixed.append(v)
            if policy.ignore_unfixed:
                continue
        if sev not in policy.blocking_severities:
            verdict.advisory.append(v)
            continue
        age = v.age_days(today)
        grace = policy.grace_for(sev)
        # Unknown age is treated as over any window: a scanner that cannot say
        # when a CVE was published cannot vouch that it is inside the grace.
        if age is None or age > grace:
            verdict.blocking.append(v)
        else:
            verdict.advisory.append(v)
    return verdict


# ----------------------------------------------------------------- parsing --
def _date(s: Any) -> date | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None


def load_trivy(path: Path) -> list[Vulnerability]:
    """Trivy's `--format json` (fs, image or sbom scan)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[Vulnerability] = []
    for result in doc.get("Results", []) or []:
        target = str(result.get("Target", ""))
        for v in result.get("Vulnerabilities", []) or []:
            out.append(Vulnerability(
                id=str(v.get("VulnerabilityID", "")), package=str(v.get("PkgName", "")),
                installed=str(v.get("InstalledVersion", "")), fixed=str(v.get("FixedVersion", "") or ""),
                severity=str(v.get("Severity", "UNKNOWN")).upper(), published=_date(v.get("PublishedDate")),
                target=target, title=str(v.get("Title", ""))[:200]))
    return out


def load_cyclonedx(path: Path) -> list[Vulnerability]:
    """A CycloneDX 1.4+ JSON BOM carrying a `vulnerabilities` array (Trivy
    `--format cyclonedx`, Grype `-o cyclonedx-json`)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    components = {c.get("bom-ref"): c for c in doc.get("components", []) or [] if isinstance(c, dict)}
    out: list[Vulnerability] = []
    for v in doc.get("vulnerabilities", []) or []:
        ratings = v.get("ratings") or []
        sev = "UNKNOWN"
        for r in ratings:
            s = str(r.get("severity", "")).upper()
            if SEVERITY_RANK.get(s, 0) > SEVERITY_RANK.get(sev, 0):
                sev = s
        fixed = ""
        for a in v.get("affects", []) or []:
            for ver in a.get("versions", []) or []:
                if ver.get("status") == "unaffected" and ver.get("version"):
                    fixed = str(ver["version"])
        if not fixed:
            rec = (v.get("recommendation") or "")
            fixed = rec if rec.lower().startswith(("upgrade", "update")) else fixed
        ref = (v.get("affects") or [{}])[0].get("ref") if v.get("affects") else None
        comp = components.get(ref, {})
        out.append(Vulnerability(
            id=str(v.get("id", "")), package=str(comp.get("name") or ref or ""),
            installed=str(comp.get("version", "")), fixed=fixed, severity=sev,
            published=_date(v.get("published")), title=str(v.get("description", ""))[:200]))
    return out


def load_vulnerabilities(path: Path) -> list[Vulnerability]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(doc, dict) and doc.get("bomFormat") == "CycloneDX":
        return load_cyclonedx(path)
    return load_trivy(path)


# ----------------------------------------------------------------- running --
def trivy_available() -> str | None:
    return shutil.which("trivy")


def generate_sbom(scan_root: Path, out: Path, *, timeout: int = 900) -> Path | None:
    """`trivy fs --format cyclonedx` over the checkout. None when trivy is absent."""
    exe = trivy_available()
    if not exe:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "fs", "--format", "cyclonedx", "--output", str(out), "--quiet", str(scan_root)]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return out


def scan(scan_root: Path, out: Path, *, severities: tuple[str, ...] = ("CRITICAL", "HIGH", "MEDIUM", "LOW"),
         sbom: Path | None = None, timeout: int = 900) -> Path | None:
    """Trivy vulnerability scan to JSON. Scans the SBOM when given, else the tree."""
    exe = trivy_available()
    if not exe:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    sev = ",".join(severities)
    if sbom is not None and sbom.exists():
        cmd = [exe, "sbom", "--format", "json", "--severity", sev, "--output", str(out), "--quiet", str(sbom)]
    else:
        cmd = [exe, "fs", "--scanners", "vuln", "--format", "json", "--severity", sev, "--output", str(out),
               "--quiet", str(scan_root)]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return out
