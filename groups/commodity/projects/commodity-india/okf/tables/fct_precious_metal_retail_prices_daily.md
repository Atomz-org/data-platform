---
type: Table
title: fct_precious_metal_retail_prices_daily
description: Landed gold and silver in Indian retail conventions — per gram, 10 g
  and kg, by purity.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one precious metal per purity grade per price date
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `fineness` | DOUBLE |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `price_inr_per_10g` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `price_inr_per_gram` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `price_inr_per_kg` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `purity_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `purity_label` | VARCHAR |  | — | 0.00 |
| `retail_price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).
