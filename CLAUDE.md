# Platform monorepo — router

Multi-tenant agentic data platform. Infra is shared; business logic is not.

- `platform/` — engines, runtime factories, ontology, knowledge graph, MCP,
  toolkits. **Shared by every project. Do not edit while working on a company.**
- `groups/<group>/` — a family of sisters: shared ontology instance, conformed
  dimensions, group metrics.
- `groups/<group>/projects/<project>/` — one entity: own warehouse, own dlt
  pipelines, own dbt project. Sisters run in parallel.

- `vendor/` — twenty-three upstreams pinned as submodules (Recce's under
  `vendor/recce/`). **Read-only, always.** What we took is in
  `platform/src/pf/vendor/registry.yaml`; `docs/VENDOR-CARD.md` indexes it,
  `pf vendor why <file>` is the reverse lookup. Bumping a pin is a human
  decision, never an agent's.

- **Tools** (`pf tool list`) are capabilities that also run: scaffolded files,
  gate rules, Dagster assets and a UI, from one declaration. Enabled in
  `tools.yaml` per group (sisters inherit) or per project; `pf.tools.recce` is
  the reference. A `pf.tools` entry point in any installed package is enough —
  adding one never edits the scaffolder, the CLI or the UI.

**Never read another group or another sister project.** Business logic does not
transfer between entities; an assumption carried across is a bug.

- **Agent actions are recorded, not assumed.** Five stages — intent, decision,
  execution, a SHA-256 chain linking them, an RFC 3161 + OpenTimestamps anchor
  over the head. Hooks write 01–03 for tool calls, `pf.agents.base` for LLM
  calls, `pf.provenance.action()` elsewhere. `provenance/**` is denied to
  every agent: you may not edit the record of what you did. `pf provenance
  verify` blocks CI; `docs/GOVERNANCE.md` is the reference.

- **Controls are named, not asserted.** `policy.yaml` entries carry `controls:`
  ids from the vendored FINOS AI Governance Framework (`AIR-DET-21`),
  cross-walked to the EU AI Act, ISO 42001, NIST and OWASP. `pf air coverage`
  derives — never stores — whether each control's enforcement resolves;
  `pf air gate <group> <project>` blocks on what that entity committed to in
  `air.yaml`. A `controls:` entry whose `enforced_by` resolves to nothing
  reports as failing, which is the point. `docs/AIR.md` is the reference.

- **The session layer** ships as `power-tools`: audit and shipping commands,
  read-only verification subagents, format/notify hooks, and the `pf` MCP server
  — which is what makes `kg_search`, `kg_neighbors`, `kg_path` and
  `impact_analysis` exist. Ask the graph before reading files; run it before
  changing a column, model or metric. `docs/CLAUDE-CODE.md` is the runbook for
  that layer.

To work on a project: `uv run pf work <group> <project>`. Everything else:
`uv run pf --help`.
