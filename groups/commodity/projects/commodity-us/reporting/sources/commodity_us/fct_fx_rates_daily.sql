-- source extract for fct_fx_rates_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    fx_day_id,
    quote_currency_code,
    rate_date,
    usd_rate,
    base_currency_code,
    fixed_on,
    is_carried_forward,
    prev_usd_rate,
    usd_rate_change_pct
from main_marts.fct_fx_rates_daily
