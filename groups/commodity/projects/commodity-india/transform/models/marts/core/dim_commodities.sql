-- Grain: one tracked commodity. The conformed catalog with this market's facts
-- beside it: the unit the local market quotes in and the duty in force today.
with market as (
    select market_code, currency_code
    from {{ ref('markets') }}
    where market_code = '{{ var("market_code") }}'
),

commodities as (
    select * from {{ ref('commodities') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
),

market_units as (
    select * from {{ ref('market_units') }}
),

current_duties as (
    select *
    from {{ ref('import_duties') }}
    where valid_from <= current_date
        and (valid_to is null or valid_to >= current_date)
)

select
    c.commodity_id,
    c.commodity_name,
    c.category,
    c.segment,
    upper(c.exchange)                                   as exchange,
    case when c.yahoo_symbol is not null then 'futures' else 'indicative' end
                                                        as price_basis,
    c.yahoo_symbol,
    c.spot_symbol,
    c.spot_symbol is not null                           as has_spot_feed,
    c.quote_unit,
    u.dimension                                         as unit_dimension,
    m.market_code,
    m.currency_code,
    mu.market_unit,
    d.tariff_id                                         as current_tariff_id,
    d.effective_duty_rate                               as current_duty_rate,
    d.duty_basis                                        as current_duty_basis,
    coalesce(d.is_import_prohibited, false)             as is_import_prohibited
from commodities as c
cross join market as m
left join units as u on u.unit_code = c.quote_unit
left join market_units as mu on mu.commodity_id = c.commodity_id
left join current_duties as d on d.commodity_id = c.commodity_id
