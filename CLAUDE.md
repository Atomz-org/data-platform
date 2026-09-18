# Platform monorepo — router

Multi-tenant agentic data platform. Infra is shared; business logic is not.

- `platform/` — engines, runtime factories, ontology, knowledge graph, MCP, toolkits.
  **Shared by every project. Do not edit while working on a company.**
- `groups/<group>/` — a family of sister companies. Shared ontology instance,
  conformed dimensions, group metrics.
- `groups/<group>/projects/<project>/` — one entity. Own warehouse, own dlt
  pipelines, own dbt project. Sisters run in parallel.

- `vendor/` — fourteen upstreams pinned as submodules (the Recce family is
  grouped under `vendor/recce/`). **Read-only, always.** What we took from each
  is recorded in `platform/src/pf/vendor/registry.yaml`; `docs/VENDOR-CARD.md`
  (~520 tokens) is the index, `pf vendor why <file>` the reverse lookup. Bumping
  a pin is a human decision, never an agent's.

- **Tools** (`pf tool list`) are capabilities that also run: scaffolded files,
  gate rules, Dagster assets and a UI, from one `Tool` declaration. Enabled in
  `tools.yaml` at the group (every sister inherits) or per project. Recce is the
  reference — `pf.tools.recce`. Adding one never edits the scaffolder, the CLI or
  the UI; a `pf.tools` entry point in any installed package is enough.

**Never read another group or another sister project.** Business logic does not
transfer between entities — an assumption carried across is a bug.

- **Agent actions are recorded, not assumed.** Every action runs through five
  stages — intent (before), decision (the gate), execution (after), a SHA-256
  chain linking them, and an RFC 3161 + OpenTimestamps anchor over the head.
  The hooks write stages 01–03 for tool calls, `pf.agents.base` for LLM calls,
  `pf.provenance.action()` for everything else. `provenance/**` is denied to
  every agent: you may not edit the record of what you did. `pf provenance
  verify` is the audit and blocks CI; `docs/GOVERNANCE.md` is the reference.

- **The session layer** ships as the `power-tools` toolkit: audit and shipping
  commands, read-only verification subagents, format/notify hooks, and the `pf`
  MCP server. That server is what makes `kg_search`, `kg_neighbors`, `kg_path`
  and `impact_analysis` exist — ask the graph before reading files, and run
  `impact_analysis` before changing a column, a model or a metric.
  `docs/CLAUDE-CODE.md` is the runbook; read it when changing that layer, not
  while working.

To work on a project: `uv run pf work <group> <project>` (launches with that cwd).
Everything else: `uv run pf --help`.
