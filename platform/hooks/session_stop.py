#!/usr/bin/env python3
"""Claude Code Stop hook — copy this session's files into the repo.

`session_start.py` links what can be linked and captures what was there at the
start. At that moment a new session has written nothing, so the capture is
close to a no-op: the files worth having are the ones the session goes on to
produce. This runs when the model stops, which is when they exist.

Incremental by construction — a file already copied and unchanged is compared
by size and mtime and never read — so running at the end of every turn costs a
stat per file and one copy of the transcript, which is the only thing that grew.

Nothing at the source is removed. The harness owns those files and is still
using them; the repo keeps its own copy.

Prints only refusals, for the same reason `session_start.py` does: a line in
front of the model at the end of every turn, saying that the expected thing
happened, is a cost paid forever for no decision anyone can make.

exit 0 always. A session whose files cannot be copied is still a working
session, and `pf workflow capture` reports the same thing on demand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root(start: Path) -> Path:
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    root = repo_root(Path(payload.get("cwd") or Path.cwd()))
    sys.path.insert(0, str(root / "platform" / "src"))
    try:
        from pf import workflows
    except Exception:
        return 0

    session_id = str(payload.get("session_id") or "")
    # A bare id, never a path: a crafted payload must not be able to name a
    # directory belonging to another checkout and copy its transcripts here.
    if not session_id or Path(session_id).name != session_id or session_id in (".", ".."):
        return 0

    try:
        home = workflows.claude_home()
        sess = home / "projects" / workflows.slug(root) / session_id
        if not sess.is_dir():
            return 0
        reports = workflows.capture(root, home, session_dir=sess)
    except Exception as exc:  # noqa: BLE001 - a turn must end regardless
        print(f"session capture: {type(exc).__name__}: {exc}")
        return 0

    for r in reports:
        if not r.ok:
            print(r.line(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
