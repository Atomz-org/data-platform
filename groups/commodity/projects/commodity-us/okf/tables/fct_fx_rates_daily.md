---
type: Table
title: fct_fx_rates_daily
description: Daily USD fixes (quote currency per 1 USD) with day-on-day change; the
  tracker's FX ticker.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: one currency per calendar day
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `base_currency_code` | VARCHAR |  | — | 0.00 |
| `fixed_on` | DATE |  | — | 0.00 |
| `fx_day_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `is_carried_forward` | BOOLEAN |  | — | 0.00 |
| `prev_usd_rate` | DOUBLE |  | — | 0.00 |
| `quote_currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `rate_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `usd_rate` | DECIMAL | exchange_rate | Units of quote currency per one unit of base currency. | 1.00 |
| `usd_rate_change_pct` | DOUBLE |  | — | 0.00 |
