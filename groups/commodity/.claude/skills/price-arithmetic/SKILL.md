---
name: price-arithmetic
description: Convert a commodity price in the conformed order, minor currency then unit then FX then duty, each step once, in intermediate or a mart, never in staging or dlt.
---
# Price arithmetic

A price is a `unit_price` (ADR-0002): one number per unit of measure, qualified
by a `currency_code` and a `unit_of_measure`. It is not additive, and it is
converted in one order. Each step happens exactly once, downstream of staging:

1. **Minor to major currency.** `to_major_currency(price, currency)` divides
   `USX` (US cents) and `GBX` (pence) by 100; `major_currency_code(currency)`
   turns them into `USD` and `GBP`. Yahoo quotes CBOT grains, ICE softs and CME
   livestock in cents, and 732.5 is a plausible dollar price for many
   benchmarks, so a cents quote read as dollars is a 100x error that no range
   test catches on its own. In commodity-india this is
   `int_commodity_prices__usd`, the only model that converts cents, and where
   the live futures and the indicative levels take one shape.
2. **Quote unit to market unit.** `reprice_per_unit(price, from_base_units,
   to_base_units)`, both sizes read from the group's `units_of_measure` seed
   (`base_units_per_unit`, joined on `unit_code`). Valid only inside one
   `dimension`: mass to mass, never `troy_oz` to `barrel`. A sister enforces
   that with singular tests (`assert_units_convert_within_one_dimension`,
   `assert_mcx_units_convert_within_one_dimension`). Never hardcode 31.1035 or
   0.4536; the seed is the one place a factor lives.
3. **FX.** `int_fx_rates__daily` holds a `usd_rate` for every calendar day per
   currency, the last fix carried over weekends and holidays (`fixed_on`,
   `is_carried_forward`). Equi-join on the price date; no ASOF join and no
   IGNORE NULLS, because both differ by adapter.
4. **Duty.** Per market, so from the sister's own duty seed, in the sister's
   marts, never in the group.

Where each step may live:

| Layer | Allowed |
|---|---|
| dlt resource | nothing: land the quote as the exchange states it, currency and unit included |
| staging | nothing: generated 1:1, `unit_price` passes through untouched at full precision |
| intermediate | steps 1 to 3; commodity-india does 1 here and prepares the daily rate for 3 here |
| marts | the remaining steps, once; `fct_india_landed_prices_daily` does 2, 3 and 4 in one pass |

A mart that shows an already landed price in another unit (an MCX quote basis
and lot, a retail kilogram) calls `reprice_per_unit` on the landed price. That
is a restatement of one conversion, not a second one, and it gets no mean
metric of its own.

A mean price is a `ratio` metric, a `sum` component over a `count` component,
with `commodity_id` the first dimension so a query groups per commodity
(ADR-0003). Never `sum` a price on its own, and never average across
commodities.
