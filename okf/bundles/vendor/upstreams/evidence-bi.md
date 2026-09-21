---
type: Vendor Upstream
title: Evidence BI (dbt semantic layer edition)
description: BI as a projection of the semantic layer, not a second place metrics
  live
resource: https://github.com/Atomz-org/Evidence-BI
tags:
- vendor
- reference
- not-stated-upstream
status: stable
sources:
- id: evidence-bi:evidence.config.yaml
  resource: https://github.com/Atomz-org/Evidence-BI
  title: evidence.config.yaml
- id: evidence-bi:components
  resource: https://github.com/Atomz-org/Evidence-BI
  title: components
- id: evidence-bi:queries
  resource: https://github.com/Atomz-org/Evidence-BI
  title: queries
- id: evidence-bi:docs
  resource: https://github.com/Atomz-org/Evidence-BI
  title: docs
---

# Evidence BI (dbt semantic layer edition)

Governed metrics plus designed dashboards — BI as a projection of the semantic layer rather than a place where metrics get redefined.

## Adopted

- **evidence.config.yaml** (shape) -> platform/src/pf/projections/evidence.py
- **components** (shape) -> platform/src/pf/projections/evidence.py
  Chart and layout conventions. The CVD-safe palette and the dual-axis prohibition are enforced mechanically in report_audit.py.
- **queries** (shape) -> platform/src/pf/projections/evidence.py
  Every query is compiled from a metric definition. A hand-written query in a page is a second definition, and the audit flags it.
- **docs** (shape) -> platform/toolkits/evidence-bi/skills/build-dashboard/SKILL.md

## Declined

- **cube/, rill/, canvas/ connectors**
  One semantic layer (MetricFlow) and one MDL projection. A second connector is a second definition of revenue.
- **deploy/**
  Deployment is out of scope for the platform; `pf report dev` is local.
