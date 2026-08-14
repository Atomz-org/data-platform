"""Rendering toolkit templates into a project's own cases.

The output goes to `evals/cases/generated/`, which is regenerable and denied to
agents by the gate, exactly like every other compiled artefact in this platform.
Hand-written cases live one directory up in `evals/cases/` and are never touched.

That separation is the whole reason generation is safe to re-run. A generator
that overwrote hand-written cases would make `pf evals-gen` a command nobody
dares use twice, and the corpus would freeze at whatever the scaffolder produced.

**A generated case is a starting point, not a verdict.** The reasoning shape
comes from the toolkit and is sound; the expectations are asserted against a
scenario constructed over this project's models, and whether they are *right for
this entity* is a judgement only someone who knows the business can make. The
header written into every file says so.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pf.evals.template import (
    Template, discover_templates, render, resolve_bindings, validate_rendered,
)

GENERATED_DIR = "generated"


@dataclass(frozen=True)
class Generated:
    template: Template
    path: Path | None = None
    skipped: str = ""


def generate(root: Path, group: str, project: str,
             toolkits: set[str] | None = None,
             prune: bool = True) -> list[Generated]:
    """Render every groundable template into the project's generated cases.

    A template whose bindings the project cannot satisfy is skipped with a
    reason, not an error: a project scaffolded an hour ago has no marts, and
    "nothing to ground this on yet" is a normal state that resolves itself once
    `pf kg build` has something to index.
    """
    pdir = root / "groups" / group / "projects" / project
    graph = pdir / "kg" / "graph.duckdb"
    out_dir = pdir / "evals" / "cases" / GENERATED_DIR

    templates = discover_templates(root, toolkits)
    results: list[Generated] = []
    written: set[Path] = set()

    for tpl in templates:
        if not graph.exists():
            results.append(Generated(tpl, skipped="no knowledge graph — run `pf kg build`"))
            continue

        bindings = resolve_bindings(graph, tpl.requires)
        if bindings is None:
            need = ", ".join(sorted(set(tpl.requires.values())))
            results.append(Generated(tpl, skipped=f"project has no {need} yet"))
            continue

        case = render(tpl, bindings)
        target = out_dir / f"{tpl.name}.json"
        validate_rendered(case, origin=str(target))

        out_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(case, indent=2) + "\n")
        written.add(target)
        results.append(Generated(tpl, path=target))

    # A template that was deleted or renamed upstream leaves a stale case behind
    # that still runs and still bills. Regeneration owns this directory
    # completely, so anything it did not write this time no longer belongs.
    if prune and out_dir.exists():
        for stale in out_dir.glob("*.json"):
            if stale not in written:
                stale.unlink()

    return results
