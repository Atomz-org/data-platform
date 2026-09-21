---
name: code-graph-scoped-to-platform
description: code graph runs via uvx (never a lockfile dep) and is scoped to platform/ by a tracked marker dir; without the marker it silently indexes every sister project and vendor/
type: project
status: active
agent: claude-code
---

**Why:** the data graph (`pf kg`) has no notion of which Python function calls
which, so a change under `platform/src/pf/` had no blast radius the way a dbt
model does. The tool fills that and nothing else; models, columns, metrics and
lineage stay with `pf kg` and the `pf` MCP server, which answer them better.

Three decisions worth not re-deriving:

- **The marker directory is load-bearing.** `platform/.code-review-graph/` is
  tracked (README and all) because the tool resolves `--repo` by walking *up*
  for a `.code-review-graph`, `.git` or `.svn` marker. With it, `--repo
  platform` stops at `platform/`. Without it the walk reaches the repo's own
  `.git` and the graph silently spans every sister project and ~27,000 vendored
  files. It does not error — it just builds the wrong graph, and crosses the one
  boundary this platform forbids. `platform/` is the only module where one
  repo-wide code graph is safe, because it is the only one with no sisters.
- **Run through `uvx`, never a lockfile dependency.** Its deps (fastmcp,
  tree-sitter-language-pack, networkx, watchdog) are not ones this workspace
  should resolve against dbt, dlt, Dagster and recce — the same reason
  `graphify` is a `uvx` entry in `.mcp.json`, and the same shape as
  elementary's "command, never imported". Pinned to a version on purpose: an
  unpinned `uvx` call is a different tool on a different day.
- **No registry entry until the submodule exists.** `verify.check_paths`
  raises an *error* for a registered upstream whose `vendor/<id>/.git` is
  absent, which is exactly the live `floci-vendor-pin-missing` defect. Adding
  the entry first would make `pf vendor verify` red for a second reason.

**Measured on this tree, 2026-09-21.** The first build indexed 231 files and
zero outside `platform/`, which is the marker working: 190 Python, 19
Terraform, 7 tsx, 5 sql, 5 sh, 3 hcl, 2 ts, giving 3,441 nodes and 30,014
edges (19,329 CALLS, 3,799 TESTED_BY). One impact query on
`platform/src/pf/memory.py`, in tokens:

    reading the 6 files it names   81,831
    the tool's own JSON            13,090   (depth 1; its default depth 2 gives 31,317, still truncated)
    `pf code impact`                   94

So the tool's own output is *not* the token-efficient surface — its
`context_savings` field even reports `saved_tokens: 0` — and the value is the
file list, which is why `summarise_impact` is the default and `--json` is the
escape hatch. Two traps in its CLI: `impact` takes `--files`, never a
positional (a positional exits 2), and the graph stores *absolute* paths.

**How to apply:** `pf code check` verifies our side (marker, ignore rule, gate
entry, MCP scope, the protocol naming it) and is folded into `pf context
check`, so the every-PR workflow covers it. `pf code plan` prints the argv
without running anything. The graph database is gitignored and gate-denied;
rebuild it rather than carrying it. When the pin lands, the registry entry's
`adopted:` paths must exist in the pinned commit or verify fails.
