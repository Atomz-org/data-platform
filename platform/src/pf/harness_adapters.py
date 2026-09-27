"""Harness dialects — each tool's hook payload in, its idea of "no" out.

`pf.agenthook` is the one implementation of every hook. What differs by tool
is only the dialect, and per harness that is two things:

    parse     the harness's stdin → a neutral `Call` (its tool names mapped
              onto Edit / Write / Bash / Read, paths pulled out of whatever
              field — or patch body — carries them)
    render    a `Verdict` → (stdout, stderr, exit code) the harness honours

Claude Code's dialect is here, because Claude's hooks are where the core came
from. Every other harness declares its own in `pf.harnesses.<name>` — its
`Adapter`, its tool vocabulary, its configs — and this module finds it there.
The helpers below are what those modules share.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf import agenthook as core
from pf.agenthook import BASH, EDIT, OTHER, READ, WRITE, Call, Verdict

Out = tuple[str, str, int]


# ----------------------------------------------------------------- helpers --
def _payload(raw: str) -> dict[str, Any]:
    try:
        v = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return v if isinstance(v, dict) else {}


def obj(v: Any) -> dict[str, Any]:
    """Tool input arrives as a dict, or — Copilot CLI — as a JSON string."""
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            d = json.loads(v)
            return d if isinstance(d, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def first(d: dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$", re.MULTILINE)

#: Tools whose input is a patch envelope rather than a path.
PATCH_TOOLS = {"apply_patch", "patch"}


def patch_paths(patch: str) -> tuple[str, ...]:
    """Every file an `apply_patch` envelope touches (Codex, Copilot, OpenCode)."""
    return tuple(dict.fromkeys(a or b for a, b in _PATCH_FILE.findall(patch or "")))


def _command(v: Any) -> str:
    if isinstance(v, list):
        # `["bash", "-lc", "<script>"]` is a script, not three words: the guard
        # has to see `git commit -n` as tokens, not as one quoted argument.
        if len(v) >= 3 and str(v[1]) in ("-c", "-lc", "-ic"):
            return str(v[2])
        return " ".join(str(x) for x in v)
    return str(v or "")


def _cwd(p: dict[str, Any]) -> Path:
    c = first(p, "cwd", "workspace_root", "project_path") or ""
    if not c:
        roots = p.get("workspace_roots") or []
        c = roots[0] if roots and isinstance(roots[0], str) else ""
    return Path(c) if c else Path.cwd()


def _paths_from(inp: dict[str, Any], name: str = "") -> tuple[str, ...]:
    if name in PATCH_TOOLS:
        return patch_paths(first(inp, "patchText", "patch", "input", "command"))
    single = first(inp, "file_path", "notebook_path", "filePath", "absolute_path", "path", "file")
    if single:
        return (single,)
    many = inp.get("paths") or inp.get("file_paths") or []
    out = [str(x) for x in many if isinstance(x, str)]
    # VS Code's multi-replace: `replacements: [{filePath, ...}, ...]`.
    for r in inp.get("replacements") or []:
        if isinstance(r, dict) and first(r, "filePath", "file_path", "path"):
            out.append(first(r, "filePath", "file_path", "path"))
    return tuple(dict.fromkeys(out))


def call(harness: str, p: dict[str, Any], name: str, inp: dict[str, Any], call_id: str = "") -> Call:
    """A neutral `Call` from one harness's tool name and input."""
    tool = tools(harness).get(name, OTHER)
    cmd = _command(inp.get("command") or inp.get("cmd") or "") if tool == BASH else ""
    paths = _paths_from(inp, name) if tool in (EDIT, WRITE, READ) else ()
    sid = first(p, "session_id", "sessionId", "sessionID", "conversation_id", "thread_id")
    key: dict[str, Any] = {"session_id": sid, "tool_name": name, "tool_input": inp}
    if call_id:
        key["tool_use_id"] = call_id
    return Call(
        harness=harness, tool=tool, paths=paths, command=cmd, cwd=_cwd(p), session_id=sid, key=key, raw_tool=name
    )


def claude_parse(harness: str) -> Callable[[dict[str, Any]], Call]:
    """The snake_case payload Claude Code introduced and most harnesses copied."""
    return lambda p: call(harness, p, first(p, "tool_name"), obj(p.get("tool_input")), first(p, "tool_use_id"))


# ---------------------------------------------------------------- dialects --
@dataclass(frozen=True)
class Adapter:
    """How one harness speaks. `parse` gets the payload; the render functions
    get the verdict. Events a harness does not have are simply not wired in
    its generated config."""

    parse: Callable[[dict[str, Any]], Call]
    deny: Callable[[Verdict], Out]
    allow: Callable[[Verdict], Out]
    ask: Callable[[Verdict], Out]
    context: Callable[[str, str], Out]  # (event, text) → session context
    ok: Callable[[dict[str, Any]], tuple[bool, str]]


def exit2(v: Verdict) -> Out:
    return "", v.message, 2


def ask_as_deny(v: Verdict) -> Out:
    """A harness with no "ask a person" answer gets a refusal that says a
    person must run it. Weaker than a prompt; stronger than letting it through."""
    return "", v.message + "\n  This harness cannot pause for approval: ask the person to run it.", 2


def native_ask(v: Verdict) -> Out:
    """For a harness that prompts a person itself, from rules `pf.harness`
    renders out of the same `ask` list. Refusing here would pre-empt that
    prompt; the harness asks."""
    return "", "", 0


def hook_specific(event: str, text: str) -> Out:
    """Claude Code / Codex / Gemini / VS Code: `hookSpecificOutput.additionalContext`."""
    if not text:
        return "", "", 0
    return json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}), "", 0


def claude_ok(p: dict[str, Any]) -> tuple[bool, str]:
    resp = p.get("tool_response")
    if isinstance(resp, dict):
        if resp.get("error"):
            return False, str(resp["error"])[:400]
        if resp.get("is_error") or resp.get("isError") or resp.get("success") is False:
            return False, str(resp.get("content") or resp)[:400]
        for key in ("filePath", "file_path", "stdout", "content"):
            if key in resp:
                return True, f"{key}={str(resp[key])[:200]}"
        return True, ""
    if isinstance(resp, str):
        return True, resp[:300]
    return True, "" if resp is None else f"tool_response was {type(resp).__name__}"


def generic_ok(p: dict[str, Any]) -> tuple[bool, str]:
    """Claude's shape, then Copilot's `toolResult.resultType`, then OpenCode's
    `output`. Unknown shapes are "ok" — an EXECUTION that claims failure
    because a field was not recognised is worse than one that could not tell."""
    tr = p.get("toolResult")
    if isinstance(tr, dict):
        failed = str(tr.get("resultType", "")).lower() in ("failure", "error", "denied")
        return (not failed), str(tr.get("textResultForLlm") or "")[:300]
    if "tool_response" in p:
        return claude_ok(p)
    if "output" in p:
        return True, str(p.get("output") or "")[:300]
    return True, ""


CLAUDE_TOOLS = {
    "Edit": EDIT,
    "MultiEdit": EDIT,
    "NotebookEdit": EDIT,
    "Write": WRITE,
    "Bash": BASH,
    "Read": READ,
}

CLAUDE = Adapter(
    parse=claude_parse("claude"),
    deny=exit2,
    allow=lambda v: (v.message, "", 0),
    ask=exit2,  # never produced: Claude applies its own permission lists
    context=lambda ev, text: (text, "", 0),  # plain stdout is added to context
    ok=claude_ok,
)


# ---------------------------------------------------------------- registry --
def adapters() -> dict[str, Adapter]:
    from pf.harnesses import specs

    return {"claude": CLAUDE, **{s.key: s.adapter for s in specs() if s.adapter is not None}}


def tools(harness: str) -> dict[str, str]:
    if harness == "claude":
        return CLAUDE_TOOLS
    from pf.harnesses import spec

    s = spec(harness)
    return dict(s.tools) if s else {}


def __getattr__(name: str) -> Any:
    """`ADAPTERS` and `TOOLS` as they stand, for callers that read them as
    constants — computed, because a harness is added by adding its module."""
    if name == "ADAPTERS":
        return adapters()
    if name == "TOOLS":
        return {h: tools(h) for h in adapters()}
    raise AttributeError(name)


def _spec(harness: str):
    from pf.harnesses import spec

    return spec(harness)


def _advice_file(c: Call) -> Path:
    import hashlib

    from pf.provenance import ledger as prov

    root = core.repo_root(c.cwd.resolve())
    key = hashlib.sha256(prov.correlation_key(c.key).encode()).hexdigest()[:24]
    return root / ".tmp" / "hook-advice" / f"{c.harness}-{key}.txt"


def _defer(c: Call, message: str) -> None:
    """A harness whose pre-tool answer cannot carry advice without also
    claiming a decision gets the blast radius on the post event instead."""
    try:
        f = _advice_file(c)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(message, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _deferred(c: Call) -> str:
    try:
        f = _advice_file(c)
        text = f.read_text(encoding="utf-8")
        f.unlink()
        return text
    except Exception:  # noqa: BLE001
        return ""


def _claude_elsewhere() -> bool:
    """Whether a *Claude* hook is really another harness that gates on its own.

    The Cursor CLI also runs `.claude/settings.json` hooks. Once Cursor's own
    config calls the core before a tool runs, answering a second time as
    "claude" would record every action twice and skip the permission lists
    only non-Claude harnesses are given. But until then the imported Claude
    hook is the only pre-action gate Cursor has, and stepping aside would let
    a denylisted edit through — so the decision follows whether a Cursor
    adapter is registered, not merely whether Cursor is the caller.
    """
    import os

    if not (os.environ.get("CURSOR_VERSION") or os.environ.get("CURSOR_PROJECT_DIR")):
        return False
    s = _spec("cursor")
    return bool(s and s.adapter is not None)


# -------------------------------------------------------------------- run --
def run(harness: str, event: str, raw: str) -> Out:
    """Dispatch one hook invocation. Unknown harness or event: allow, silently."""
    ad = adapters().get(harness)
    if ad is None or (harness == "claude" and _claude_elsewhere()):
        return "", "", 0
    s = _spec(harness)
    defer = bool(s and s.defer_advice)
    p = _payload(raw)

    if event in ("pre", "shell"):  # `shell`: the name the first Cursor config used
        c = ad.parse(p)
        v = core.pre(c)
        if v.decision == "deny":
            return ad.deny(v)
        if v.decision == "ask":
            return ad.ask(v)
        if v.message and defer:
            _defer(c, v.message)
            return "", "", 0
        return ad.allow(v)

    if event in ("post", "edit"):
        c = ad.parse(p)
        ok, detail = ad.ok(p)
        # Claude's formatter runs from the power-tools plugin; everyone else's here.
        v = core.post(c, ok=ok, detail=detail, fmt=harness != "claude")
        text = "\n".join(t for t in (_deferred(c) if defer else "", v.message) if t)
        return ad.allow(Verdict("allow", text)) if text else ("", "", 0)

    if event == "session":
        ev = s.session_event if s else "SessionStart"
        return ad.context(ev, core.session_context(_cwd(p), harness))

    if event == "stop":
        core.stop(
            _cwd(p),
            harness,
            session_id=first(p, "session_id", "sessionId", "sessionID", "conversation_id"),
            transcript=first(p, "transcript_path", "transcriptPath"),
            last_message=first(p, "last_assistant_message", "prompt_response"),
        )
        return "", "", 0

    return "", "", 0
