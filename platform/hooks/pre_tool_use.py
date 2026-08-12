#!/usr/bin/env python3
"""Claude Code PreToolUse hook — the gate that does not rely on the agent
remembering to run it.

Reads the tool call on stdin. Denies writes to generated artefacts, secrets and
shared platform infra; for models and sources it prints the blast radius as
feedback so the decision is informed rather than blocked.

exit 0 = allow (stdout is shown to the agent)
exit 2 = block (stderr is shown to the agent)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never block on a malformed payload

    tool = payload.get("tool_name", "")
    if tool not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd())
    root = repo_root(cwd.resolve())
    sys.path.insert(0, str(root / "platform" / "src"))

    try:
        from pf.loops.gate import check_path, nodes_for, project_for
    except Exception:
        return 0  # platform not importable — do not block the user's work

    try:
        rel = str(Path(file_path).resolve().relative_to(root))
    except ValueError:
        rel = file_path

    in_project = project_for(rel, root) is not None
    result = check_path(rel, root, in_project=in_project)

    if result.blocked:
        print(f"BLOCKED by gate.yaml [{result.rule}]\n  {rel}\n  {result.message}",
              file=sys.stderr)
        return 2

    if result.verdict == "warn":
        nodes = nodes_for(rel)
        proj = project_for(rel, root)
        if nodes and proj:
            group, project, pdir = proj
            gp = pdir / "kg" / "graph.duckdb"
            if gp.exists():
                try:
                    from pf.kg.impact import impact_of_many
                    report = impact_of_many(gp, nodes)
                    if report.total:
                        print(f"⚠ Blast radius of editing {Path(rel).name}:\n"
                              + report.render())
                        return 0
                except Exception:
                    pass
        print(f"⚠ {rel} is impact-gated. Run `pf impact {rel}` if the graph is stale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
