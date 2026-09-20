-- Grain: one commodity per price date with a USD fix for this market's currency.
--
-- The conformed landed price every sister in this family produces, in the same
-- shape, so the roll-up can line markets up without a per-market mapping:
--     landed (local) per market unit = benchmark USD per market unit × USD/local × (1 + duty)
--
-- Which market this is comes from `var('market_code')` and the group's `markets`
-- seed, never from a literal in this file. A market whose currency is USD has a
-- rate of 1 and no fix to wait for. The benchmark stands in for the assessable
-- (CIF) value: freight, insurance, landing charges and local taxes are excluded,
-- exactly as in the source methodology. A commodity this market prohibits
-- importing keeps its row with no landed price.
with market as (
    select market_code, currency_code
    from {{ ref('markets') }}
    where market_code = '{{ var("market_code") }}'
),

prices as (
    select * from {{ ref('int_commodity_prices__usd') }}
),

fx as (
    select rate_date, usd_rate, fixed_on, quote_currency_code
    from {{ ref('int_fx_rates__daily') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
),

market_units as (
    select * from {{ ref('market_units') }}
),

duties as (
    select * from {{ ref('import_duties') }}
),

priced as (
    select
        p.price_id,
        m.market_code,
        p.commodity_id,
        p.price_date,
        p.price_basis,
        p.quote_unit,
        mu.market_unit,
        m.currency_code,
        p.close_price                                                       as benchmark_price_usd,
        {{ reprice_per_unit('p.close_price', 'qu.base_units_per_unit', 'mku.base_units_per_unit') }}
                                                                            as benchmark_usd_per_market_unit,
        case when m.currency_code = 'USD' then 1.0 else fx.usd_rate end     as usd_fx_rate,
        case when m.currency_code = 'USD' then p.price_date else fx.fixed_on end
                                                                            as fx_fixed_on,
        d.tariff_id,
        d.duty_basis,
        coalesce(d.is_import_prohibited, false)                             as is_import_prohibited,
        d.effective_duty_rate,
        d.confirmed_from is not null and p.price_date >= d.confirmed_from  as is_duty_rate_confirmed
    from prices as p
    cross join market as m
    inner join market_units as mu on mu.commodity_id = p.commodity_id
    inner join units as qu on qu.unit_code = p.quote_unit
    inner join units as mku on mku.unit_code = mu.market_unit
    left join fx
        on fx.rate_date = p.price_date
        and fx.quote_currency_code = m.currency_code
    left join duties as d
        on d.commodity_id = p.commodity_id
        and p.price_date >= d.valid_from
        and (d.valid_to is null or p.price_date <= d.valid_to)
    where m.currency_code = 'USD' or fx.usd_rate is not null
),

landed as (
    select
        *,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_fx_rate
        end                                                                 as assessable_local,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_fx_rate * effective_duty_rate
        end                                                                 as duty_local_raw,
        case when not is_import_prohibited
            then benchmark_usd_per_market_unit * usd_fx_rate * (1 + effective_duty_rate)
        end                                                                 as landed_local_raw
    from priced
),

changes as (
    select
        *,
        lag(landed_local_raw) over (partition by commodity_id order by price_date) as prev_landed_local
    from landed
)

select
    price_id,
    market_code,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    market_unit,
    currency_code,
    benchmark_price_usd,
    benchmark_usd_per_market_unit,
    usd_fx_rate,
    fx_fixed_on,
    tariff_id,
    duty_basis,
    is_import_prohibited,
    effective_duty_rate,
    is_duty_rate_confirmed,
    cast(round(assessable_local, 4) as decimal(18, 4))                          as assessable_value_local,
    cast(round(duty_local_raw, 4) as decimal(18, 4))                            as duty_local,
    cast(round(landed_local_raw, 4) as decimal(18, 4))                          as landed_price_local,
    cast(round(landed_local_raw - prev_landed_local, 4) as decimal(18, 4))      as landed_price_change_local,
    {{ sf_safe_divide('landed_local_raw - prev_landed_local', 'prev_landed_local') }} as landed_price_change_pct
from changes
