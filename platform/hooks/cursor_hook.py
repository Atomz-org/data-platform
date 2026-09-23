#!/usr/bin/env python3
"""Cursor hook adapter — the platform's gate, reached from Cursor's events.

Two events, one script, chosen by the first argument:

    shell   beforeShellExecution   can block.  Refuses `git commit --no-verify`
                                   (and `-n`), because the pre-commit hook is the
                                   only gate Cursor has and that flag skips it.
    edit    afterFileEdit          cannot block. Runs `pf gate` over the edited
                                   file and reports the verdict, so an edit to a
                                   generated artefact or a secret is named now
                                   rather than at commit.

Contract, as Cursor's own adapters follow it: stdin is JSON, stdout echoes it
back on allow, exit 2 with a reason on stderr means deny. Anything that goes
wrong exits 0 — a hook that fails closed on a parse error blocks every command
in the editor, which is a worse outcome than one missed check.

The `--no-verify` matcher is flag-position-aware: it tokenises the command and
skips the values of `-m`, `-F`, `--message` and friends, so a commit message
that *mentions* `--no-verify` is not refused. That false positive is the reason
the upstream this is ported from (`vendor/ecc`, `scripts/hooks/block-no-verify.js`)
rewrote its own matcher; it is worth not repeating.

Nothing here writes provenance. The chain's stages are written by Claude Code's
hooks around a tool call that has not yet run; Cursor's `afterFileEdit` fires
after, and an INTENT written for an action already taken is a record that
flatters the outcome. `docs/HARNESSES.md` says provenance is Claude-only, and
that is the truth this script keeps.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

#: Flags whose *next* token is a value and must not be inspected.
_TAKES_VALUE = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "--author", "--date"}


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def bypasses_hooks(command: str) -> bool:
    """True when `command` is a git commit/push that skips hooks.

    Only `git commit` and `git push` carry `--no-verify`; `-n` means no-verify
    for commit alone (for push it is `--dry-run`'s short form on some versions,
    so it is not treated as a bypass there).
    """
    try:
        toks = shlex.split(command)
    except ValueError:
        toks = command.split()
    # Walk every `git ...` segment: `a && git commit -n` must still be caught.
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
            # bundled short flags: `-an`, `-na`
            return True
    return False


def _shell(payload: dict, raw: str) -> int:
    command = str(payload.get("command") or (payload.get("args") or {}).get("command") or "")
    if bypasses_hooks(command):
        sys.stderr.write(
            "BLOCKED — `--no-verify` skips the pre-commit gate, which is the only gate\n"
            "Cursor has here. gate.yaml's denylist and file cap are enforced there and\n"
            "nowhere else. Commit without the flag; if the gate is wrong, say why in the\n"
            "commit message and let a person decide.\n"
        )
        return 2
    sys.stdout.write(raw)
    return 0


def _edit(payload: dict, raw: str) -> int:
    path = str(payload.get("path") or payload.get("file") or payload.get("file_path") or "")
    if not path:
        sys.stdout.write(raw)
        return 0
    root = repo_root(Path(path).resolve().parent)
    try:
        rel = str(Path(path).resolve().relative_to(root))
    except ValueError:
        rel = path
    r = subprocess.run(
        ["uv", "run", "--project", str(root), "pf", "gate", "--paths", rel],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        # Advisory by necessity: the edit has happened. Say what the commit
        # gate will say, now, while the file is still open.
        msg = (r.stdout + r.stderr).strip()
        sys.stderr.write(f"⚠ gate.yaml would refuse this edit at commit:\n{msg}\n")
    sys.stdout.write(raw)
    return 0


def main(argv: list[str]) -> int:
    event = argv[1] if len(argv) > 1 else ""
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        payload = {}
    try:
        if event == "shell":
            return _shell(payload, raw)
        if event == "edit":
            return _edit(payload, raw)
    except Exception:  # noqa: BLE001 — never fail closed on our own bug
        pass
    sys.stdout.write(raw)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
