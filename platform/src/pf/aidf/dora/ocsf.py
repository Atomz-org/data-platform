"""Prowler findings in OCSF, normalised to the few fields the audit judges.

Prowler writes `*.ocsf.json` as a JSON array of OCSF Detection Findings; older
runs and other tools write NDJSON, one object per line. Both are read. What is
kept per finding:

    check_id     Prowler's check name (`unmapped.check_id`, else `finding_info.uid`)
    status       PASS | FAIL | MANUAL | MUTED (`status_code`, else `status`)
    severity     CRITICAL .. INFORMATIONAL, upper-cased
    provider     aws | azure | gcp | kubernetes
    resource     the first resource uid, for the report
    compliance   framework -> requirement ids, from `unmapped.compliance`

Anything else the finding carries is left in the file the audit copies beside
the matrix; the matrix cites the file, not the finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL")
_SEVERITY_IDS = {6: "CRITICAL", 5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW", 1: "INFORMATIONAL", 0: "INFORMATIONAL"}


@dataclass(frozen=True)
class Finding:
    check_id: str
    status: str
    severity: str
    provider: str = ""
    title: str = ""
    resource: str = ""
    compliance: dict[str, list[str]] | None = None

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"

    def cites(self, key: str) -> bool:
        """Does any compliance framework name on this finding contain `key`?"""
        return any(key in k.lower() for k in (self.compliance or {}))

    def requirements(self, key: str) -> set[str]:
        """Requirement ids this finding is mapped to, under every framework whose
        name contains `key` — `{"DORA-Art9"}` for a DORA-mapped IAM check."""
        out: set[str] = set()
        for k, ids in (self.compliance or {}).items():
            if key in k.lower():
                out.update(str(i) for i in ids)
        return out


def _sev(entry: dict[str, Any]) -> str:
    s = entry.get("severity")
    if isinstance(s, str) and s.strip():
        return s.strip().upper()
    sid = entry.get("severity_id")
    if isinstance(sid, int):
        return _SEVERITY_IDS.get(sid, "INFORMATIONAL")
    return "INFORMATIONAL"


def _status(entry: dict[str, Any]) -> str:
    for key in ("status_code", "status"):
        s = entry.get(key)
        if isinstance(s, str) and s.strip():
            return s.strip().upper()
    return "UNKNOWN"


def _check_id(entry: dict[str, Any], unmapped: dict[str, Any], info: dict[str, Any], provider: str) -> str:
    """The check name, from the field Prowler actually writes it to.

    Prowler 5 puts it in `metadata.event_code` (`organization_members_mfa_required`);
    our own scans and older shapes put it in `unmapped.check_id`. The
    `finding_info.uid` is the last resort and is a composite —
    `prowler-github-organization_members_mfa_required-Atomz-org-…` — so the
    provider prefix is stripped from it before it can be matched.
    """
    for candidate in (unmapped.get("check_id"), (entry.get("metadata") or {}).get("event_code"), entry.get("check_id")):
        if candidate:
            return str(candidate).strip()
    uid = str(info.get("uid") or "").strip()
    prefix = f"prowler-{provider}-" if provider else "prowler-"
    return uid[len(prefix):] if uid.startswith(prefix) else uid


def normalise(entry: dict[str, Any]) -> Finding:
    unmapped = entry.get("unmapped") or {}
    info = entry.get("finding_info") or {}
    cloud = entry.get("cloud") or {}
    resources = entry.get("resources") or []
    provider = str(cloud.get("provider") or unmapped.get("provider") or entry.get("provider") or "").lower()
    compliance = unmapped.get("compliance") if isinstance(unmapped.get("compliance"), dict) else None
    if compliance is not None:
        compliance = {str(k): [str(x) for x in (v if isinstance(v, list) else [v])] for k, v in compliance.items()}
    first = resources[0] if resources and isinstance(resources[0], dict) else {}
    return Finding(
        check_id=_check_id(entry, unmapped, info, provider),
        status=_status(entry),
        severity=_sev(entry),
        provider=provider,
        title=str(info.get("title") or entry.get("title") or "")[:200],
        resource=str(first.get("name") or first.get("uid") or "")[:200],
        compliance=compliance,
    )


def load_findings(path: Path) -> list[Finding]:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    entries: list[Any]
    if text[0] == "[":
        entries = json.loads(text)
    elif text[0] == "{" and "\n" not in text:
        doc = json.loads(text)
        entries = doc.get("findings", [doc]) if isinstance(doc, dict) else [doc]
    else:
        entries = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [normalise(e) for e in entries if isinstance(e, dict)]


def summarise(findings: list[Finding]) -> dict[str, int]:
    out = {f"fail_{s.lower()}": 0 for s in SEVERITIES}
    out.update({"total": len(findings), "pass": 0, "fail": 0, "manual": 0})
    for f in findings:
        if f.status == "PASS":
            out["pass"] += 1
        elif f.status == "FAIL":
            out["fail"] += 1
            key = f"fail_{f.severity.lower()}"
            if key in out:
                out[key] += 1
        elif f.status == "MANUAL":
            out["manual"] += 1
    return out
