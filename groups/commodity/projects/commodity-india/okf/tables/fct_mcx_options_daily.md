---
type: Table
title: fct_mcx_options_daily
description: 'Each MCX option chain per session against its underlying future: put/call
  ratio by OI and volume, positioning, call and put OI walls, max pain and their distance
  from the underlying.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: ContractSession
okf_x_layer: marts
okf_x_grain: one MCX option chain per trading day
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_mcx_options_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `call_open_interest_lots` | VARCHAR |  | — | 0.00 |
| `call_volume_lots` | VARCHAR |  | — | 0.00 |
| `call_wall_distance_pct` | DOUBLE |  | — | 0.00 |
| `call_wall_strike` | DOUBLE |  | — | 0.00 |
| `chain_day_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `contract_code` | VARCHAR |  | — | 0.00 |
| `contract_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_mcx_contracts](/tables/dim_mcx_contracts.md) | 1.00 |
| `days_to_expiry` | BIGINT |  | — | 0.00 |
| `expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `expiry_rank` | BIGINT |  | — | 0.00 |
| `is_flagship` | BOOLEAN |  | — | 0.00 |
| `is_latest` | BOOLEAN |  | — | 0.00 |
| `max_pain_distance_pct` | DOUBLE |  | — | 0.00 |
| `max_pain_strike` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `notional_turnover_inr` | DECIMAL |  | — | 0.00 |
| `positioning` | VARCHAR |  | — | 0.00 |
| `premium_turnover_inr` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `put_call_ratio_oi` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `put_call_ratio_volume` | DOUBLE |  | — | 0.00 |
| `put_open_interest_lots` | VARCHAR |  | — | 0.00 |
| `put_volume_lots` | VARCHAR |  | — | 0.00 |
| `put_wall_distance_pct` | DOUBLE |  | — | 0.00 |
| `put_wall_strike` | DOUBLE |  | — | 0.00 |
| `strikes_listed` | BIGINT |  | — | 0.00 |
| `trade_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `underlying_close_price` | DOUBLE |  | — | 0.00 |
| `underlying_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |

# Concept

Instantiates [ContractSession](/concepts/ContractSession.md).

# Lineage

* **Upstream:** `int_mcx__futures_sessions`, `int_mcx__options_chain_daily`
* **Downstream:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md), [rpt_mcx_commodity_board](/tables/rpt_mcx_commodity_board.md)
* **Read by:** `report_mcx_[commodity]` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
