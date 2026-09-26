---
type: Table
title: fct_mcx_futures_daily
description: Every MCX futures contract's session — all expiries — with price change,
  open-interest change and build-up, notional per lot and volume/OI. The term-structure
  and expiry-by-expiry view.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: ContractSession
okf_x_layer: marts
okf_x_grain: one MCX futures contract per trading day
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_mcx_futures_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `contract_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_mcx_contracts](/tables/dim_mcx_contracts.md) | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `days_to_expiry` | BIGINT |  | — | 0.00 |
| `expiry_bucket` | VARCHAR |  | — | 0.00 |
| `expiry_date` | DATE | reference_date | A date the row refers to that is not its own event time — the FX fix a price used, the day a duty was confirmed. No freshness monitor. | 1.00 |
| `expiry_rank` | BIGINT |  | — | 0.00 |
| `high_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `implied_quote_units_per_lot` | DOUBLE |  | — | 0.00 |
| `is_flagship` | BOOLEAN |  | — | 0.00 |
| `is_spec_verified` | BOOLEAN |  | — | 0.00 |
| `is_traded` | BOOLEAN |  | — | 0.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `low_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `notional_per_lot_inr` | DOUBLE |  | — | 0.00 |
| `oi_buildup` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `open_interest_change_lots` | BIGINT |  | — | 0.00 |
| `open_interest_lots` | BIGINT | quantity | Countable measure. | 1.00 |
| `open_interest_value_inr` | DOUBLE |  | — | 0.00 |
| `open_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `previous_close_price` | DOUBLE |  | — | 0.00 |
| `price_change` | DOUBLE |  | — | 0.00 |
| `price_change_pct` | DOUBLE |  | — | 0.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `quote_units_per_lot` | DOUBLE |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `session_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `trade_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `turnover_inr` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `volume_lots` | BIGINT | quantity | Countable measure. | 1.00 |
| `volume_to_oi_ratio` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [ContractSession](/concepts/ContractSession.md).

# Lineage

* **Upstream:** `int_mcx__futures_sessions`
* **Read by:** `report_mcx_[commodity]` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
