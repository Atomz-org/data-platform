---
type: Table
title: dim_commodities
description: 'Every tracked commodity — the group catalog — with this market''s facts
  beside it: the unit the local market quotes in and the duty in force today.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Commodity
okf_x_layer: marts
okf_x_grain: one commodity
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `category` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `commodity_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `commodity_name` | VARCHAR |  | — | 0.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `current_duty_basis` | VARCHAR |  | — | 0.00 |
| `current_duty_rate` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `current_tariff_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `exchange` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `has_spot_feed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `market_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |
| `price_basis` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `quote_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |
| `segment` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `spot_symbol` | VARCHAR |  | — | 0.00 |
| `unit_dimension` | VARCHAR |  | — | 0.00 |
| `yahoo_symbol` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [Commodity](/concepts/Commodity.md).
