---
type: Table
title: fct_mcx_lot_equivalents_daily
description: The landed price of each MCX bullion and base-metal contract, per its
  quote basis and per lot — GOLDM per 10 g, ALUMINI and ZINCMINI per kg and per 1
  MT lot. Computed from international benchmarks — not an MCX quote.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one MCX contract per price date
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `contract_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `exchange` | VARCHAR |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `lot_equivalent_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `lot_value_inr` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `price_basis` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_equivalent_inr` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).
