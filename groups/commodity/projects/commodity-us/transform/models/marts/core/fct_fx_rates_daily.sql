-- Grain: one currency per calendar day. Quote currency per 1 USD, carried
-- forward over days with no fix.
with fx as (
    select
        *,
        lag(usd_rate) over (partition by quote_currency_code order by rate_date) as prev_usd_rate
    from {{ ref('int_fx_rates__daily') }}
)

select
    fx_day_id,
    base_currency_code,
    quote_currency_code,
    rate_date,
    usd_rate,
    fixed_on,
    is_carried_forward,
    prev_usd_rate,
    {{ sf_safe_divide('usd_rate - prev_usd_rate', 'prev_usd_rate') }} as usd_rate_change_pct
from fx
