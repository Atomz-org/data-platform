---
name: platform-init
description: Always-on workspace rules for every project in this platform.
---
# Platform rules

You are working inside ONE project of a multi-tenant data platform.

- **Isolation.** Never read another group, or a sister project, from here. Cross-entity
  work happens only in `_rollup`. Business logic does not transfer between entities.
- **Infra is shared and off-limits.** `platform/` holds engines, runtime factories,
  the ontology and the toolkits. Do not edit it while working on a company.
- **Dagster assembly is a factory.** `definitions.py` calls
  `pf.runtime.dagster_runtime.build_definitions()`. Never scaffold a raw
  `Definitions`, resource, executor or pool.
- **Ontology first.** Every dlt resource carries `@annotate(concept=..., roles=...)`.
  An unannotated source fails `pf check`.
- **Secrets.** Never ask for a credential in chat and never read a secrets file.
  Use `secrets_view_redacted` and `secrets_update_fragment`.
- **Read the routing order** in ROUTING.md before choosing a tool.
