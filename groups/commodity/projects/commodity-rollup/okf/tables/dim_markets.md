---
type: Table
title: dim_markets
description: Every market registered in the group's `markets` seed, with whether its
  sister is reporting and what the roll-up has received from it.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Market
okf_x_layer: marts
okf_x_grain: one market
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `commodities_priced` | BIGINT |  | — | 0.00 |
| `country_code` | VARCHAR | geo_country | ISO 3166 country code. | 1.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `first_price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `home_exchange` | VARCHAR |  | — | 0.00 |
| `is_reporting` | BOOLEAN |  | — | 0.00 |
| `landed_price_rows` | BIGINT |  | — | 0.00 |
| `latest_price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `market_code` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `market_name` | VARCHAR |  | — | 0.00 |
| `project` | VARCHAR |  | — | 0.00 |
| `timezone` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [Market](/concepts/Market.md).
