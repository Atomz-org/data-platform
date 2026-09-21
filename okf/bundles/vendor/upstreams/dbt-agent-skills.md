---
type: Vendor Upstream
title: dbt Agent Skills
description: how an agent drives dbt — rewritten for dbt Core + DuckDB
resource: https://github.com/dbt-labs/dbt-agent-skills
tags:
- vendor
- skills
- Apache-2.0
status: stable
sources:
- id: dbt-agent-skills:skills/dbt/skills/using-dbt-for-analytics-engineering/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/using-dbt-for-analytics-engineering/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/running-dbt-commands/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/running-dbt-commands/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/fetching-dbt-docs/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/fetching-dbt-docs/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/building-dbt-semantic-layer/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/building-dbt-semantic-layer/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/answering-natural-language-questions-with-dbt/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/answering-natural-language-questions-with-dbt/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/adding-dbt-unit-test/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/adding-dbt-unit-test/SKILL.md
- id: dbt-agent-skills:skills/dbt/skills/troubleshooting-dbt-job-errors/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt/skills/troubleshooting-dbt-job-errors/SKILL.md
- id: dbt-agent-skills:skills/dbt-migration/skills/upgrading-dbt-core/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt-migration/skills/upgrading-dbt-core/SKILL.md
- id: dbt-agent-skills:skills/dbt-migration/skills/migrating-dbt-core-to-fusion/SKILL.md
  resource: https://github.com/dbt-labs/dbt-agent-skills
  title: skills/dbt-migration/skills/migrating-dbt-core-to-fusion/SKILL.md
---

# dbt Agent Skills

dbt Labs' own account of how an agent should drive dbt. Written for dbt Cloud; every skill here was rewritten against dbt Core + dbt-duckdb.

## Adopted

- **skills/dbt/skills/using-dbt-for-analytics-engineering/SKILL.md** (port) -> platform/toolkits/dbt-modeling/skills/using-dbt/SKILL.md
- **skills/dbt/skills/running-dbt-commands/SKILL.md** (port) -> platform/toolkits/dbt-modeling/skills/run-commands/SKILL.md, platform/src/pf/runtime/dbt_runtime.py
  Cloud job triggers became local `dbt` invocations with our profile and target resolution.
- **skills/dbt/skills/fetching-dbt-docs/SKILL.md** (port) -> platform/toolkits/dbt-modeling/skills/fetch-docs/SKILL.md
- **skills/dbt/skills/building-dbt-semantic-layer/SKILL.md** (port) -> platform/toolkits/dbt-semantic/skills/build-semantic-layer/SKILL.md, docs/SEMANTICS.md
  The ratio-metric rule (carry numerator and denominator; never average a ratio) comes from here and is now enforced in the report audit.
- **skills/dbt/skills/answering-natural-language-questions-with-dbt/SKILL.md** (port) -> platform/toolkits/dbt-semantic/skills/answer-with-metrics/SKILL.md
- **skills/dbt/skills/adding-dbt-unit-test/SKILL.md** (port) -> platform/toolkits/dbt-testing/skills/add-unit-test/SKILL.md
- **skills/dbt/skills/troubleshooting-dbt-job-errors/SKILL.md** (port) -> platform/toolkits/dbt-govern/skills/troubleshoot-runs/SKILL.md, platform/src/pf/loops/registry.py
  Upstream's triage taxonomy is what the test-failure-triage loop classifies into.
- **skills/dbt-migration/skills/upgrading-dbt-core/SKILL.md** (port) -> platform/toolkits/dbt-migrate/skills/upgrade-and-migrate/SKILL.md
- **skills/dbt-migration/skills/migrating-dbt-core-to-fusion/SKILL.md** (port) -> platform/toolkits/dbt-migrate/skills/upgrade-and-migrate/SKILL.md

## Declined

- **skills/dbt/skills/configuring-dbt-mcp-server/SKILL.md**
  We ship our own MCP server. It exposes dbt alongside the graph, metrics and impact analysis behind one truncation policy; two servers would give an agent an ungoverned second route to the warehouse.
- **skills/dbt/skills/working-with-dbt-mesh/SKILL.md**
  `groups/` is our mesh. Cross-entity access is the roll-up project's ATTACH READ_ONLY, which is enforceable; mesh refs are not.
- **skills/dbt/skills/using-dbt-state/SKILL.md**
  State comparison answers "what changed". The knowledge graph answers "what breaks", which is the question the merge gate asks.
- **skills/dbt-extras/skills/creating-mermaid-dbt-dag/SKILL.md**
  The graph is already the DAG, and the UI renders it. A second rendering path drifts from the first.
- **skills/dbt-migration/skills/migrating-dbt-project-across-platforms/SKILL.md**
  DuckDB is the warehouse by design — one adapter, one dialect, no portability layer.
