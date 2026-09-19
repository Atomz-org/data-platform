"""Delivery: where an answer, a finding or a proposal goes when a person is not
sitting at the terminal that produced it.

One mechanism, an incoming webhook per group, configured in the group's
`notify.yaml` or by environment:

    groups/<group>/notify.yaml      channels: {default: <url>, loops: <url>, ask: <url>}
    PF_NOTIFY_WEBHOOK               overrides every channel (CI, a laptop)

Slack and Teams both accept `{"text": ...}` on an incoming webhook, so the
payload is deliberately the lowest common denominator. Nothing here depends on
a chat SDK; `urllib` is enough and is always installed.

Secrets: the webhook URL is a credential, so the scaffolded file names an
environment variable (`${PF_NOTIFY_WEBHOOK_ACME}`) rather than holding a URL.
A group that wants a literal URL may write one, and then should not commit it.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

TIMEOUT_S = 10


def webhook_for(root: Path, group: str, channel: str = "default") -> str:
    env = os.environ.get("PF_NOTIFY_WEBHOOK")
    if env:
        return env
    f = root / "groups" / group / "notify.yaml"
    if not f.exists():
        return ""
    doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    chans = doc.get("channels") or {}
    for key in (channel, "default"):
        url = _expand(str(chans.get(key) or ""))
        if url:
            return url
    return ""


def _expand(value: str) -> str:
    """`${VAR}` -> the environment, else empty. A literal URL is passed through,
    but the scaffolded file never contains one."""
    m = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", value.strip())
    if m:
        return os.environ.get(m.group(1), "")
    return value.strip()


def post(url: str, text: str, *, blocks: list[dict[str, Any]] | None = None) -> tuple[bool, str]:
    """POST to an incoming webhook. Returns (ok, detail). Never raises."""
    if not url:
        return False, "no webhook configured"
    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 — https webhook
            return 200 <= resp.status < 300, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def notify(root: Path, group: str, text: str, *, channel: str = "default") -> tuple[bool, str]:
    return post(webhook_for(root, group, channel), text)


# ------------------------------------------------------------ renderers ----
def render_answer(result: Any, group: str, project: str) -> str:
    a = result.answer
    head = f"*{group}/{project}* · _{result.question}_"
    body = a.answer
    meta = []
    if a.metrics:
        meta.append("metric: `" + "`, `".join(a.metrics) + "`")
    if a.group_by:
        meta.append("by " + ", ".join(a.group_by))
    if a.where:
        meta.append(f"where `{a.where}`")
    if result.page:
        meta.append(f"page: `{result.page}`")
    if not a.covered and a.missing_definition:
        meta.append(f"_no metric covers this — needs: {a.missing_definition}_")
    return "\n".join([head, body, " · ".join(meta)] + [f"caveat: {c}" for c in a.caveats])


def render_run(run: Any) -> str:
    icon = {"ok": "•", "noop": "✓", "proposed": "↗", "gate_blocked": "⛔",
            "error": "✗", "escalated": "‼", "circuit_open": "⏏"}.get(run.outcome, "•")
    lines = [f"{icon} *{run.loop}* · {run.group}/{run.project} · {run.outcome} · {run.level}"]
    lines += [f"  - {f}" for f in run.findings[:8]]
    for p in run.proposals:
        where = p.get("pr_url") or p.get("branch") or p.get("path", "")
        lines.append(f"  ↗ proposal {p['proposal_id']} {p['status']}: {where}")
    if run.message:
        lines.append(f"  _{run.message}_")
    return "\n".join(lines)
