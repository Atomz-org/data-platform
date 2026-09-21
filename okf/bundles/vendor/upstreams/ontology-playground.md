---
type: Vendor Upstream
title: Microsoft Ontology Playground
description: what a business ontology actually looks like, and RDF/XML fidelity
resource: https://github.com/microsoft/Ontology-Playground
tags:
- vendor
- reference
- MIT
status: stable
sources:
- id: ontology-playground:catalogue/official
  resource: https://github.com/microsoft/Ontology-Playground
  title: catalogue/official
- id: ontology-playground:docs
  resource: https://github.com/microsoft/Ontology-Playground
  title: docs
---

# Microsoft Ontology Playground

A working reference for how a business ontology is actually shaped — classes with identity, datatype properties, and object properties with domain/range — plus round-tripping through RDF/XML.

## Adopted

- **catalogue/official** (shape) -> platform/src/pf/ontology/concepts.yaml, platform/src/pf/ontology/topology.yaml
  Their ecommerce and finance catalogue entries model the same Customer/Order/Payment core. Ours matched against them rather than inventing a vocabulary.
- **docs** (shape) -> platform/src/pf/projections/owl.py
  RDF/XML fidelity — cardinality projected as FunctionalProperty / InverseFunctionalProperty so an external OWL tool reads what we meant.

## Declined

- **The React/Vite playground application (src/, api/)**
  It is an editor. Our ontology is edited as YAML in the repo and reviewed as a diff.
- **api/generate-ontology**
  We induce from what actually landed in the warehouse (`pf semantic scan`) rather than from a prompt, so every axiom carries observed evidence.
