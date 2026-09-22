---
type: Table
title: fct_landed_prices_daily
description: 'Every market''s daily landed price side by side: as the market reports
  it (its currency per its unit) and in USD per the benchmark''s quote unit, with
  the import-parity premium each market adds over the benchmark. Prices are non-additive:
  aggregate within one commodity and one market.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per market per price date
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `benchmark_price_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `fx_fixed_on` | DATE |  | — | 0.00 |
| `import_parity_premium_pct` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `landed_price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `landed_price_local` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `landed_price_usd_per_quote_unit` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_markets](/tables/dim_markets.md) | 1.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `usd_fx_rate` | DECIMAL | exchange_rate | Units of quote currency per one unit of base currency. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [avg_import_parity_ratio](/metrics/avg_import_parity_ratio.md)
* [avg_landed_price_usd](/metrics/avg_landed_price_usd.md)
* [benchmark_usd_total_where_landed](/metrics/benchmark_usd_total_where_landed.md)
* [landed_usd_days](/metrics/landed_usd_days.md)
* [landed_usd_total](/metrics/landed_usd_total.md)
