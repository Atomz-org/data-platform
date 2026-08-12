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

    # `in_project` is a property of the *session*, not of the file being edited.
    # Resolving it from the target path made platform_denylist unreachable: a
    # path under platform/ never resolves to a project, so the one rule that
    # stops a project session from editing shared infra never fired.
    in_project = project_for(str(cwd), root) is not None
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
            else:
                # Deliberately a warning, not a block: a brand-new project has
                # no graph yet and must stay workable. But say plainly that the
                # gate is inert rather than implying it passed.
                print(f"⚠ NO BLAST RADIUS CHECKED for {Path(rel).name} — "
                      f"{group}/{project} has no knowledge graph at "
                      f"kg/graph.duckdb, so the impact gate is inert.\n"
                      f"  This edit is allowed, but nothing verified what it breaks.\n"
                      f"  Build the index: `pf kg build {group} {project}`")
                return 0
            print(f"⚠ {Path(rel).name} is impact-gated but resolved to no graph node. "
                  f"If it is a new model, run `pf kg build {group} {project}` "
                  f"then `pf impact {group} {project} model:{Path(rel).stem}`.")
            return 0
        print(f"⚠ {rel} is impact-gated; it is outside any project, so no graph applies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
