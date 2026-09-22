---
type: Concept
title: Contract
description: A negotiated agreement, usually with custom terms.
okf_x_defined_in: platform
okf_x_parent: Agreement
okf_x_identity: contract_id
okf_x_kg_node: concept:Contract
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Contract.md
---

Defined by the platform ontology: [Contract](../../../../../../platform/okf/concepts/Contract.md).

# Instantiated by

* [int_supplier_contract_expiry](/tables/int_supplier_contract_expiry.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `contract_id` | string | natural_key |
| `signed_at` | timestamp | event_time |

# Relations

* Contract signed by Organization — 

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
