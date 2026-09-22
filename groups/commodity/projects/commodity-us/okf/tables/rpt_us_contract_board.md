---
type: Table
title: rpt_us_contract_board
description: 'One row per tracked US exchange contract: the latest import-parity value
  per quote basis and per lot, and how old its benchmark is.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one US exchange contract
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_us_contract_board
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `contract_code` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `exchange` | VARCHAR |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_stale` | BOOLEAN |  | — | 0.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `lot_value_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `price_age_days` | BIGINT |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_equivalent_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Lineage

* **Upstream:** [fct_us_contract_values_daily](/tables/fct_us_contract_values_daily.md)
* **Read by:** `report_us_contracts` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
