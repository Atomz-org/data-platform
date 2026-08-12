# Platform monorepo — router

Multi-tenant agentic data platform. Infra is shared; business logic is not.

- `platform/` — engines, runtime factories, ontology, knowledge graph, MCP, toolkits.
  **Shared by every project. Do not edit while working on a company.**
- `groups/<group>/` — a family of sister companies. Shared ontology instance,
  conformed dimensions, group metrics.
- `groups/<group>/projects/<project>/` — one entity. Own warehouse, own dlt
  pipelines, own dbt project. Sisters run in parallel.

**Never read another group or another sister project.** Business logic does not
transfer between entities — an assumption carried across is a bug.

To work on a project: `uv run pf work <group> <project>` (launches with that cwd).
Everything else: `uv run pf --help`.
