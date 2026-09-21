---
type: Vendor Upstream
title: Dagster Skills
description: asset-first orchestration; @dbt_assets is what makes lineage cross dlt/dbt
resource: https://github.com/dagster-io/skills
tags:
- vendor
- skills
- Apache-2.0
status: stable
sources:
- id: dagster-skills:skills/dagster-expert/skills/dagster-expert/SKILL.md
  resource: https://github.com/dagster-io/skills
  title: skills/dagster-expert/skills/dagster-expert/SKILL.md
- id: dagster-skills:skills/dignified-python/skills/dignified-python/SKILL.md
  resource: https://github.com/dagster-io/skills
  title: skills/dignified-python/skills/dignified-python/SKILL.md
---

# Dagster Skills

Dagster's own asset-first idioms, which our runtime factory generates against.

## Adopted

- **skills/dagster-expert/skills/dagster-expert/SKILL.md** (port) -> platform/toolkits/dagster-orchestrate/skills/build-assets/SKILL.md, platform/src/pf/runtime/dagster_runtime.py
  Asset-first modelling, external assets for dlt sources, and @dbt_assets with a custom translator — which is what makes lineage cross the dlt/dbt boundary instead of collapsing into one opaque node.
- **skills/dignified-python/skills/dignified-python/SKILL.md** (port) -> platform/toolkits/python-standards/skills/dignified-python/SKILL.md

## Declined

- **Dagster+ / cloud deployment guidance**
  Code locations here are local processes, one per project, for genuine sister parallelism.
