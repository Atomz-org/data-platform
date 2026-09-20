#!/usr/bin/env python3
"""Claude Code PreToolUse hook — stages 01 and 02 of the provenance chain.

Reads the tool call on stdin. Writes INTENT (what the agent proposed), consults
the policy gate, then writes DECISION (what the gate said) — in that order,
before the tool runs. `post_tool_use.py` closes the action with EXECUTION.

Denies writes to generated artefacts, secrets and shared platform infra; for
models and sources it prints the blast radius as feedback so the decision is
informed rather than blocked.

Recording is deliberately ordered so the record cannot flatter the outcome:
INTENT is written before the gate is consulted, so a denied action still leaves
evidence of what was attempted. A gate that only logs its refusals can prove it
said no; it cannot prove it was ever asked.

exit 0 = allow (stdout is shown to the agent)
exit 2 = block (stderr is shown to the agent)
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

#: Tools that can change the world. Reads are not recorded by default — a
#: chain in which every file view is an action buries the writes that matter.
#: `PF_PROVENANCE_SCOPE=all` records everything, for deployments that need it.
MUTATING = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}

#: Tools the *file* gate applies to. Bash is recorded but not path-gated here:
#: its safety rules live in the permissions layer, and pretending a command
#: string is a path would produce confident, wrong verdicts.
GATED = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def _target(tool: str, tool_input: dict) -> str:
    if tool == "Bash":
        return str(tool_input.get("command", ""))[:400]
    return str(tool_input.get("file_path", ""))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never block on a malformed payload

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    scope_all = os.environ.get("PF_PROVENANCE_SCOPE", "mutating") == "all"
    if tool not in MUTATING and not scope_all:
        return 0

    target = _target(tool, tool_input)
    if not target:
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd())
    root = repo_root(cwd.resolve())
    sys.path.insert(0, str(root / "platform" / "src"))

    try:
        from pf.loops.gate import check_path, nodes_for, project_for
    except Exception:
        return 0  # platform not importable — do not block the user's work

    # Provenance is imported separately: a platform new enough to gate but
    # without the provenance package must still gate rather than fail open on
    # both. `prov` staying None degrades recording, never enforcement.
    try:
        from pf.provenance import ledger as prov
    except Exception:
        prov = None

    file_path = tool_input.get("file_path", "")
    rel = target
    if file_path:
        try:
            rel = str(Path(file_path).resolve().relative_to(root))
        except ValueError:
            rel = file_path

    proj = project_for(str(cwd), root)
    group, project = (proj[0], proj[1]) if proj else ("", "")

    # ---- stage 01: INTENT, before anything is decided --------------------
    action_id = None
    if prov is not None:
        try:
            rec = prov.intent(
                root, tool=tool, target=rel,
                summary=f"{tool} {Path(rel).name if file_path else rel[:80]}",
                group=group, project=project,
                payload={"cwd": str(cwd), "session": payload.get("session_id", "")})
            action_id = rec.action_id
            prov.stash_action(root, prov.correlation_key(payload), action_id)
        except prov.Revoked as exc:
            # The kill switch is not advisory and does not depend on the
            # enforcement flag: a revoked actor is stopped here, before the
            # gate is even consulted.
            print(f"REVOKED — agent action refused\n  {exc}\n"
                  f"  Reinstate with `pf provenance reinstate`.", file=sys.stderr)
            return 2
        except prov.NotRecorded as exc:
            print(f"BLOCKED — action could not be recorded and "
                  f"PF_PROVENANCE_ENFORCE=1\n  {exc}", file=sys.stderr)
            return 2
        except Exception:
            action_id = None  # recording is best-effort unless enforcing

    def record_decision(verdict: str, rule: str, message: str) -> None:
        if prov is None or action_id is None:
            return
        with contextlib.suppress(Exception):
            prov.decision(root, action_id, verdict=verdict, rule=rule,
                          message=message, tool=tool, target=rel,
                          group=group, project=project)

    # ---- stage 02: DECISION ----------------------------------------------
    if tool not in GATED:
        # Recorded as explicitly ungated rather than silently allowed. The
        # distinction matters in an audit: "no rule applied" and "a rule
        # allowed it" are different facts.
        record_decision("allow", "ungated", f"{tool} is not path-gated")
        return 0

    # `in_project` is a property of the *session*, not of the file being edited.
    # Resolving it from the target path made platform_denylist unreachable: a
    # path under platform/ never resolves to a project, so the one rule that
    # stops a project session from editing shared infra never fired.
    result = check_path(rel, root, in_project=proj is not None)
    record_decision(result.verdict, result.rule, result.message)

    if result.blocked:
        print(f"BLOCKED by gate.yaml [{result.rule}]\n  {rel}\n  {result.message}",
              file=sys.stderr)
        # Close the action here: the tool never runs, so PostToolUse never
        # fires, and an action left open would read as a crash rather than as
        # a refusal that worked.
        if prov is not None and action_id is not None:
            with contextlib.suppress(Exception):
                prov.execution(root, action_id, status="blocked", tool=tool,
                               target=rel, group=group, project=project,
                               detail=f"{result.rule}: {result.message}")
                prov.claim_action(root, prov.correlation_key(payload))
        return 2

    if result.verdict == "warn":
        nodes = nodes_for(rel)
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
