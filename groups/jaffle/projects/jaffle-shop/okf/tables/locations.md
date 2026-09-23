---
type: Table
title: locations
description: Every store, one row per location, straight from the source.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:locations
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `location_name` | VARCHAR |  | — | 0.00 |
| `opened_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `tax_rate` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** `stg_locations`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
