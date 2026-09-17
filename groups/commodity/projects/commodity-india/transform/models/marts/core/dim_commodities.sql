-- Grain: one tracked commodity. Duty columns are the schedule in force today.
with commodities as (
    select * from {{ ref('stg_reference__commodities') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
),

market_units as (
    select * from {{ ref('india_market_units') }}
),

current_duties as (
    select *
    from {{ ref('india_import_duties') }}
    where valid_from <= current_date
        and (valid_to is null or valid_to >= current_date)
)

select
    c.commodity_id,
    c.commodity_name,
    c.category,
    c.segment,
    upper(c.exchange)                                   as exchange,
    c.price_basis,
    c.yahoo_symbol,
    c.spot_symbol,
    c.spot_symbol is not null                           as has_spot_feed,
    c.quote_unit,
    u.dimension                                         as unit_dimension,
    mu.market_unit,
    d.tariff_id                                         as current_tariff_id,
    d.effective_duty_rate                               as current_duty_rate,
    d.duty_basis                                        as current_duty_basis,
    coalesce(d.is_import_prohibited, false)             as is_import_prohibited
from commodities as c
left join units as u on u.unit_code = c.quote_unit
left join market_units as mu on mu.commodity_id = c.commodity_id
left join current_duties as d on d.commodity_id = c.commodity_id
