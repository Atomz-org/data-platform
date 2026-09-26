---
type: Table
title: dim_mcx_contracts
description: 'The MCX expiry calendar: every futures contract and option chain listed
  for the tracked codes, its commodity, lot and quote basis, days to expiry, and whether
  it traded in the latest session.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: ExchangeContract
okf_x_layer: marts
okf_x_grain: one MCX futures contract or option expiry chain
okf_x_columns_withheld: 0
okf_x_kg_node: model:dim_mcx_contracts
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `contract_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `contract_kind` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `days_to_expiry` | BIGINT |  | — | 0.00 |
| `exchange` | VARCHAR |  | — | 0.00 |
| `expiry_date` | DATE | reference_date | A date the row refers to that is not its own event time — the FX fix a price used, the day a duty was confirmed. No freshness monitor. | 1.00 |
| `instrument_type` | VARCHAR |  | — | 0.00 |
| `is_flagship` | BOOLEAN |  | — | 0.00 |
| `is_open` | BOOLEAN | flag | A true/false state of the row (prohibited, confirmed). Passes through staging; never aggregated. | 1.00 |
| `is_traded_today` | BOOLEAN |  | — | 0.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [ExchangeContract](/concepts/ExchangeContract.md).

# Lineage

* **Upstream:** `stg_mcx__contract_master`, `stg_mcx__futures_bhavcopy`
* **Read by:** `report_mcx_[commodity]` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
