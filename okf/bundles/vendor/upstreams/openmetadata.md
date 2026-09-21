---
type: Vendor Upstream
title: OpenMetadata
description: catalogue ingestion, and the dbt connector for lineage
resource: https://github.com/open-metadata/OpenMetadata
tags:
- vendor
- engine
- Apache-2.0
status: stable
sources:
- id: openmetadata:ingestion/src/metadata/workflow/metadata.py
  resource: https://github.com/open-metadata/OpenMetadata
  title: ingestion/src/metadata/workflow/metadata.py
---

# OpenMetadata

The catalogue is the surface for people who do not read YAML. What made it worth integrating rather than reimplementing is the dbt connector: it reads manifest.json and catalog.json and produces column-level lineage, which we would otherwise be re-deriving from the knowledge graph, worse, and then reconciling two answers.

## Adopted

- **ingestion/src/metadata/workflow/metadata.py** (shape) -> platform/src/pf/tools/openmetadata.py
  The workflow shape our generated `catalog/ingestion.yaml` conforms to — source / sink / workflowConfig. Run through the `metadata` CLI rather than by importing MetadataWorkflow, so the pinned wheel owns its own execution and we own only the configuration.

## Declined

- **the Airflow-based ingestion scheduler**
  OpenMetadata schedules ingestion with its own Airflow. This platform already orchestrates with Dagster, and the catalogue must describe the build that just happened — so ingestion is a Dagster asset downstream of the marts, not a separate timer that drifts from the warehouse between runs.
- **writing back from the catalogue to the ontology**
  The ontology is canonical in YAML, in git, judged by `pf check` and the gate. A catalogue that can silently redefine a concept is a second source of truth, and then neither side can say what `Customer` means.
- **emitting tables and lineage from our own graph**
  `metadata ingest-dbt` already does it from the dbt artefacts. Two descriptions of one table drift apart, and the catalogue shows whichever ran last.
