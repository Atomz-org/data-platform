---
name: wren-conversational-analytics
description: 'Wren: a workspace per project is the boundary; dry-run is our EXPLAIN; redact before rules'
type: project
status: active
agent: claude-code
---

Current WrenAI (0.13+) is a CLI over MDL plus `wren serve mcp`, no web UI. Every
`wren context`/`memory`/`cube` command wants a project directory with a
`wren_project.yml`, and defaults its config, profiles and memory to `~/.wren` —
one home for every project on the machine. `pf.tools.wren_context` writes the
workspace (`mdl/wren/`) from tracked inputs and runs every call inside it with
`WREN_PROJECT_HOME` and `WREN_HOME` pointed at it; that is the tenancy boundary.

Traps met while adopting it:

- `wren dry-run` cannot validate against DuckDB: its connector scans files and
  has no notion of dbt's schemas (`main_marts.x` → "not found"). The gate's
  dry-run is `EXPLAIN` on the platform's own `Warehouse`, read-only.
- `isHidden` is masking, not removal. The LLM-facing `target/mdl.json` removes
  the column and everything that read it (relationships, cube measures and
  dimensions, views); the rules are rendered from that redacted manifest, or a
  withheld column's measure is still *described* to the model (caught by a test).
- Without `wren[memory]` (LanceDB) memory is a grep backend over
  `knowledge/sql/*.md` — recall works, `memory fetch` (schema embeddings) does
  not; `memory describe` gives the schema as text without embeddings.
- `wren memory store` writes front matter with `nl`, `sql`, `source`, `tags`;
  a hand-written pair with other keys is not recalled.
- The manifest's metrics are `cubes`, not `metrics` — count the right key.
- Every gated question appends to the group's tracked `loop-ledger.json`, like
  every other loop run. Smoke tests dirty it; revert before committing.
