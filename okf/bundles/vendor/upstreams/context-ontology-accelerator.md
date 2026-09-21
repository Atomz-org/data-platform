---
type: Vendor Upstream
title: AWS Context Ontology Accelerator
description: Scan → Model → Serve induction, with a steward in the middle
resource: https://github.com/aws/context-ontology-accelerator
tags:
- vendor
- reference
- Apache-2.0
status: stable
sources:
- id: context-ontology-accelerator:packages/context-manager
  resource: https://github.com/aws/context-ontology-accelerator
  title: packages/context-manager
- id: context-ontology-accelerator:packages/vkg
  resource: https://github.com/aws/context-ontology-accelerator
  title: packages/vkg
- id: context-ontology-accelerator:packages/mcp-server
  resource: https://github.com/aws/context-ontology-accelerator
  title: packages/mcp-server
- id: context-ontology-accelerator:scripts/agents/pr-review
  resource: https://github.com/aws/context-ontology-accelerator
  title: scripts/agents/pr-review
---

# AWS Context Ontology Accelerator

The Scan -> Model -> Serve shape for inducing an ontology from real systems, with a steward in the middle. Induction proposes; a person decides.

## Adopted

- **packages/context-manager** (shape) -> platform/src/pf/ontology/induct.py, platform/src/pf/ontology/proposal.py
  Scan reads statistics rather than names, so cardinality comes from distinct counts. The steward loop — every axiom carrying its evidence, nothing auto-applied for PII or relations — is ours on top.
- **packages/vkg** (shape) -> platform/src/pf/kg/build.py
  Virtual knowledge graph over physical tables; ours is materialised in DuckDB and queried by agents.
- **packages/mcp-server** (shape) -> platform/src/pf/mcp/server.py
  Serving the ontology to agents over MCP rather than as a file to read.
- **scripts/agents/pr-review** (shape) -> .github/workflows/pr-report.yml

## Declined

- **infra/ (CDK stacks, Lambda, state machines)**
  This platform is local-first and runs on Dagster. The AWS deployment surface is not ours.
- **packages/web-app**
  `pf ui` is the control plane, and it reads the same graph the agents do.
