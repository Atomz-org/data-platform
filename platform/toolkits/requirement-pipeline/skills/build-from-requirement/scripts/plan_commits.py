"""Slice a finished build into commits the gate accepts, in pipeline order.

    uv run python plan_commits.py [--group <g> --project <p>] [--json] < paths.txt
    git status --porcelain -uall | uv run python plan_commits.py --porcelain

It plans and never commits: committing is the user's call (`/ship`). What it
encodes is what the pre-commit gate enforces on every commit, learned the hard
way on a 270-file build:

* **At most 12 files per commit** (`maxFiles`), counted with the harness maps
  the commit must carry. A slice leaves room for them: one map for a project
  slice, three for a group-tier slice (group, project, reporting maps move
  together).
* **Harness maps are not planned, they are regenerated per slice.** They render
  from the git index, so a map is only current for the files already staged:
  `git add <slice>` → `pf harness <g> <p>` (or `pf harness <g>` for a group
  change) → `git add` whatever map changed → commit.
* **Pipeline order**, so every commit is reviewable on its own and a bisect
  lands on a layer: group tier → ingestion → staging → intermediate → marts →
  semantic → orchestration → hand-written pages → report sources → generated
  pages → OKF → graph, MDL and catalogue.
* **Paths that never ship** (vendor/, provenance/, local warehouses, the
  machine-local Dagster workspace, secrets) are refused, not sliced.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys

MAX_FILES = 12
#: Never committed from a build: read-only upstreams, the provenance record,
#: machine-local state and secrets. `gate.yaml`'s denylist is the authority;
#: these are the ones a build actually produces.
NEVER = ("vendor/*", "provenance/*", "*.duckdb", "*.duckdb.wal", "platform/workspace.yaml",
         "*/.env", ".env*", "*/secrets.toml", "graphify-out/*", "*/target/*", "*/kg/graph.duckdb",
         "*/kg/context_card.md")

P = r"groups/[^/]+/projects/[^/]+/"
G = r"groups/[^/]+/"
#: (order, label, pattern). First match wins, so specific patterns come first.
LAYERS: list[tuple[int, str, str]] = [
    (0, "platform prerequisite", r"^platform/|^docs/|^\.github/|^gate\.capabilities\.yaml$"),
    (3, "sister bundles (generated)", G + r"projects/[^/]+/okf/"),        # re-tagged when not ours
    (1, "group tier", G + r"(ontology|shared|okf|kg|tools\.yaml|notify\.yaml|group\.yaml|air\.yaml|\.claude)/?"),
    (2, "requirement record", P + r"requirements/"),
    (15, "generated metric pages", P + r"reporting/pages/metrics/"),
    (13, "hand-written pages", P + r"reporting/pages/"),
    (14, "report sources", P + r"reporting/sources/"),
    (13, "hand-written pages", P + r"reporting/"),
    (16, "OKF bundle", P + r"okf/"),
    (17, "graph, MDL, catalogue", P + r"(kg|mdl|governance|catalog)/"),
    (5, "staging (generated)", P + r"transform/models/staging/|" + P + r"transform/macros/|"
        + P + r"transform/dbt_project\.yml$|" + P + r"transform/packages\.yml$"),
    (6, "intermediate", P + r"transform/models/intermediate/"),
    (8, "semantic layer", P + r"transform/models/(semantic/|.*semantic.*\.ya?ml$|_reporting__exposures\.yml$)"),
    (7, "marts and tests", P + r"transform/(models/|tests/)"),
    (4, "ingestion", P + r"(src/[^/]+/sources/|\.dlt/|contracts/|transform/seeds/|tests/|pyproject\.toml$|"
        r"decisions/|\.memory/notes/)|^uv\.lock$"),
    (9, "orchestration and docs", P + r"(src/|docs/|CLAUDE\.md$|air\.yaml$|atlas\.yaml$)"),
    (18, "memory index", r"(^|/)\.memory/MEMORY\.md$"),
]
HARNESS = re.compile(r"(^|/)HARNESS\.md$")


def classify(path: str, group: str | None = None, project: str | None = None) -> tuple[int, str]:
    for order, label, pattern in LAYERS:
        if re.search(pattern, path):
            if order == 3 and project and f"/projects/{project}/" in path:
                return 16, "OKF bundle"
            return order, label
    return 10, "other project files"


def refused(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in NEVER)


def plan(paths: list[str], group: str | None = None, project: str | None = None) -> dict:
    keep = sorted({p.strip() for p in paths if p.strip()})
    out = {"refused": [p for p in keep if refused(p)], "maps": [p for p in keep if HARNESS.search(p)]}
    layers: dict[tuple[int, str], list[str]] = {}
    for p in keep:
        if refused(p) or HARNESS.search(p):
            continue
        layers.setdefault(classify(p, group, project), []).append(p)
    slices = []
    for (order, label), files in sorted(layers.items()):
        room = MAX_FILES - (3 if order in (1, 3) else 1)
        parts = [files[i:i + room] for i in range(0, len(files), room)]
        for n, part in enumerate(parts, 1):
            title = label if len(parts) == 1 else f"{label} ({n} of {len(parts)})"
            slices.append({"order": order, "title": title, "files": part,
                           "harness": f"pf harness {group}" if order in (1, 3) and group
                           else f"pf harness {group} {project}" if group and project else "pf harness <g> <p>"})
    out["slices"] = slices
    return out


def _porcelain(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        if len(line) > 3 and not line.startswith(" D") and not line.startswith("D "):
            path = line[3:]
            out.append(path.split(" -> ", 1)[-1])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group")
    ap.add_argument("--project")
    ap.add_argument("--porcelain", action="store_true", help="stdin is `git status --porcelain -uall`")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    lines = sys.stdin.read().splitlines()
    result = plan(_porcelain(lines) if args.porcelain else lines, args.group, args.project)
    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if result["refused"] else 0
    for p in result["refused"]:
        print(f"✗ never committed: {p}")
    print(f"slices[{len(result['slices'])}]{{n,files,title}}:")
    for i, s in enumerate(result["slices"], 1):
        print(f"  {i},{len(s['files'])},{s['title']}")
    print("per slice: git add <files> → " + (result["slices"][0]["harness"] if result["slices"] else "pf harness")
          + " → git add the maps it changed → commit (≤ 12 files) · then `pf gate --commits origin/main..HEAD`")
    return 1 if result["refused"] else 0


if __name__ == "__main__":
    sys.exit(main())
