---
type: Vendor Upstream
title: OpenMetadata Standards
description: entity schemas our catalogue payloads validate against
resource: https://github.com/open-metadata/OpenMetadataStandards
tags:
- vendor
- spec
- Apache-2.0
status: stable
sources:
- id: openmetadata-standards:schemas/api/data/createGlossary.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/api/data/createGlossary.json
- id: openmetadata-standards:schemas/api/data/createGlossaryTerm.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/api/data/createGlossaryTerm.json
- id: openmetadata-standards:schemas/api/classification/createClassification.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/api/classification/createClassification.json
- id: openmetadata-standards:schemas/api/classification/createTag.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/api/classification/createTag.json
- id: openmetadata-standards:schemas/api/data/createMetric.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/api/data/createMetric.json
- id: openmetadata-standards:schemas/type/basic.json
  resource: https://github.com/open-metadata/OpenMetadataStandards
  title: schemas/type/basic.json
---

# OpenMetadata Standards

Pinned separately from the product, and this is the point of the split. The server validates what it is sent; without these schemas we would find out whether a payload was well-formed by watching an ingestion fail against a live catalogue. Here the same JSON Schemas run in the test suite, so an upstream field becoming required breaks the build at the pin bump instead.

## Adopted

- **schemas/api/data/createGlossary.json** (schema) -> platform/src/pf/projections/openmetadata.py
  The glossary payload is validated against this exact file.
- **schemas/api/data/createGlossaryTerm.json** (schema) -> platform/src/pf/projections/openmetadata.py
  Every ontology class and policy becomes one of these. `glossary`, `name` and `description` are required, which is why an undocumented concept publishes an explicit "no description in the ontology" rather than an empty string that would read as deliberate.
- **schemas/api/classification/createClassification.json** (schema) -> platform/src/pf/projections/openmetadata.py
- **schemas/api/classification/createTag.json** (schema) -> platform/src/pf/projections/openmetadata.py
  One tag per ontology role.
- **schemas/api/data/createMetric.json** (schema) -> platform/src/pf/projections/openmetadata.py
- **schemas/type/basic.json** (schema) -> platform/src/pf/projections/openmetadata.py
  `entityName` forbids `::` because that is the field separator in the `entityLink` grammar. `_om_name` enforces it rather than trusting our identifiers to be safe by luck.

## Declined

- **the RDF/OWL ontology and SHACL shapes**
  Tempting, because this platform already emits OWL. Declined for now: aligning our OWL export to OpenMetadata's ontology is a modelling decision about whose vocabulary wins, and making it silently inside a catalogue integration is how an ontology acquires a second owner.
- **the OpenAPI specification**
  We do not generate a client. `metadata` ships one, and a second hand-rolled client is a second thing to keep in step with the server.
