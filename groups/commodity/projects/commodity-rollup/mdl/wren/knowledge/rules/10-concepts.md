# Concepts

What each model is an instance of, and how a row is identified.

| model | concept | identity | meaning |
|---|---|---|---|
| `dim_commodities` | Commodity | commodity_id | A traded raw material with an international benchmark, quoted per a physical unit. |
| `dim_markets` | Market | market_code | A jurisdiction commodities are landed in — one sister project, one currency, one customs regime. The tenant of this family. |
| `fct_landed_prices_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_market_spreads_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `rpt_market_comparison_board` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |

## Column roles

Every column carries `pf.role` in the manifest. What a role means for a query:

| role | rule |
|---|---|
| `currency_code` | ISO 4217 code of the money columns beside it |
| `event_time` | the time axis; the default for any trend or period |
| `exchange_rate` | as named |
| `foreign_key` | a join to another model along a declared relationship |
| `geo_country` | as named |
| `natural_key` | identity of the row; count it, never sum it |
| `quantity` | additive count or volume; never money |
| `rate_fraction` | as named |
| `status_enum` | a fixed set of values; see the enumerations |
| `unit_of_measure` | as named |
| `unit_price` | a price per unit — never summed, never averaged across rows; weight by quantity or take a ratio of additive parts |
