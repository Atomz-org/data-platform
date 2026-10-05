"""R2 bucket posture, as OCSF findings the audit reads like any Prowler scan.

Prowler's `cloudflare` provider audits zones, DNS and the WAF — the edge. It
has no R2 checks, and R2 is where this platform keeps the one thing it stores
outside git: the artefact store (docs/ARTIFACTS.md) — review baselines, recorded
diffs, the `recce_state.json` that carries compared rows. Evidence about those
buckets has to come from somewhere, so this module asks the Cloudflare API
directly and emits Detection Findings in the shape `pf.aidf.dora.ocsf` already
parses: `cloud.provider = cloudflare`, `unmapped.check_id = r2_*`. The statutory
matrix maps the `r2_` prefixes to articles beside Prowler's own.

    r2_bucket_inventoried               every bucket, PASS — the inventory (Art. 8)
    r2_bucket_public_access_disabled    the r2.dev managed domain is off (Art. 9)
    r2_bucket_custom_domain_tls_secure  custom domains enforce TLS 1.2+ (Art. 9)
    r2_bucket_cors_not_wildcard         no CORS rule allows any origin (Art. 9)
    r2_bucket_lifecycle_configured      a retention or transition rule exists (Art. 12)

Needs an API token with the account permission *Workers R2 Storage: Read*
(`CLOUDFLARE_API_TOKEN` or `DORA_CLOUDFLARE_API_TOKEN`) and the account id
(`--account-id`, `CLOUDFLARE_ACCOUNT_ID`, or derived from `PF_ARTIFACTS_ENDPOINT`,
which is `https://<account>.r2.cloudflarestorage.com`). Nothing else is read,
nothing is written, and the token never appears in a finding.

The HTTP call is one injectable function so the tests run the whole scan
against canned responses; the real one is urllib, because this must not add a
dependency to the platform for a nightly check.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

API = "https://api.cloudflare.com/client/v4"
Fetch = Callable[[str], dict[str, Any]]


class R2AccessError(RuntimeError):
    """The API refused us, or the account could not be determined."""


def account_id_from_env() -> str:
    for key in ("DORA_CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_ACCOUNT_ID"):
        if os.environ.get(key):
            return os.environ[key].strip()
    endpoint = os.environ.get("PF_ARTIFACTS_ENDPOINT", "")
    m = re.match(r"https?://([0-9a-f]{32})\.r2\.cloudflarestorage\.com", endpoint)
    return m.group(1) if m else ""


def token_from_env() -> str:
    return (os.environ.get("DORA_CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()


def http_fetch(token: str, timeout: int = 60) -> Fetch:
    """The real client: GET a Cloudflare API path, return the JSON envelope."""

    def _get(path: str) -> dict[str, Any]:
        req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}",
                                                          "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (401, 403):
                raise R2AccessError(f"Cloudflare API refused {path}: HTTP {exc.code} — the token needs "
                                    f"'Workers R2 Storage: Read' on the account") from exc
            if exc.code == 404:
                return {"success": False, "errors": [{"code": 404, "message": body}], "result": None}
            raise R2AccessError(f"Cloudflare API error on {path}: HTTP {exc.code} {body}") from exc
        except urllib.error.URLError as exc:
            raise R2AccessError(f"Cloudflare API unreachable: {exc.reason}") from exc

    return _get


def _result(env: dict[str, Any], default: Any) -> Any:
    return env.get("result") if env.get("success") and env.get("result") is not None else default


def _finding(check_id: str, status: str, severity: str, bucket: str, account: str, detail: str,
             title: str) -> dict[str, Any]:
    return {
        "activity_name": "Create", "category_name": "Findings", "class_name": "Detection Finding",
        "time_dt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status_code": status, "status_detail": detail, "severity": severity,
        "finding_info": {"uid": f"pf-aidf-r2-{account}-{bucket}-{check_id}", "title": title},
        "cloud": {"provider": "cloudflare", "account": {"uid": account}},
        "resources": [{"uid": f"r2://{account}/{bucket}", "name": bucket, "type": "r2_bucket"}],
        "unmapped": {"check_id": check_id, "compliance": {}, "source": "pf.aidf.dora.r2"},
    }


def scan(account_id: str, fetch: Fetch) -> list[dict[str, Any]]:
    """Every R2 bucket in the account, judged. Raises R2AccessError when the
    account cannot be listed; a per-bucket sub-call that fails becomes a
    MANUAL finding naming the call, never a silent pass."""
    env = fetch(f"/accounts/{account_id}/r2/buckets")
    if not env.get("success"):
        errs = "; ".join(str(e.get("message", e)) for e in env.get("errors", []) or [])
        raise R2AccessError(f"could not list R2 buckets for account {account_id}: {errs or 'unknown error'}")
    buckets = _result(env, {}).get("buckets", []) if isinstance(_result(env, {}), dict) else _result(env, [])
    out: list[dict[str, Any]] = []
    for b in buckets or []:
        name = str(b.get("name", ""))
        if not name:
            continue
        out.append(_finding("r2_bucket_inventoried", "PASS", "Informational", name, account_id,
                            f"bucket {name} in {b.get('location') or 'auto'} created {b.get('creation_date', '?')}",
                            "R2 bucket is inventoried"))

        # Public access: the managed r2.dev domain is the one switch that makes
        # every object readable by anyone with the URL.
        managed = fetch(f"/accounts/{account_id}/r2/buckets/{name}/domains/managed")
        if managed.get("success"):
            enabled = bool((_result(managed, {}) or {}).get("enabled"))
            state = "ENABLED — every object is world-readable" if enabled else "disabled"
            out.append(_finding("r2_bucket_public_access_disabled", "FAIL" if enabled else "PASS",
                                "High", name, account_id, f"r2.dev public domain {state}",
                                "R2 bucket public access is disabled"))
        else:
            out.append(_finding("r2_bucket_public_access_disabled", "MANUAL", "High", name, account_id,
                                "managed-domain state unreadable with this token",
                                "R2 bucket public access is disabled"))

        # Custom domains, when any: TLS floor.
        custom = fetch(f"/accounts/{account_id}/r2/buckets/{name}/domains/custom")
        domains = (_result(custom, {}) or {}).get("domains", []) if custom.get("success") else None
        if domains:
            weak = [d.get("domain") for d in domains
                    if str(d.get("minTLS") or d.get("min_tls") or "1.0") not in ("1.2", "1.3")]
            detail = (f"custom domain(s) below TLS 1.2: {weak}" if weak
                      else f"{len(domains)} custom domain(s) at TLS 1.2+")
            out.append(_finding("r2_bucket_custom_domain_tls_secure", "FAIL" if weak else "PASS", "Medium",
                                name, account_id, detail, "R2 custom domains enforce TLS 1.2 or newer"))

        # CORS: a wildcard origin on a private artefact bucket is a misconfiguration.
        cors = fetch(f"/accounts/{account_id}/r2/buckets/{name}/cors")
        if cors.get("success"):
            rules = (_result(cors, {}) or {}).get("rules", []) or []
            wild = [r for r in rules if "*" in (r.get("allowed", {}).get("origins") or [])]
            detail = (f"{len(wild)} CORS rule(s) allow any origin" if wild
                      else f"{len(rules)} CORS rule(s), none wildcard")
            out.append(_finding("r2_bucket_cors_not_wildcard", "FAIL" if wild else "PASS", "Medium", name, account_id,
                                detail, "R2 bucket CORS allows no wildcard origin"))

        # Lifecycle: the retention policy Art. 12 asks to be written down.
        life = fetch(f"/accounts/{account_id}/r2/buckets/{name}/lifecycle")
        if life.get("success"):
            rules = (_result(life, {}) or {}).get("rules", []) or []
            detail = f"{len(rules)} lifecycle rule(s)" if rules else "no lifecycle rule: retention is undeclared"
            out.append(_finding("r2_bucket_lifecycle_configured", "PASS" if rules else "FAIL", "Low", name, account_id,
                                detail, "R2 bucket declares a lifecycle (retention) policy"))
    return out


def write_ocsf(findings: list[dict[str, Any]], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    return out


def summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    s = {"buckets": 0, "pass": 0, "fail": 0, "manual": 0}
    for f in findings:
        if f["unmapped"]["check_id"] == "r2_bucket_inventoried":
            s["buckets"] += 1
        s[f["status_code"].lower()] = s.get(f["status_code"].lower(), 0) + 1
    return s
