-- Grain: one commodity per price date with a USD/INR fix.
--
-- India import landed price, the tracker's formula:
--     landed ₹ per market unit = benchmark USD per market unit × USD/INR × (1 + duty)
--
-- The benchmark stands in for the assessable (CIF) value: freight, insurance,
-- landing charges and GST are excluded, exactly as in the source methodology.
-- A commodity India prohibits importing keeps its row with no landed price.
with prices as (
    select * from {{ ref('int_commodity_prices__usd') }}
),

usd_inr as (
    select rate_date, usd_rate, fixed_on
    from {{ ref('int_fx_rates__daily') }}
    where quote_currency_code = 'INR'
),

units as (
    select * from {{ ref('units_of_measure') }}
),

market_units as (
    select * from {{ ref('india_market_units') }}
),

duties as (
    select * from {{ ref('india_import_duties') }}
),

priced as (
    select
        p.price_id,
        p.commodity_id,
        p.price_date,
        p.price_basis,
        p.quote_unit,
        mu.market_unit,
        p.close_price                                                       as benchmark_price_usd,
        {{ reprice_per_unit('p.close_price', 'qu.base_units_per_unit', 'mku.base_units_per_unit') }}
                                                                            as benchmark_usd_per_market_unit,
        fx.usd_rate                                                         as usd_inr_rate,
        fx.fixed_on                                                         as usd_inr_fixed_on,
        d.tariff_id,
        d.duty_basis,
        coalesce(d.is_import_prohibited, false)                             as is_import_prohibited,
        d.effective_duty_rate,
        d.confirmed_from is not null and p.price_date >= d.confirmed_from  as is_duty_rate_confirmed
    from prices as p
    inner join market_units as mu on mu.commodity_id = p.commodity_id
    inner join units as qu on qu.unit_code = p.quote_unit
    inner join units as mku on mku.unit_code = mu.market_unit
    inner join usd_inr as fx on fx.rate_date = p.price_date
    left join duties as d
        on d.commodity_id = p.commodity_id
        and p.price_date >= d.valid_from
        and (d.valid_to is null or p.price_date <= d.valid_to)
),

landed as (
    select
        *,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_inr_rate
        end                                                                 as assessable_inr,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_inr_rate * effective_duty_rate
        end                                                                 as duty_inr,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_inr_rate * (1 + effective_duty_rate)
        end                                                                 as landed_inr
    from priced
),

changes as (
    select
        *,
        lag(landed_inr) over (partition by commodity_id order by price_date) as prev_landed_inr
    from landed
)

select
    price_id,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    market_unit,
    benchmark_price_usd,
    benchmark_usd_per_market_unit,
    usd_inr_rate,
    usd_inr_fixed_on,
    tariff_id,
    duty_basis,
    is_import_prohibited,
    effective_duty_rate,
    is_duty_rate_confirmed,
    cast(round(assessable_inr, 4) as decimal(18, 4))                        as assessable_value_inr,
    cast(round(duty_inr, 4) as decimal(18, 4))                              as duty_inr,
    cast(round(landed_inr, 4) as decimal(18, 4))                            as landed_price_inr,
    cast(round(landed_inr - prev_landed_inr, 4) as decimal(18, 4))          as landed_price_change_inr,
    {{ sf_safe_divide('landed_inr - prev_landed_inr', 'prev_landed_inr') }} as landed_price_change_pct
from changes
