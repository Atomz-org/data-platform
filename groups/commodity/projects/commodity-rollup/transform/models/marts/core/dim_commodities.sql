-- Grain: one tracked commodity. The group catalog as every market sees it; a
-- market's own unit and duty are that market's business and live in her marts.
with commodities as (
    select * from {{ ref('commodities') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
),

markets_pricing as (
    select commodity_id, count(distinct market_code) as markets_pricing
    from {{ ref('stg_sisters__landed_prices') }}
    group by commodity_id
)

select
    c.commodity_id,
    c.commodity_name,
    c.category,
    c.segment,
    upper(c.exchange)                                       as exchange,
    case when c.yahoo_symbol is not null then 'futures' else 'indicative' end
                                                            as price_basis,
    c.quote_unit,
    u.dimension                                             as unit_dimension,
    coalesce(mp.markets_pricing, 0)                         as markets_pricing
from commodities as c
left join units as u on u.unit_code = c.quote_unit
left join markets_pricing as mp on mp.commodity_id = c.commodity_id
