"""Trace log — everything an agent understood, intended, asked, called and got.

Every agentic step in this platform writes to one place:

    logs/trace/<YYYY-MM-DD>/<kind>-<name>-<id>.jsonl      one run, one file
    logs/trace/index.jsonl                                one line per run

A run is a CLI command, a loop execution, a proposal chain or a question. Inside
it, events are appended as they happen, so a run that dies halfway still has
everything up to the death. The events are typed by what a reader asks for:

    intent         why this step exists (the routed agent's purpose, the loop's subject)
    understanding  what the agent took the input to mean — its own words, from
                   the schema field every agent now fills in
    request        the model call: model, params, the user prompt in full, a
                   hash and length of the cached system prefix (not the prefix —
                   it is byte-identical across runs and lives in the repo)
    response       the typed result in full, usage, stop reason, latency
    tool_call      a tool the agent chose, with its arguments
    tool_result    what the tool returned (clipped at TOOL_CLIP)
    step           a deterministic stage (gate, worktree, impact, memory …)
    finding        one loop finding, as written to the ledger
    proposal       what a loop proposed and what `actions` did with it
    outcome        the run's final status
    error          an exception, with the step it happened in

## Why JSONL on disk and not the tracking DB

The tracking DB (`pf.obs`) holds *counts* — tokens, cost, status — and is
queried for dashboards. A trace is a *transcript*, read one run at a time when
something went wrong, and a prompt body does not belong in a column. The file
is also what you attach to an issue, and what an eval can replay.

## Secrets

The user prompt is logged verbatim because it is the thing you need when an
answer is wrong. It is built from project files, never from credentials, and
the gate denies every credential path to the agents that could read one. Tool
results pass through `redact()` anyway: anything shaped like a key is masked.

`PF_TRACE=0` disables writing; nothing else changes.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOOL_CLIP = 6000
_SECRET = re.compile(r"(?i)((?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*)(\S+)")

_current: contextvars.ContextVar[Trace | None] = contextvars.ContextVar("pf_trace", default=None)


def enabled() -> bool:
    return os.environ.get("PF_TRACE", "1") not in ("0", "false", "no")


def trace_dir(root: Path) -> Path:
    return root / "logs" / "trace"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: m.group(1) + "***", text)


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


@dataclass
class Trace:
    root: Path
    kind: str              # command | loop | proposal | ask | agent
    name: str
    group: str = ""
    project: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started: str = field(default_factory=_now)
    path: Path | None = None
    events: int = 0
    parent: str = ""
    _token: Any = None

    def __post_init__(self) -> None:
        if not enabled():
            return
        day = self.started[:10]
        d = trace_dir(self.root) / day
        d.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.name)[:60]
        self.path = d / f"{self.kind}-{safe}-{self.id}.jsonl"
        self.event("start", kind=self.kind, name=self.name, group=self.group,
                   project=self.project, parent=self.parent)

    # -- writing ----------------------------------------------------------
    def event(self, type_: str, **payload: Any) -> None:
        if self.path is None:
            return
        row = {"ts": _now(), "run": self.id, "type": type_} | _jsonable(payload)
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=repr) + "\n")
            self.events += 1
        except OSError:
            self.path = None  # a full disk must not take an agent down

    def intent(self, what: str, **ctx: Any) -> None:
        self.event("intent", intent=what, **ctx)

    def understanding(self, text: str, **ctx: Any) -> None:
        self.event("understanding", understanding=text, **ctx)

    def step(self, name: str, status: str = "ok", **ctx: Any) -> None:
        self.event("step", step=name, status=status, **ctx)

    def request(self, *, agent: str, model: str, params: dict[str, Any],
                system: list[dict[str, Any]], user: str, schema: str = "") -> None:
        text = "\n".join(b.get("text", "") for b in system if isinstance(b, dict))
        self.event("request", agent=agent, model=model,
                   params={k: v for k, v in params.items()
                           if k not in ("system", "messages", "output_format", "tools")},
                   system_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                   system_chars=len(text),
                   cache_marker=any("cache_control" in b for b in system if isinstance(b, dict)),
                   schema=schema, user=redact(user))

    def response(self, *, agent: str, parsed: Any, usage: dict[str, Any],
                 stop_reason: str = "", ms: int = 0) -> None:
        self.event("response", agent=agent, parsed=_jsonable(parsed), usage=usage,
                   stop_reason=stop_reason, ms=ms)
        u = getattr(parsed, "understanding", None)
        if isinstance(u, str) and u:
            self.understanding(u, agent=agent)

    def tool_call(self, name: str, args: dict[str, Any], **ctx: Any) -> None:
        self.event("tool_call", tool=name, args=_jsonable(args), **ctx)

    def tool_result(self, name: str, result: str, **ctx: Any) -> None:
        r = redact(result)
        self.event("tool_result", tool=name, chars=len(result),
                   result=r if len(r) <= TOOL_CLIP else r[:TOOL_CLIP] + "…", **ctx)

    def finding(self, text: str, **ctx: Any) -> None:
        self.event("finding", finding=text, **ctx)

    def proposal(self, proposal: Any, outcome: Any) -> None:
        self.event("proposal", proposal=_jsonable(proposal), outcome=_jsonable(outcome))

    def error(self, exc: BaseException, step: str = "") -> None:
        self.event("error", step=step, error=f"{type(exc).__name__}: {exc}"[:800])

    def close(self, outcome: str = "ok", **ctx: Any) -> None:
        self.event("outcome", outcome=outcome, events=self.events, **ctx)
        if self.path is not None:
            idx = trace_dir(self.root) / "index.jsonl"
            try:
                with idx.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": self.started, "run": self.id, "kind": self.kind,
                        "name": self.name, "group": self.group, "project": self.project,
                        "outcome": outcome, "events": self.events,
                        "path": str(self.path.relative_to(self.root)).replace("\\", "/"),
                        "parent": self.parent,
                    }) + "\n")
            except OSError:
                pass

    # -- context ------------------------------------------------------------
    def __enter__(self) -> Trace:
        self._token = _current.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        if exc is not None:
            self.error(exc)
            self.close("error")
        else:
            self.close()
        if self._token is not None:
            _current.reset(self._token)


def start(root: Path, kind: str, name: str, *, group: str = "", project: str = "") -> Trace:
    """Open a run. Nested inside another, it records the parent id."""
    parent = _current.get()
    return Trace(root=root, kind=kind, name=name, group=group, project=project,
                 parent=parent.id if parent else "")


def current() -> Trace | None:
    return _current.get()


class _Null:
    """What `get()` returns outside any run: every method is a no-op."""

    def __getattr__(self, _: str):  # noqa: ANN204
        return lambda *a, **k: None


def get() -> Any:
    """The active trace, or a silent stand-in. Callers never check for None."""
    return _current.get() or _Null()


def decision(root: Path, name: str, *, group: str = "", project: str = "",
             **payload: Any) -> None:
    """One governance act, always logged — whoever's entry point it came through.

    Promotions, demotions, reverts, memory edits and proposal resolutions are
    the platform's *decisions*: the moments where autonomy changes hands. Each
    one gets its own single-event trace file (kind `decision`), so `pf logs
    list --kind decision` is the audit trail of judgement, separate from the
    transcripts of work. If a run is already open, the decision is also
    recorded inside it, linked by the parent id.
    """
    active = _current.get()
    if active is not None:
        active.event("decision", decision=name, **payload)
    t = Trace(root=root, kind="decision", name=name, group=group, project=project,
              parent=active.id if active else "")
    t.event("decision", decision=name, **payload)
    t.close("recorded")


# --------------------------------------------------------------- reading ----
def index(root: Path, limit: int = 50, **where: str) -> list[dict[str, Any]]:
    p = trace_dir(root) / "index.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if all(not v or r.get(k) == v for k, v in where.items()):
            rows.append(r)
    return rows[-limit:]


def read(root: Path, run_id: str) -> list[dict[str, Any]]:
    for r in index(root, limit=10_000):
        if r["run"] == run_id or r["run"].startswith(run_id):
            p = root / r["path"]
            if not p.exists():
                return []
            out = []
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return out
    return []


def render(events: list[dict[str, Any]]) -> str:
    """A transcript a person can read: one line per event, payload summarised."""
    lines = []
    for e in events:
        t = e["type"]
        ts = e["ts"][11:23]
        if t == "start":
            lines.append(f"{ts}  ▶ {e['kind']} {e['name']} {e.get('group','')}/{e.get('project','')}")
        elif t == "intent":
            lines.append(f"{ts}  intent: {e['intent']}")
        elif t == "understanding":
            lines.append(f"{ts}  understood: {e['understanding']}")
        elif t == "request":
            lines.append(f"{ts}  → {e['agent']} @ {e['model']} ({len(e['user'])} chars, "
                         f"schema {e.get('schema') or '-'}, cache {'on' if e.get('cache_marker') else 'off'})")
        elif t == "response":
            u = e.get("usage") or {}
            lines.append(f"{ts}  ← {e['agent']} {e.get('stop_reason') or 'ok'} "
                         f"{u.get('input_tokens', 0)}+{u.get('output_tokens', 0)}t {e.get('ms', 0)}ms")
        elif t == "tool_call":
            lines.append(f"{ts}  ⚙ {e['tool']}({json.dumps(e.get('args') or {})[:160]})")
        elif t == "tool_result":
            lines.append(f"{ts}    ↳ {e.get('chars', 0)} chars: {str(e.get('result', ''))[:120]!r}")
        elif t == "step":
            extra = {k: v for k, v in e.items() if k not in ("ts", "run", "type", "step", "status")}
            lines.append(f"{ts}  · {e['step']} [{e['status']}] {json.dumps(extra, default=str)[:160] if extra else ''}")
        elif t == "finding":
            lines.append(f"{ts}  • {e['finding']}")
        elif t == "proposal":
            o = e.get("outcome") or {}
            where = o.get("pr_url") or o.get("branch") or ""
            lines.append(f"{ts}  ↗ proposal {o.get('proposal_id')} {o.get('status')} {where}")
        elif t == "error":
            lines.append(f"{ts}  ✗ {e.get('step', '')} {e['error']}")
        elif t == "decision":
            extra = {k: v for k, v in e.items() if k not in ("ts", "run", "type", "decision")}
            lines.append(f"{ts}  ⚖ {e['decision']} {json.dumps(extra, default=str)[:220]}")
        elif t == "question":
            lines.append(f"{ts}  ? {e.get('question', '')}  ({'direct' if e.get('direct') else 'live'})")
        elif t == "answer":
            a = e.get("answer") or {}
            lines.append(f"{ts}  = {str(a.get('answer', ''))[:200]!r} via {a.get('metrics')} "
                         f"{'covered' if a.get('covered') else 'NOT covered'}")
        elif t == "turn":
            lines.append(f"{ts}  ↻ turn {e.get('turn')} {e.get('stop_reason', '')}")
        elif t == "outcome":
            lines.append(f"{ts}  ■ {e['outcome']} ({e.get('events', 0)} events)")
        else:
            lines.append(f"{ts}  {t}")
    return "\n".join(lines)
