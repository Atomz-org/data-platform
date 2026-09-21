---
type: Context Card
title: commodity/commodity-india
description: Always-in-context index for commodity/commodity-india.
tags:
- context-card
- commodity
- commodity-india
status: stable
---

## commodity-india — data index

**Group:** commodity · **Concepts in use:** FxRate, PriceObservation
**Sources (2):** gold_api, yahoo_finance

**Raw tables (3):**
- `futures_prices` → PriceObservation — one commodity per trading day
- `fx_rates` → FxRate — one currency pair per day
- `spot_prices` → PriceObservation — one precious metal per gold-api update

**Staging models (3):** `stg_gold_api__spot_prices`, `stg_yahoo_finance__futures_prices`, `stg_yahoo_finance__fx_rates`

**Intermediate models (2):** `int_commodity_prices__usd`, `int_fx_rates__daily`

**Marts (8):**
- `dim_commodities` — grain: one commodity — Every tracked commodity — the group catalog — with this market's facts beside it: the unit the local market quotes in and the duty in force today.
- `fct_commodity_prices_daily` — grain: one commodity per price date — Daily benchmark price per commodity in USD per quote unit, with day-on-day change, 20/50-day moving averages and a 252-trading-day range. Prices are non-additive: aggregate within one commodity only.
- `fct_fx_rates_daily` — grain: one currency per calendar day — Daily USD fixes (quote currency per 1 USD) with day-on-day change; the tracker's FX ticker.
- `fct_landed_prices_daily` — grain: one commodity per price date — Import landed price per commodity per day in this market's currency per its market unit: benchmark × USD/local × (1 + customs duty). The benchmark stands in for CIF value — freight, insurance, landing charges and local taxes are excluded. History before a tariff's `confirmed_from` uses today's rate; filter on `is_duty_rate_confirmed` when that matters. The same shape in every sister; `market_code` and `currency_code` say whose it is.
- `fct_mcx_lot_equivalents_daily` — grain: one MCX contract per price date — The landed price of each MCX bullion and base-metal contract, per its quote basis and per lot — GOLDM per 10 g, ALUMINI and ZINCMINI per kg and per 1 MT lot. Computed from international benchmarks — not an MCX quote.
- `fct_precious_metal_retail_prices_daily` — grain: one precious metal per purity grade per price date — Landed gold and silver in Indian retail conventions — per gram, 10 g and kg, by purity.
- `rpt_commodity_price_board` — grain: one commodity — One row per tracked commodity: latest benchmark and move, 252-day range, landed price in this market's currency, duty, precious-metal spot basis, and staleness. The table behind the commodity price board.
- `rpt_mcx_contract_board` — grain: one MCX contract — One row per tracked MCX contract: the latest landed equivalent per quote basis and per lot, and how old its benchmark is. ZINC and ZINCMINI carry the last indicative LME level and read stale until it is refreshed.

**Metrics (15):**
- `avg_benchmark_price_usd` (ratio) — Avg Benchmark Price (USD)
- `avg_duty_local` (ratio) — Avg Customs Duty (market currency)
- `avg_landed_price_local` (ratio) — Avg Landed Price (market currency)
- `avg_usd_fx_rate` (ratio) — Avg Applied FX Rate
- `benchmark_price_days` (simple) — Priced Days
- `benchmark_price_mom_change` (derived) — Benchmark Price MoM Change
- `benchmark_price_usd_total` (simple) — Benchmark Price Total (component)
- `contracts_traded` (simple) — Contracts Traded
- `duty_local_total` (simple) — Customs Duty Total (component)
- `landed_price_days` (simple) — Days With a Landed Price
- `landed_price_local_total` (simple) — Landed Price Total (component)
- `landed_price_mom_change` (derived) — Landed Price MoM Change
- `period_high_price_usd` (simple) — Period High (USD)
- `period_low_price_usd` (simple) — Period Low (USD)
- `usd_fx_rate_total` (simple) — Applied FX Rate Total (component)

**Common dimensions:** category, commodity_id, commodity_name, currency_code, exchange, is_carried_forward, is_duty_rate_confirmed, is_import_prohibited, market_code, market_unit, price_basis, price_date, +4 more

**Exposures (18):**
- `commodity_price_board` (dashboard) ← Commodity Research
- `report_index` (dashboard) ← data-platform
- `report_landed_cost` (dashboard) ← data-platform
- `report_mcx_contracts` (dashboard) ← data-platform
- `report_metrics_avg_benchmark_price_usd` (dashboard) ← data-platform
- `report_metrics_avg_duty_local` (dashboard) ← data-platform
- `report_metrics_avg_landed_price_local` (dashboard) ← data-platform
- `report_metrics_avg_usd_fx_rate` (dashboard) ← data-platform
- `report_metrics_benchmark_price_days` (dashboard) ← data-platform
- `report_metrics_benchmark_price_usd_total` (dashboard) ← data-platform
- `report_metrics_contracts_traded` (dashboard) ← data-platform
- `report_metrics_duty_local_total` (dashboard) ← data-platform
- …and 6 more (use `kg_search`)

**Decisions (5):**
- `ADR-0001` — Duty rates are back-applied to history, and flagged
- `ADR-0002` — Prices carry the `unit_price` role, not `money_amount`
- `ADR-0003` — Mean prices are ratio metrics, not `average` measures
- `ADR-0004` — dlt Core lands the raw stage; dbt stages it
- `ADR-0005` — commodity-india is one market of many

**Known gaps:**
- 1 raw table(s) reach no metric: `spot_prices`

_Query the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`._
