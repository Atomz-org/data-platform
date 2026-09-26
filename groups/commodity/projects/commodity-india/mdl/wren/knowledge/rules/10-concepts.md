# Concepts

What each model is an instance of, and how a row is identified.

| model | concept | identity | meaning |
|---|---|---|---|
| `dim_commodities` | Commodity | commodity_id | A traded raw material with an international benchmark, quoted per a physical unit. |
| `dim_mcx_contracts` | ExchangeContract | contract_id | A standardised exchange-traded derivative on one commodity — a futures contract, or one expiry's chain of options — identified by exchange, instrument, contract code and expiry. |
| `fct_commodity_prices_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_commodity_trading_signals_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_fx_rates_daily` | — | fx_day_id |  |
| `fct_landed_price_attribution_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_landed_prices_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_mcx_commodity_daily` | ContractSession | session_id | One exchange contract's trading day as the exchange settles it — open, high, low, close, the previous settlement, volume and open interest in lots, and turnover. Prices are per the contract's quote basis and never summed; volume and turnover are additive within a day. |
| `fct_mcx_commodity_rollup_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_mcx_futures_daily` | ContractSession | session_id | One exchange contract's trading day as the exchange settles it — open, high, low, close, the previous settlement, volume and open interest in lots, and turnover. Prices are per the contract's quote basis and never summed; volume and turnover are additive within a day. |
| `fct_mcx_lot_equivalents_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `fct_mcx_options_daily` | ContractSession | session_id | One exchange contract's trading day as the exchange settles it — open, high, low, close, the previous settlement, volume and open interest in lots, and turnover. Prices are per the contract's quote basis and never summed; volume and turnover are additive within a day. |
| `fct_precious_metal_retail_prices_daily` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `rpt_commodity_price_board` | Commodity | commodity_id | A traded raw material with an international benchmark, quoted per a physical unit. |
| `rpt_mcx_commodity_board` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |
| `rpt_mcx_contract_board` | PriceObservation | quote_id | One benchmark price for one commodity at one point in time. Never summed. |

## Column roles

Every column carries `pf.role` in the manifest. What a role means for a query:

| role | rule |
|---|---|
| `currency_code` | ISO 4217 code of the money columns beside it |
| `event_time` | the time axis; the default for any trend or period |
| `exchange_rate` | as named |
| `flag` | true/false; count the trues |
| `foreign_key` | a join to another model along a declared relationship |
| `geo_country` | as named |
| `money_amount` | additive within one currency; the sibling currency_code says which |
| `natural_key` | identity of the row; count it, never sum it |
| `quantity` | additive count or volume; never money |
| `rate_fraction` | as named |
| `reference_date` | a date attribute, not the time axis |
| `status_enum` | a fixed set of values; see the enumerations |
| `unit_of_measure` | as named |
| `unit_price` | a price per unit — never summed, never averaged across rows; weight by quantity or take a ratio of additive parts |
