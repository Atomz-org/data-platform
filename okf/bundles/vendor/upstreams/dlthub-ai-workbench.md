---
type: Vendor Upstream
title: dltHub AI Workbench
description: toolkit/skill layout, and the annotate-then-generate ingest flow
resource: https://github.com/dlt-hub/dlthub-ai-workbench
tags:
- vendor
- skills
- dltHub-License-(proprietary)
status: stable
sources:
- id: dlthub-ai-workbench:TOOLKITS.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: TOOLKITS.md
- id: dlthub-ai-workbench:workbench/transformations/skills/annotate-sources/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/transformations/skills/annotate-sources/SKILL.md
- id: dlthub-ai-workbench:workbench/transformations/skills/create-ontology/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/transformations/skills/create-ontology/SKILL.md
- id: dlthub-ai-workbench:workbench/transformations/skills/generate-cdm/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/transformations/skills/generate-cdm/SKILL.md
- id: dlthub-ai-workbench:workbench/rest-api-pipeline/skills/create-rest-api-pipeline/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/rest-api-pipeline/skills/create-rest-api-pipeline/SKILL.md
- id: dlthub-ai-workbench:workbench/rest-api-pipeline/skills/debug-pipeline/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/rest-api-pipeline/skills/debug-pipeline/SKILL.md
- id: dlthub-ai-workbench:workbench/sql-database-pipeline/skills/find-source/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/sql-database-pipeline/skills/find-source/SKILL.md
- id: dlthub-ai-workbench:workbench/sql-database-pipeline/skills/create-sql-database-pipeline/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/sql-database-pipeline/skills/create-sql-database-pipeline/SKILL.md
- id: dlthub-ai-workbench:workbench/filesystem-pipeline/skills/create-filesystem-pipeline/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/filesystem-pipeline/skills/create-filesystem-pipeline/SKILL.md
- id: dlthub-ai-workbench:workbench/data-exploration/skills/explore-data/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/data-exploration/skills/explore-data/SKILL.md
- id: dlthub-ai-workbench:workbench/data-quality/skills/setup-data-quality/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/data-quality/skills/setup-data-quality/SKILL.md
- id: dlthub-ai-workbench:workbench/rest-api-pipeline/skills/optimize-rest-api-performance/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/rest-api-pipeline/skills/optimize-rest-api-performance/SKILL.md
- id: dlthub-ai-workbench:workbench/quick-start/skills/quick-start/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/quick-start/skills/quick-start/SKILL.md
- id: dlthub-ai-workbench:workbench/init/skills/setup-secrets/SKILL.md
  resource: https://github.com/dlt-hub/dlthub-ai-workbench
  title: workbench/init/skills/setup-secrets/SKILL.md
---

# dltHub AI Workbench

The workbench established the toolkit/skill layout this platform's `platform/toolkits/` follows, and the annotate-then-generate flow that our ontology layer is built on.

## Adopted

- **TOOLKITS.md** (shape) -> platform/toolkits/ROUTING.md
  Toolkit-of-skills packaging. Ours adds a precedence order, because four merged skill sets overlap and an agent that picks wrong answers a governed metric question with ad-hoc SQL.
- **workbench/transformations/skills/annotate-sources/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/annotate-source/SKILL.md, platform/src/pf/ontology/annotate.py
  Upstream annotates for its own transformation engine. Ours drives staging generation, PII policy, monitors, graph edges and conformance — the annotation is the contract, not a hint.
- **workbench/transformations/skills/create-ontology/SKILL.md** (shape) -> platform/src/pf/ontology/concepts.yaml, platform/src/pf/ontology/model.py
  Upstream's ontology is per-pipeline. Ours is three-layered (platform / group / project) so sister companies share a vocabulary without inheriting each other's invented terms.
- **workbench/transformations/skills/generate-cdm/SKILL.md** (shape) -> platform/src/pf/runtime/staging.py
  Common-model generation became 1:1 staging with role-driven cleaning.
- **workbench/rest-api-pipeline/skills/create-rest-api-pipeline/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/create-rest-pipeline/SKILL.md
  Independent rewrite against dlt Core's `rest_api` and `RESTClient`; it names no dltHub command. Ours adds the parent-yields-one-page rule for dependent resources, cursors per key in resource state, and the platform's contract, `rows` check and annotation steps.
- **workbench/rest-api-pipeline/skills/debug-pipeline/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/debug-pipeline/SKILL.md
  dlt Core's `dlt pipeline` commands in place of `dlthub local pipeline`, plus the dataset API for row counts, which is what the seed reads.
- **workbench/sql-database-pipeline/skills/find-source/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/find-source/SKILL.md
- **workbench/sql-database-pipeline/skills/create-sql-database-pipeline/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/create-sql-pipeline/SKILL.md
- **workbench/filesystem-pipeline/skills/create-filesystem-pipeline/SKILL.md** (port) -> platform/toolkits/dlt-ingest/skills/create-filesystem-pipeline/SKILL.md
- **workbench/data-exploration/skills/explore-data/SKILL.md** (port) -> platform/toolkits/dlt-explore/skills/explore-data/SKILL.md
- **workbench/data-quality/skills/setup-data-quality/SKILL.md** (port) -> platform/toolkits/dlt-quality/skills/setup-data-quality/SKILL.md
- **workbench/rest-api-pipeline/skills/optimize-rest-api-performance/SKILL.md** (port) -> platform/toolkits/dlt-performance/skills/optimize-performance/SKILL.md
- **workbench/quick-start/skills/quick-start/SKILL.md** (port) -> platform/toolkits/platform-init/skills/quick-start/SKILL.md
- **workbench/init/skills/setup-secrets/SKILL.md** (shape) -> platform/src/pf/mcp/server.py
  Became `secrets_view_redacted` / `secrets_update_fragment`. An agent can write a credential fragment but can never read one back into context.

## Declined

- **dltHub Platform deploy skills (one-shot, deploy-run-sample-pipeline)**
  They target dltHub's hosted runtime. This platform deploys to Dagster, and the request was explicitly dlt Core rather than dltHub.
- **workbench/init/skills/dlthub-router/SKILL.md**
  Our router is ROUTING.md plus the knowledge graph, which routes on structure rather than skill name.
