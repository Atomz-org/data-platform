#!/usr/bin/env python3
"""Claude Code PostToolUse hook — stage 03 of the provenance chain.

Closes the action `pre_tool_use.py` opened: writes EXECUTION with what actually
happened, linked to the same `action_id` by the correlation key both hooks
compute from the tool call.

This hook never blocks. PostToolUse runs after the tool has already changed the
world, so a non-zero exit here cannot prevent anything — it would only inject a
misleading error into the transcript for work that succeeded. Everything is
best-effort and silent on failure; `pf provenance verify` is what reports the
gaps, and an action left without an EXECUTION is visible there as dangling.

exit 0 always.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MUTATING = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def _outcome(payload: dict) -> tuple[str, str]:
    """Read success or failure out of the tool response.

    The shape of `tool_response` varies by tool — a dict with `success`, a dict
    carrying `error`, a plain string, or nothing at all. Unknown shapes are
    recorded as "ok" with the raw type noted rather than guessed at: an
    EXECUTION that claims failure because the parser did not recognise a field
    is worse than one that says plainly it could not tell.
    """
    resp = payload.get("tool_response")
    if resp is None:
        return "ok", ""
    if isinstance(resp, dict):
        if resp.get("error"):
            return "error", str(resp["error"])[:400]
        if resp.get("is_error") or resp.get("isError"):
            return "error", str(resp.get("content") or resp)[:400]
        if resp.get("success") is False:
            return "error", str(resp)[:400]
        for key in ("filePath", "file_path", "stdout", "content"):
            if key in resp:
                return "ok", f"{key}={str(resp[key])[:200]}"
        return "ok", ""
    if isinstance(resp, str):
        return "ok", resp[:300]
    return "ok", f"tool_response was {type(resp).__name__}"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool = payload.get("tool_name", "")
    scope_all = os.environ.get("PF_PROVENANCE_SCOPE", "mutating") == "all"
    if tool not in MUTATING and not scope_all:
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd())
    root = repo_root(cwd.resolve())
    sys.path.insert(0, str(root / "platform" / "src"))

    try:
        from pf.loops.gate import project_for
        from pf.provenance import ledger as prov
    except Exception:
        return 0

    try:
        key = prov.correlation_key(payload)
        action_id = prov.claim_action(root, key)
        if action_id is None:
            # No INTENT to close. Either the pre-hook did not run (tool not in
            # scope then, or the platform was unimportable) or the pair was
            # broken. Writing a bare EXECUTION would manufacture an action that
            # was never gated — exactly the finding the verifier exists to
            # raise — so this stays silent instead.
            return 0

        tool_input = payload.get("tool_input") or {}
        file_path = tool_input.get("file_path", "")
        rel = str(tool_input.get("command", ""))[:400] if tool == "Bash" else file_path
        if file_path:
            try:
                rel = str(Path(file_path).resolve().relative_to(root))
            except ValueError:
                rel = file_path

        proj = project_for(str(cwd), root)
        group, project = (proj[0], proj[1]) if proj else ("", "")

        status, detail = _outcome(payload)
        prov.execution(root, action_id, status=status, tool=tool, target=rel,
                       group=group, project=project, detail=detail)
    except Exception:
        # PostToolUse cannot undo the tool call, so it must never turn a
        # successful edit into a visible error.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
