---
type: Vendor Upstream
title: DuckDB Skills
description: driving DuckDB from an agent, read-only and truncated by policy
resource: https://github.com/duckdb/duckdb-skills
tags:
- vendor
- skills
- MIT
status: stable
sources:
- id: duckdb-skills:skills/query/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/query/SKILL.md
- id: duckdb-skills:skills/attach-db/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/attach-db/SKILL.md
- id: duckdb-skills:skills/install-duckdb/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/install-duckdb/SKILL.md
- id: duckdb-skills:skills/duckdb-docs/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/duckdb-docs/SKILL.md
- id: duckdb-skills:skills/read-file/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/read-file/SKILL.md
- id: duckdb-skills:skills/read-memories/SKILL.md
  resource: https://github.com/duckdb/duckdb-skills
  title: skills/read-memories/SKILL.md
---

# DuckDB Skills

DuckDB's own guidance on driving DuckDB from an agent.

## Adopted

- **skills/query/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/query/SKILL.md
  Ours is read-only and truncated by policy — schema plus <=20 rows.
- **skills/attach-db/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/attach-db/SKILL.md
  Session state moved into the project (`.duckdb-skills/state.sql`) so a sister company's ATTACH can never leak into another's session.
- **skills/install-duckdb/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/install-duckdb/SKILL.md
- **skills/duckdb-docs/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/duckdb-docs/SKILL.md
- **skills/read-file/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/read-file/SKILL.md
- **skills/read-memories/SKILL.md** (port) -> platform/toolkits/duckdb-ops/skills/read-memories/SKILL.md

## Declined

- **skills/convert-file/SKILL.md**
  File conversion enters this platform through dlt, where it is annotated and tracked.
- **skills/s3-explore/SKILL.md**
  Unannotated object-store browsing bypasses the ingest contract. Buckets are reached through a dlt filesystem source.
- **skills/spatial/SKILL.md**
  No geospatial concepts in the ontology. Add the skill when a class needs one.
