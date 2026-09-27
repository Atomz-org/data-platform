"""The agent hooks, once — every harness reaches the same gate through an adapter.

Claude Code was the only tool here whose actions were *stopped*, because it was
the only one with hooks when the hooks were written. That is no longer true of
the tools this repo is used with: Codex, Gemini CLI, Copilot, Cursor and
OpenCode all run a command before a tool call, and all of them can refuse it.
What they do not share is a payload shape, a tool vocabulary, or a way of
saying "no". So this module is split the way the MCP layer already is:

    one core        `pre`, `post`, `session_context`, `stop` — the gate, the
                    provenance chain, the permission rules, the formatter, the
                    turn-one context and the session capture. Written against a
                    neutral `Call`, never against a vendor payload.

    one adapter     `platform/hooks/agent_hook.py <harness> <event>` parses that
    per harness     harness's stdin into a `Call`, runs the core, and renders
                    the `Verdict` in that harness's dialect (an exit code, a
                    `permissionDecision`, a `{"permission": "deny"}`, a thrown
                    error in OpenCode's plugin).

Claude Code goes through the same core. Two gates that agree today disagree the
first time one of them is edited; one gate reached six ways cannot.

## Permissions are a source, not a Claude feature

`.claude/settings.json` (and each project's) carries the deny/ask lists — no
reading `.env`, no writing `vendor/`, a person approves `git push`. Claude Code
applies them itself. For every other harness the core applies them, read from
the same files, so there is one list to review and no per-tool copy to drift.
`Bash(...)` rules match a command prefix per shell segment; `Read`/`Edit`/
`Write` rules match paths the way Claude resolves them — relative to the
directory holding `.claude/`, `**/` anywhere, `//` absolute, `~/` home.

## Fail open on our bugs, closed on policy

Every entry point swallows its own exceptions and allows: a hook that crashes
closed blocks every tool call in the editor, which gets the hook removed, which
enforces nothing. A *policy* refusal — the gate, a revoked actor, an enforced
provenance write — is never swallowed.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# ------------------------------------------------------------------ model --
#: The neutral tool vocabulary. Every adapter maps its harness's names onto
#: these; anything it cannot map is `Other` and passes through unrecorded.
EDIT, WRITE, BASH, READ, OTHER = "Edit", "Write", "Bash", "Read", "Other"

#: Recorded in the provenance chain. Reads are not, by default — a chain in
#: which every file view is an action buries the writes that matter.
MUTATING = {EDIT, WRITE, BASH}
#: Path-gated by `gate.yaml`. Bash is recorded but not path-gated: pretending a
#: command string is a path produces confident, wrong verdicts.
GATED = {EDIT, WRITE}

Decision = Literal["allow", "deny", "ask"]


def _no_post(harness: str) -> bool:
    """A harness with no post-tool event gets the gate but writes no
    provenance: an INTENT nothing will close is a dangling action, which is
    the verifier's finding for a crash — a false record, not a partial one."""
    try:
        from pf.harnesses import spec

        s = spec(harness)
        return bool(s and s.no_post)
    except Exception:  # noqa: BLE001
        return False


@dataclass
class Call:
    """One tool call, as every harness can describe it."""

    harness: str
    tool: str  # EDIT | WRITE | BASH | READ | OTHER
    paths: tuple[str, ...] = ()
    command: str = ""
    cwd: Path = field(default_factory=Path.cwd)
    session_id: str = ""
    #: What the correlation key is computed from. Pre and post must hash the
    #: same thing, so it is the harness's *raw* tool name and input, plus its
    #: call id when it has one.
    key: dict[str, Any] = field(default_factory=dict)
    raw_tool: str = ""


@dataclass
class Verdict:
    decision: Decision = "allow"
    #: Shown to the agent. On deny, why; on allow, advisory context (a blast
    #: radius, a formatter complaint) — empty means say nothing.
    message: str = ""


ALLOW = Verdict()


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def _import_platform(root: Path) -> None:
    src = str(root / "platform" / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def rel_to(root: Path, path: str, cwd: Path) -> str:
    if not path:
        return path
    p = Path(path)
    p = p if p.is_absolute() else cwd / p
    try:
        return str(p.resolve().relative_to(root))
    except (ValueError, OSError):
        return path


# ------------------------------------------------------------ --no-verify --
#: Flags whose *next* token is a value and must not be inspected.
_TAKES_VALUE = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "--author", "--date"}


def bypasses_hooks(command: str) -> bool:
    """True when `command` is a git commit/push that skips hooks.

    Flag-position-aware: it skips the values of `-m`, `-F`, `--message` and
    friends, so a commit message that *mentions* `--no-verify` is not refused.
    `-n` is no-verify for commit only; for push it is `--dry-run`.
    """
    try:
        toks = shlex.split(command)
    except ValueError:
        toks = command.split()
    for i, t in enumerate(toks):
        if t != "git":
            continue
        seg = toks[i + 1 :]
        sub = next((s for s in seg if not s.startswith("-")), "")
        if sub not in {"commit", "push"}:
            continue
        skip = False
        for s in seg:
            if skip:
                skip = False
                continue
            if s in _TAKES_VALUE:
                skip = True
                continue
            if s.startswith(("-m", "-F")) and len(s) > 2 and not s.startswith("--"):
                continue  # `-mMessage` / `-am "..."` style, value attached
            if s in {"--no-verify", "--no-verify=true"}:
                return True
            if sub == "commit" and s == "-n":
                return True
        if sub == "commit" and any(
            s.startswith("-") and not s.startswith("--") and "n" in s[1:] and s not in _TAKES_VALUE for s in seg
        ):
            return True  # bundled short flags: `-an`, `-na`
    return False


NO_VERIFY = (
    "BLOCKED — `--no-verify` skips the pre-commit gate. gate.yaml's denylist and\n"
    "maxFiles are enforced there; that flag walks past both. Commit without it;\n"
    "if the gate is wrong, say why in the commit message and let a person decide.\n"
)


# ------------------------------------------------------------ permissions --
@dataclass(frozen=True)
class Rule:
    kind: str  # Read | Edit | Write | Bash
    pattern: str
    base: Path  # the directory holding `.claude/`


_RULE = re.compile(r"^(Read|Edit|Write|Bash)\((.*)\)$")


def _settings_files(root: Path, cwd: Path) -> list[Path]:
    """The root settings, then the project's when the session is inside one —
    the same two Claude Code would load for a session started there."""
    out = [root / ".claude" / "settings.json"]
    for p in [cwd, *cwd.parents]:
        if p == root or root not in p.parents:
            break
        s = p / ".claude" / "settings.json"
        if s.is_file():
            out.append(s)
            break
    return [p for p in out if p.is_file()]


def permission_rules(root: Path, cwd: Path) -> dict[str, list[Rule]]:
    out: dict[str, list[Rule]] = {"deny": [], "ask": []}
    for f in _settings_files(root, cwd.resolve()):
        try:
            perms = (json.loads(f.read_text(encoding="utf-8")) or {}).get("permissions") or {}
        except (OSError, json.JSONDecodeError):
            continue
        for level in out:
            for spec in perms.get(level) or []:
                m = _RULE.match(str(spec).strip())
                if m:
                    out[level].append(Rule(m.group(1), m.group(2), f.parent.parent))
    return out


def _glob_re(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts) + r"\Z")


def path_matches(rule: Rule, path: Path) -> bool:
    pat = rule.pattern
    target = os.path.normpath(str(path))
    if pat.startswith("**/"):
        return bool(_glob_re(pat).search(target)) or bool(_glob_re(pat[3:]).match(Path(target).name))
    if pat.startswith("//"):
        absolute = pat[1:]
    elif pat.startswith("~/"):
        absolute = str(Path.home() / pat[2:])
    else:
        absolute = os.path.normpath(str(rule.base / pat))
        if pat.endswith(("/**", "**")):
            absolute = absolute.rstrip("*").rstrip("/") + "/**"
    return bool(_glob_re(absolute).match(target))


_SEGMENT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def command_matches(rule: Rule, command: str) -> bool:
    pat = rule.pattern
    prefix, star = (pat[:-2], True) if pat.endswith(":*") else (pat, False)
    for seg in _SEGMENT.split(command):
        seg = seg.strip()
        if not seg:
            continue
        if seg == prefix or (star and (seg.startswith(prefix + " ") or seg == prefix)):
            return True
    return False


def permission(call: Call, root: Path) -> Verdict:
    """What `.claude/settings.json` says about this call, for harnesses that do
    not read it themselves. Deny wins over ask; nothing here grants."""
    rules = permission_rules(root, call.cwd)
    kinds = {READ: {"Read"}, EDIT: {"Edit", "Write"}, WRITE: {"Edit", "Write"}}.get(call.tool, set())
    for level in ("deny", "ask"):
        for r in rules[level]:
            hit = ""
            if call.tool == BASH and r.kind == "Bash" and command_matches(r, call.command):
                hit = call.command[:120]
            elif r.kind in kinds:
                for p in call.paths:
                    ap = Path(p) if Path(p).is_absolute() else call.cwd / p
                    if path_matches(r, ap.resolve()):
                        hit = p
                        break
            if hit:
                spec = f"{r.kind}({r.pattern})"
                if level == "deny":
                    return Verdict("deny", f"BLOCKED by permissions.deny [{spec}]\n  {hit}")
                return Verdict("ask", f"{spec} needs a person's approval\n  {hit}")
    return ALLOW


# -------------------------------------------------------------------- pre --
def pre(call: Call, root: Path | None = None) -> Verdict:
    """Before the tool runs: permissions, INTENT, the gate, DECISION.

    INTENT is written before the gate is consulted, so a denied action still
    leaves evidence of what was attempted. A gate that only logs its refusals
    can prove it said no; it cannot prove it was ever asked.
    """
    root = root or repo_root(call.cwd.resolve())
    try:
        return _pre(call, root)
    except Exception:  # noqa: BLE001 — never fail closed on our own bug
        return ALLOW


def _pre(call: Call, root: Path) -> Verdict:
    if call.tool == BASH and bypasses_hooks(call.command):
        return Verdict("deny", NO_VERIFY)

    # Claude Code applies its own settings; every other tool gets them here.
    if call.harness != "claude":
        v = permission(call, root)
        if v.decision != "allow":
            return v

    scope_all = os.environ.get("PF_PROVENANCE_SCOPE", "mutating") == "all"
    if call.tool not in MUTATING and not scope_all:
        return ALLOW
    rels = tuple(rel_to(root, p, call.cwd) for p in call.paths)
    target = ",".join(rels) if rels else call.command[:400]
    if not target:
        return ALLOW

    _import_platform(root)
    try:
        from pf.loops.gate import check_path, nodes_for, project_for
    except Exception:  # noqa: BLE001
        return ALLOW
    try:
        from pf.provenance import ledger as prov
    except Exception:  # noqa: BLE001
        prov = None  # degrades recording, never enforcement
    if _no_post(call.harness):
        prov = None

    proj = project_for(str(call.cwd), root)
    group, project = (proj[0], proj[1]) if proj else ("", "")
    tool = call.tool

    action_id = None
    if prov is not None:
        try:
            summary = f"{tool} {', '.join(Path(r).name for r in rels)}" if rels else f"{tool} {target[:80]}"
            rec = prov.intent(
                root,
                tool=tool,
                target=target,
                summary=summary[:200],
                group=group,
                project=project,
                payload={"cwd": str(call.cwd), "session": call.session_id, "harness": call.harness},
            )
            action_id = rec.action_id
            prov.stash_action(root, prov.correlation_key(call.key), action_id)
        except prov.Revoked as exc:
            return Verdict(
                "deny", f"REVOKED — agent action refused\n  {exc}\n  Reinstate with `pf provenance reinstate`."
            )
        except prov.NotRecorded as exc:
            return Verdict("deny", f"BLOCKED — action could not be recorded and PF_PROVENANCE_ENFORCE=1\n  {exc}")
        except Exception:  # noqa: BLE001
            action_id = None

    def record(verdict: str, rule: str, message: str) -> None:
        if prov is None or action_id is None:
            return
        with contextlib.suppress(Exception):
            prov.decision(
                root,
                action_id,
                verdict=verdict,
                rule=rule,
                message=message,
                tool=tool,
                target=target,
                group=group,
                project=project,
            )

    if tool not in GATED:
        # "no rule applied" and "a rule allowed it" are different facts.
        record("allow", "ungated", f"{tool} is not path-gated")
        return ALLOW

    # `in_project` is a property of the *session*, not of the file.
    results = [check_path(r, root, in_project=proj is not None) for r in rels]
    blocked = next((r for r in results if r.blocked), None)
    worst = blocked or next((r for r in results if r.verdict == "warn"), None) or (results[0] if results else None)
    if worst is not None:
        record(worst.verdict, worst.rule, worst.message)

    if blocked is not None:
        if prov is not None and action_id is not None:
            with contextlib.suppress(Exception):
                prov.execution(
                    root,
                    action_id,
                    status="blocked",
                    tool=tool,
                    target=target,
                    group=group,
                    project=project,
                    detail=f"{blocked.rule}: {blocked.message}",
                )
                prov.claim_action(root, prov.correlation_key(call.key))
        return Verdict("deny", f"BLOCKED by gate.yaml [{blocked.rule}]\n  {blocked.path}\n  {blocked.message}")

    notes = [_blast_radius(r.path, proj, root, nodes_for) for r in results if r.verdict == "warn"]
    return Verdict("allow", "\n".join(n for n in notes if n))


def _blast_radius(rel: str, proj, root: Path, nodes_for) -> str:
    nodes = nodes_for(rel)
    name = Path(rel).name
    if not proj:
        return f"⚠ {rel} is impact-gated; it is outside any project, so no graph applies."
    group, project, pdir = proj
    if not nodes:
        return (
            f"⚠ {name} is impact-gated but resolved to no graph node. If it is a new model, run "
            f"`pf kg build {group} {project}` then `pf impact {group} {project} model:{Path(rel).stem}`."
        )
    gp = pdir / "kg" / "graph.duckdb"
    if not gp.exists():
        return (
            f"⚠ NO BLAST RADIUS CHECKED for {name} — {group}/{project} has no knowledge graph at "
            f"kg/graph.duckdb, so the impact gate is inert.\n  This edit is allowed, but nothing "
            f"verified what it breaks.\n  Build the index: `pf kg build {group} {project}`"
        )
    try:
        from pf.kg.impact import impact_of_many

        report = impact_of_many(gp, nodes)
        if report.total:
            return f"⚠ Blast radius of editing {name}:\n" + report.render()
    except Exception:  # noqa: BLE001
        pass
    return ""


# ------------------------------------------------------------------- post --
def post(call: Call, *, ok: bool = True, detail: str = "", root: Path | None = None, fmt: bool = True) -> Verdict:
    """After the tool ran: EXECUTION, then the formatter. Never blocks — the
    tool has already changed the world; a non-zero exit here would only put a
    misleading error in front of the agent for work that succeeded."""
    root = root or repo_root(call.cwd.resolve())
    with contextlib.suppress(Exception):
        _record_execution(call, root, ok=ok, detail=detail)
    if not fmt or not ok or call.tool not in GATED:
        return ALLOW
    try:
        return format_paths(call, root)
    except Exception:  # noqa: BLE001
        return ALLOW


def _record_execution(call: Call, root: Path, *, ok: bool, detail: str) -> None:
    scope_all = os.environ.get("PF_PROVENANCE_SCOPE", "mutating") == "all"
    if call.tool not in MUTATING and not scope_all:
        return
    _import_platform(root)
    from pf.loops.gate import project_for
    from pf.provenance import ledger as prov

    action_id = prov.claim_action(root, prov.correlation_key(call.key))
    if action_id is None:
        # No INTENT to close. A bare EXECUTION would manufacture an action that
        # was never gated — exactly the finding the verifier exists to raise.
        return
    rels = tuple(rel_to(root, p, call.cwd) for p in call.paths)
    target = ",".join(rels) if rels else call.command[:400]
    proj = project_for(str(call.cwd), root)
    group, project = (proj[0], proj[1]) if proj else ("", "")
    prov.execution(
        root,
        action_id,
        status="ok" if ok else "error",
        tool=call.tool,
        target=target,
        group=group,
        project=project,
        detail=detail[:400],
    )


FORMATTER = "platform/toolkits/power-tools/hooks/format_edit.py"


def format_paths(call: Call, root: Path) -> Verdict:
    """The power-tools formatter, fed a Claude-shaped payload per file. It is
    the one formatter; this only saves every harness from reimplementing its
    refusals (gate-denied, generated, vendor/)."""
    script = root / FORMATTER
    if not script.is_file():
        return ALLOW
    out: list[str] = []
    for p in call.paths:
        ap = Path(p) if Path(p).is_absolute() else call.cwd / p
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(ap)}, "cwd": str(call.cwd)}
        r = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=60,
            check=False,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)},
        )
        if r.returncode == 2 and r.stderr.strip():
            out.append(r.stderr.strip())
    return Verdict("allow", "\n".join(out))


# ----------------------------------------------------------- session start --
SESSION_SCRIPT = "platform/toolkits/power-tools/hooks/session_start.sh"


def scratch_rule(root: Path) -> str:
    return (
        "Hard rule for this repo: every file you write stays inside the checkout. Scratch and "
        f"temporary files go in {root}/.tmp/ (gitignored) — never /tmp, /private/tmp, or a "
        "session scratchpad path the environment names. That covers PR bodies, notes, scripts "
        "and intermediate output. Always use an absolute path under .tmp/."
    )


def session_context(cwd: Path, harness: str) -> str:
    """What every session is shown on turn one: scope, graph state, branch,
    memory for exactly this scope, a missing commit gate — and, for harnesses
    Claude's settings do not reach, the scratch rule those settings inject."""
    root = repo_root(cwd.resolve())
    with contextlib.suppress(OSError):
        (root / ".tmp").mkdir(exist_ok=True)
    parts: list[str] = []
    script = root / SESSION_SCRIPT
    if script.is_file():
        try:
            r = subprocess.run(
                ["bash", str(script)],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
                cwd=str(cwd),
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd), "PF_HARNESS": harness},
            )
            if r.stdout.strip():
                parts.append(r.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    if harness != "claude":
        parts.append(scratch_rule(root))
        parts.append(
            f"- harness: {harness} — hooks here run the same gate, permissions and provenance as "
            "Claude Code (docs/HARNESSES.md). A refusal is a finding: report it, never re-route it."
        )
    return "\n".join(parts)


# -------------------------------------------------------------------- stop --
def stop(cwd: Path, harness: str, session_id: str = "", transcript: str = "", last_message: str = "") -> None:
    """End of turn: copy the transcript into the repo, tell the human.

    Claude Code's own folders are captured by `session_stop.py`, which knows
    their layout. Every other harness names its transcript in the payload, and
    that file is what is copied — to the same `.tmp/<session>/transcript.jsonl`
    a Claude session gets.
    """
    root = repo_root(cwd.resolve())
    with contextlib.suppress(Exception):
        if harness != "claude" and transcript and session_id and Path(session_id).name == session_id:
            src = Path(transcript).expanduser()
            if src.is_file():
                _import_platform(root)
                from pf import workflows

                suffix = src.suffix or ".jsonl"
                workflows._copy_if_changed(src, root / workflows.SCRATCH_DIR / session_id / f"transcript{suffix}")
    with contextlib.suppress(Exception):
        notify(root, harness, "stop", last_message or "Task finished")


NOTIFY = "platform/toolkits/power-tools/hooks/notify.sh"


def notify(root: Path, harness: str, kind: str, message: str) -> None:
    script = root / NOTIFY
    if not script.is_file() or os.environ.get("PF_NOTIFY", "1") == "0":
        return
    subprocess.run(
        ["bash", str(script), kind],
        input=json.dumps({"cwd": str(root), "last_assistant_message": message, "message": message}),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env={**os.environ, "PF_HARNESS_LABEL": _label(harness)},
    )


def _label(harness: str) -> str:
    try:
        from pf.harnesses import spec

        s = spec(harness)
        return s.label if s else harness
    except Exception:  # noqa: BLE001
        return harness
