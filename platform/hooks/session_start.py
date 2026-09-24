#!/usr/bin/env python3
"""Claude Code SessionStart hook — point this session's workflow directories at
the repo before anything can write to them.

Claude Code keeps a Workflow run under
`~/.claude/projects/<slug>/<session>/`, split across `subagents/workflows/` and
`workflows/`. `pf workflow link` replaces both with symlinks to
`<repo>/logs/workflows`, so runs are written inside the repo as they happen
rather than copied there afterwards.

Timing is the reason this is a hook and not a command someone remembers to run:
the harness may not have created the session folder yet, and a link made after
the first run has started is already too late for that run. The session id comes
from the payload, so the folder is created here, linked, and waiting.

Nothing is printed unless a link could not be made. A SessionStart hook's stdout
is added to the session context, and both the steady state (already linked) and
the expected state for a new session (just created) would otherwise put lines in
front of the model at every single session, forever, saying nothing it can act
on. A refusal is different: it means this session's runs will go to ~/.claude.

exit 0 always. A repo whose session folder cannot be linked still works; its runs
land under ~/.claude, `pf workflow list` says so, and
`pf workflow link --adopt` brings them in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root(start: Path) -> Path:
    """The checkout the session is in, which in a git worktree is that worktree:
    its runs go to its own `logs/workflows` and go away with it. That is the
    useful default, because a worktree is usually one piece of work."""
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def session_dir(payload: dict, home: Path, root: Path) -> Path | None:
    """The folder for this session. `transcript_path` is
    `<home>/projects/<slug>/<session-id>.jsonl`, which names the home and the
    slug the harness actually chose, so it is preferred over rebuilding them."""
    transcript = payload.get("transcript_path") or ""
    if transcript:
        p = Path(transcript).expanduser()
        if p.suffix == ".jsonl" and p.parent.parent.name == "projects":
            return p.with_suffix("")
    sid = payload.get("session_id") or ""
    if not sid:
        return None
    from pf import workflows

    return home / "projects" / workflows.slug(root) / sid


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):  # a bare list or string is still valid JSON
        payload = {}

    root = repo_root(Path(payload.get("cwd") or Path.cwd()))
    sys.path.insert(0, str(root / "platform" / "src"))
    try:
        from pf import workflows
    except Exception:
        return 0  # a session must start even when the platform package is broken

    try:
        home = workflows.claude_home()
        sess = session_dir(payload, home, root)
        if sess is None:
            return 0
        reports = workflows.link(root, home, session_dir=sess, create=True)
    except Exception as exc:  # noqa: BLE001 - a session must start regardless
        print(f"workflow link: {type(exc).__name__}: {exc}")
        return 0

    # The files the sweep would delete if they were linked. Only this session:
    # a first capture of every session of this repo can be hundreds of
    # megabytes, and a session must not wait for that to start. `pf workflow
    # capture` with no --session backfills the rest.
    try:
        reports += workflows.capture(root, home, session_dir=sess)
    except Exception as exc:  # noqa: BLE001 - a session must start regardless
        print(f"session capture: {type(exc).__name__}: {exc}")

    refused = [r for r in reports if not r.ok]
    for r in refused:
        print(r.line(root))
    if refused:
        print("This session's workflow runs will be written under ~/.claude "
              "instead of logs/workflows/. `pf workflow link --adopt` fixes it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
