"""The write path: INTENT before, DECISION at the gate, EXECUTION after.

This is the module everything else calls. The hooks call it for tool calls, and
`pf.agents.base` calls it for programmatic LLM calls, so an action is recorded
the same way whether a human is watching a Claude Code session or a Dagster
schedule is running a loop at 3am.

## Ordering is the guarantee

`intent()` must return before the action starts and `execution()` must be called
after it ends. The API is shaped to make that hard to get wrong: `action()` is a
context manager that writes INTENT on entry and EXECUTION on exit, including the
exit where the body raised. A caller who writes the three records by hand can
reorder them; a caller using `action()` cannot.

An action that appears with an INTENT and no EXECUTION is not a bug in the
ledger — it is the honest record of a process that died mid-action, and
`pf provenance verify` reports it as `dangling` rather than quietly closing it.

## Fail-open by default, fail-closed on request

If the ledger cannot be written, does the action proceed? Both answers are
defensible and they suit different organisations, so it is a setting:

    PF_PROVENANCE_ENFORCE=0   (default) record-keeping failure never blocks work
    PF_PROVENANCE_ENFORCE=1             an unrecordable action is a denied action

The default matches the existing hook, which deliberately does not block when
the platform is unimportable — a governance system whose failure mode is "the
whole team stops" gets switched off, and a governance system that is switched
off records nothing. Regulated deployments should set it to 1 and accept the
trade, which is why the flag exists rather than the choice being hardcoded.

## The database is a mirror, not the record

`chain.jsonl` is the evidence; the DuckDB tables are for querying and for the
UI. Nothing writes to DuckDB on the hot path: it is a single-writer store, and
two concurrent hooks contending for its lock would add exactly the latency and
failure surface the anchoring design avoids. `pf provenance sync` replays the
chain into DuckDB, and a mirror that disagrees with the chain loses.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pf.provenance.chain import append, chain_dir, read_all
from pf.provenance.record import Record, now

REVOKED_NAME = "revoked.json"
APPROVALS_NAME = "approvals.jsonl"


class NotRecorded(RuntimeError):
    """The action could not be written to the ledger, and enforcement is on."""


class Revoked(RuntimeError):
    """The kill switch is engaged for this actor or for the platform."""


def enforcing() -> bool:
    return os.environ.get("PF_PROVENANCE_ENFORCE", "0") not in ("0", "", "false")


def _actor() -> str:
    """Who is acting. Not authentication — attribution.

    The ledger records the claim, and the claim is only as good as whatever set
    the variable. That is a real limit and it is stated rather than papered
    over: to bind an action to a person you need a signature, which is the
    natural extension of this design once actors have keys.
    """
    return (os.environ.get("PF_ACTOR")
            or os.environ.get("CLAUDE_AGENT")
            or os.environ.get("USER")
            or "unknown")


def _session() -> str:
    return os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("PF_SESSION") or ""


# --------------------------------------------------------------------------
# Revocation — stage 02's hard stop. Independent of the gate's path rules:
# the gate answers "may this path be written", this answers "may this actor
# act at all", and an incident needs the second question answerable in one
# command without editing policy.
# --------------------------------------------------------------------------

def revoke(root: Path, *, actor: str = "*", reason: str = "") -> dict[str, Any]:
    """Engage the kill switch. `*` stops every actor."""
    d = chain_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    state = _revocations(root)
    state[actor] = {"ts": now(), "reason": reason, "by": _actor()}
    (d / REVOKED_NAME).write_text(json.dumps(state, indent=2, sort_keys=True),
                                  encoding="utf-8")
    return state


def reinstate(root: Path, *, actor: str = "*") -> dict[str, Any]:
    state = _revocations(root)
    state.pop(actor, None)
    (chain_dir(root) / REVOKED_NAME).write_text(
        json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state


def _revocations(root: Path) -> dict[str, Any]:
    p = chain_dir(root) / REVOKED_NAME
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # An unreadable kill switch is treated as engaged. This is the one
        # place the module is deliberately fail-closed regardless of the
        # enforcement flag: "I cannot tell whether you are revoked" must not
        # resolve to "carry on".
        return {"*": {"ts": now(), "reason": "revocation file unreadable",
                      "by": "system"}}


def is_revoked(root: Path, actor: str | None = None) -> tuple[bool, str]:
    state = _revocations(root)
    who = actor or _actor()
    for key in ("*", who):
        if key in state:
            entry = state[key]
            return True, (f"{key} revoked at {entry.get('ts')}: "
                          f"{entry.get('reason') or 'no reason given'}")
    return False, ""


# --------------------------------------------------------------------------
# Human oversight — the approval side of stage 02.
# --------------------------------------------------------------------------

def approve(root: Path, action_id: str, *, note: str = "") -> dict[str, Any]:
    """Record a human's approval of a held action.

    Append-only, and the approver is recorded separately from the actor: an
    approval where the two are the same identity is still written, and
    `pf provenance verify` flags it, because self-approval is a finding rather
    than something to silently refuse.
    """
    d = chain_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now(), "action_id": action_id, "approver": _actor(),
             "note": note}
    with (d / APPROVALS_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    return entry


def approvals(root: Path) -> dict[str, dict[str, Any]]:
    p = chain_dir(root) / APPROVALS_NAME
    if not p.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            out[e["action_id"]] = e
    return out


def is_approved(root: Path, action_id: str) -> bool:
    return action_id in approvals(root)


# --------------------------------------------------------------------------
# The three stages.
# --------------------------------------------------------------------------

def _write(root: Path, rec: Record) -> Record | None:
    try:
        return append(root, rec)
    except OSError as exc:
        if enforcing():
            raise NotRecorded(f"could not write the ledger: {exc}") from exc
        return None


def new_action_id() -> str:
    return uuid.uuid4().hex


def intent(root: Path, *, tool: str, target: str, summary: str,
           group: str = "", project: str = "", action_id: str | None = None,
           payload: dict[str, Any] | None = None) -> Record:
    """Stage 01 — written before anything happens.

    Raises `Revoked` when the kill switch is engaged, regardless of the
    enforcement flag: revocation that a fail-open setting could bypass is not
    revocation.
    """
    stopped, why = is_revoked(root)
    if stopped:
        raise Revoked(why)

    rec = Record(
        seq=-1, action_id=action_id or new_action_id(), stage="intent",
        ts=now(), actor=_actor(), session=_session(), group=group,
        project=project, tool=tool, target=target,
        payload={"summary": summary, **(payload or {})})
    return _write(root, rec) or rec


def decision(root: Path, action_id: str, *, verdict: str, rule: str,
             message: str = "", tool: str = "", target: str = "",
             group: str = "", project: str = "",
             payload: dict[str, Any] | None = None) -> Record:
    """Stage 02 — the gate's verdict, recorded whether it allowed or denied.

    Recording allows matters as much as recording denies. A ledger holding only
    refusals proves the gate can say no; it cannot show the gate was consulted
    for the action that caused the incident.
    """
    rec = Record(
        seq=-1, action_id=action_id, stage="decision", ts=now(),
        actor=_actor(), session=_session(), group=group, project=project,
        tool=tool, target=target,
        payload={"verdict": verdict, "rule": rule, "message": message,
                 "enforcing": enforcing(), **(payload or {})})
    return _write(root, rec) or rec


def execution(root: Path, action_id: str, *, status: str, tool: str = "",
              target: str = "", group: str = "", project: str = "",
              detail: str = "", payload: dict[str, Any] | None = None) -> Record:
    """Stage 03 — written after the action, success or failure alike."""
    rec = Record(
        seq=-1, action_id=action_id, stage="execution", ts=now(),
        actor=_actor(), session=_session(), group=group, project=project,
        tool=tool, target=target,
        payload={"status": status, "detail": detail, **(payload or {})})
    return _write(root, rec) or rec


@contextmanager
def action(root: Path, *, tool: str, target: str, summary: str,
           group: str = "", project: str = "",
           gate: tuple[str, str, str] | None = None,
           require_approval: bool = False) -> Iterator[dict[str, Any]]:
    """Record all three stages around a block of work.

    The preferred entry point, because it closes the two gaps a hand-written
    sequence leaves: an EXECUTION that never runs because the body raised, and
    an EXECUTION whose status says "ok" because nobody checked. The body gets a
    dict it can put result detail into.

        with action(root, tool="dbt", target="model.x", summary="rebuild") as a:
            a["detail"] = run_model()

    `gate` is `(verdict, rule, message)` from an already-consulted policy gate.
    A `deny` verdict raises before the body runs, so the guarded work cannot
    execute — the DECISION record is written either way.
    """
    aid = new_action_id()
    intent(root, tool=tool, target=target, summary=summary, group=group,
           project=project, action_id=aid)

    verdict, rule, message = gate or ("allow", "default", "")
    if require_approval and not is_approved(root, aid):
        verdict, rule = "hold", "human_oversight"
        message = (f"awaiting human approval — approve with "
                   f"`pf provenance approve {aid}`")

    decision(root, aid, verdict=verdict, rule=rule, message=message,
             tool=tool, target=target, group=group, project=project)

    if verdict in ("deny", "hold"):
        execution(root, aid, status="blocked", tool=tool, target=target,
                  group=group, project=project, detail=message)
        raise Revoked(message) if verdict == "deny" else NotRecorded(message)

    box: dict[str, Any] = {"action_id": aid, "detail": ""}
    try:
        yield box
    except BaseException as exc:
        execution(root, aid, status="error", tool=tool, target=target,
                  group=group, project=project,
                  detail=f"{type(exc).__name__}: {exc}"[:500])
        raise
    else:
        execution(root, aid, status="ok", tool=tool, target=target,
                  group=group, project=project, detail=str(box.get("detail", ""))[:500])


# --------------------------------------------------------------------------
# Reading back.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Correlating a PreToolUse hook with the PostToolUse hook for the same call.
#
# The two hooks are separate processes, so the action_id minted while writing
# INTENT has to survive to the process that writes EXECUTION. Claude Code
# supplies `tool_use_id` on both sides when it can, and that is used verbatim.
# When it does not, the fallback keys on (session, tool, the exact tool input),
# which is stable across the pair for the same call.
#
# The stash is deliberately not the chain: an un-claimed entry is a process
# that died between the hooks, and it should expire quietly rather than
# accumulate as evidence of nothing.
# --------------------------------------------------------------------------

PENDING_NAME = "pending.json"
PENDING_MAX = 512


def correlation_key(payload: dict[str, Any]) -> str:
    import hashlib

    tid = payload.get("tool_use_id") or payload.get("toolUseID")
    if tid:
        return str(tid)
    body = json.dumps(
        [payload.get("session_id", ""), payload.get("tool_name", ""),
         payload.get("tool_input", {})],
        sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]


def stash_action(root: Path, key: str, action_id: str) -> None:
    from pf.provenance.chain import _locked

    d = chain_dir(root)
    with _locked(d):
        p = d / PENDING_NAME
        try:
            state = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except json.JSONDecodeError:
            state = {}
        state[key] = action_id
        if len(state) > PENDING_MAX:
            # Bounded: keep the newest half. Dropping an entry costs one
            # EXECUTION its link back to its INTENT, which `verify` reports as
            # dangling — visibly wrong, rather than an unbounded file.
            state = dict(list(state.items())[-PENDING_MAX // 2:])
        p.write_text(json.dumps(state), encoding="utf-8")


def claim_action(root: Path, key: str) -> str | None:
    """Take the action_id for `key`, removing it. None if the pair was broken."""
    from pf.provenance.chain import _locked

    d = chain_dir(root)
    with _locked(d):
        p = d / PENDING_NAME
        if not p.exists():
            return None
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        aid = state.pop(key, None)
        if aid is not None:
            p.write_text(json.dumps(state), encoding="utf-8")
        return aid


def actions(root: Path) -> dict[str, dict[str, Record]]:
    """Group the flat chain into `{action_id: {stage: record}}`."""
    out: dict[str, dict[str, Record]] = {}
    for rec in read_all(root):
        out.setdefault(rec.action_id, {})[rec.stage] = rec
    return out


def dangling(root: Path) -> list[str]:
    """Actions missing a stage — started and never closed, or never gated."""
    return [aid for aid, stages in actions(root).items()
            if not {"intent", "decision", "execution"} <= set(stages)]
