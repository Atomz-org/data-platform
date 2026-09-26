# Evals for wren-analytics

There are no agent cases here yet, and that is deliberate.

A case under a toolkit's `evals/` drives one **agent step**: `pf.agents.base`
routes it, `pf evals` calls it, and the `expect` block is graded against what
the model returned. `ask-through-wren` ships no agent step of its own. The
interactive agent reads the context and writes the SELECT; everything that
decides whether that SELECT may run is deterministic and lives in
`pf.tools.wren_gate`, and everything that decides what the agent was told lives
in `pf.tools.wren_context`. A case written against a model that is not called
would pass by finding nothing.

What proves this skill is `platform/tests/capabilities/test_tool_wren.py` and
`test_wren_analytics_skill.py`:

- a restricted column is absent from the LLM-facing manifest, with every
  relationship, cube measure, dimension and view that read it
- every `wren` process runs inside the project's workspace with Wren's home
  pointed at it — nothing global, nothing of another project
- the workspace is rebuilt from tracked inputs only, is deterministic, and
  `check` tells stale, missing and orphaned apart (CI runs it for every project)
- the gate refuses anything but one read-only SELECT by statement type, plans
  before it dry-runs, dry-runs before it executes, row-limits what it returns,
  and records every outcome — including the fourth attempt at a statement that
  failed three times, refused with "escalate"
- the MCP server the tool wires is transpile-only; execution is only the gate
- every command the skill names resolves in the CLI, and every skill it routes
  to is shipped

If the planning step is ever routed through a model — a `wren_planner` agent
that drafts the SELECT from the context — its cases belong here, graded by the
gate's outcome plus pinned fields: the models named, the aggregate used, the
row limit.
