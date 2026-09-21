---
type: Vendor Upstream
title: OpenTopology (otop-core)
description: 'the traceability chain: intent → constraint → artifact → evidence'
resource: https://github.com/opentopology/opentopology
tags:
- vendor
- spec
- Apache-2.0
status: stable
sources:
- id: opentopology:schemas/otop-core-v0.2.schema.json
  resource: https://github.com/opentopology/opentopology
  title: schemas/otop-core-v0.2.schema.json
- id: opentopology:specs/otop-core-0.2.md
  resource: https://github.com/opentopology/opentopology
  title: specs/otop-core-0.2.md
---

# OpenTopology (otop-core)

otop's contribution is not entity modelling — it is the traceability chain intent -> constraint -> artifact -> evidence. That is what turns "we have a PII rule" into "here is the check, and here is the run that proves it fired".

## Adopted

- **schemas/otop-core-v0.2.schema.json** (schema) -> platform/src/pf/projections/otop.py, platform/src/pf/ontology/policy.yaml
  Our policy layer is emitted as an otop 0.2 manifest and validated against this exact file. If upstream tightens the schema, the export fails here rather than in a consumer.
- **specs/otop-core-0.2.md** (shape) -> platform/src/pf/ontology/policy.yaml
  Relationship vocabulary taken verbatim: governed_by, implemented_by, verified_by. Renaming them locally would break every otop consumer.

## Declined

- **signatures / attestation blocks**
  Nothing signs evidence in this platform yet. An unsigned signature block is worse than none — it implies a guarantee that does not exist.
- **otop-core-0.1 schema**
  Superseded by 0.2. We track one version so there is one answer to "does this conform".
