---
type: Table
title: fct_us_contract_values_daily
description: The import-parity value of each tracked US exchange contract per its
  quote basis and per lot — GC per troy ounce and per 100 oz lot, HG per pound and
  per 25,000 lb lot, ALI per tonne with Section 232 duty grossed on. Computed from
  the benchmark, not a separate contract quote.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one US exchange contract per price date
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `contract_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `contract_value_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `exchange` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `lot_value_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `price_basis` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_equivalent_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).
