---
type: Table
title: fct_landed_prices_daily
description: 'Import landed price per commodity per day in this market''s currency
  per its market unit: benchmark × USD/local × (1 + customs duty). The benchmark stands
  in for CIF value — freight, insurance, landing charges and local taxes are excluded.
  History before a tariff''s `confirmed_from` uses today''s rate; filter on `is_duty_rate_confirmed`
  when that matters. The same shape in every sister; `market_code` and `currency_code`
  say whose it is.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per price date
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_landed_prices_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `assessable_value_local` | DECIMAL |  | — | 0.00 |
| `benchmark_price_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `benchmark_usd_per_market_unit` | DOUBLE |  | — | 0.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `duty_basis` | VARCHAR |  | — | 0.00 |
| `duty_local` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `effective_duty_rate` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `fx_fixed_on` | DATE |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `landed_price_change_local` | DECIMAL |  | — | 0.00 |
| `landed_price_change_pct` | DOUBLE |  | — | 0.00 |
| `landed_price_local` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `market_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `tariff_id` | VARCHAR |  | — | 0.00 |
| `usd_fx_rate` | DECIMAL | exchange_rate | Units of quote currency per one unit of base currency. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [avg_duty_local](/metrics/avg_duty_local.md)
* [avg_landed_price_local](/metrics/avg_landed_price_local.md)
* [avg_usd_fx_rate](/metrics/avg_usd_fx_rate.md)
* [duty_local_total](/metrics/duty_local_total.md)
* [landed_price_days](/metrics/landed_price_days.md)
* [landed_price_local_total](/metrics/landed_price_local_total.md)
* [landed_price_mom_change](/metrics/landed_price_mom_change.md)
* [usd_fx_rate_total](/metrics/usd_fx_rate_total.md)

# Lineage

* **Upstream:** `int_commodity_prices__usd`, `int_fx_rates__daily`
* **Downstream:** [fct_us_contract_values_daily](/tables/fct_us_contract_values_daily.md), [rpt_commodity_price_board](/tables/rpt_commodity_price_board.md)
* **Read by:** `report_import_parity` (data-platform), `report_index` (data-platform), `report_metrics_avg_duty_local` (data-platform), `report_metrics_avg_landed_price_local` (data-platform), `report_metrics_avg_usd_fx_rate` (data-platform), `report_metrics_duty_local_total` (data-platform), and 3 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
