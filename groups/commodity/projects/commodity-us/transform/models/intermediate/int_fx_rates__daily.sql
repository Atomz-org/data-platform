-- Grain: one currency per calendar day, from its first fix to today.
-- Markets price on days FX does not fix (and the reverse), so weekends and
-- holidays carry the last fix forward. `fixed_on` says which fix a day uses.
-- Portable on purpose: no ASOF join, no IGNORE NULLS — both differ by adapter.
with fx as (
    select
        quote_currency_code                                           as currency_code,
        cast(rate_at as date)                                         as rate_date,
        rate
    from {{ ref('stg_yahoo_finance__fx_rates') }}
    where base_currency_code = 'USD'
),

first_fix as (
    select currency_code, min(rate_date) as first_date
    from fx
    group by currency_code
),

calendar as (
    select cast(date_day as date) as calendar_date
    from ({{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date=dbt.dateadd('day', 1, 'current_date')
    ) }}) as spine
),

days as (
    select f.currency_code, c.calendar_date
    from first_fix as f
    inner join calendar as c on c.calendar_date >= f.first_date
),

last_fix as (
    select
        d.currency_code,
        d.calendar_date,
        max(fx.rate_date) over (
            partition by d.currency_code
            order by d.calendar_date
            rows between unbounded preceding and current row
        )                                                             as fixed_on
    from days as d
    left join fx
        on fx.currency_code = d.currency_code
        and fx.rate_date = d.calendar_date
)

select
    l.currency_code || ':' || cast(l.calendar_date as varchar)        as fx_day_id,
    'USD'                                                             as base_currency_code,
    l.currency_code                                                   as quote_currency_code,
    l.calendar_date                                                   as rate_date,
    fx.rate                                                           as usd_rate,
    l.fixed_on,
    l.fixed_on < l.calendar_date                                      as is_carried_forward
from last_fix as l
inner join fx
    on fx.currency_code = l.currency_code
    and fx.rate_date = l.fixed_on
