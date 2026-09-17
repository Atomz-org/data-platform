-- Grain: one precious metal per purity grade per price date.
-- Indian retail quote conventions on top of the landed per-gram price:
-- per gram, per 10 grams, per kilogram, by purity (24K/22K/18K, 999/925/900).
with landed as (
    select * from {{ ref('fct_india_landed_prices_daily') }}
    where market_unit = 'g'
        and landed_price_inr is not null
),

purities as (
    select * from {{ ref('precious_metal_purities') }}
),

grams as (
    select base_units_per_unit from {{ ref('units_of_measure') }} where unit_code = 'g'
),

kilograms as (
    select base_units_per_unit from {{ ref('units_of_measure') }} where unit_code = 'kg'
),

graded as (
    select
        l.commodity_id,
        p.purity_code,
        p.purity_label,
        p.fineness,
        l.price_date,
        l.price_basis,
        l.is_duty_rate_confirmed,
        l.landed_price_inr * p.fineness                                     as inr_per_gram
    from landed as l
    inner join purities as p on p.commodity_id = l.commodity_id
)

select
    g.commodity_id || ':' || g.purity_code || ':' || cast(g.price_date as varchar) as retail_price_id,
    g.commodity_id,
    g.purity_code,
    g.purity_label,
    g.fineness,
    g.price_date,
    g.price_basis,
    g.is_duty_rate_confirmed,
    cast(round(g.inr_per_gram, 4) as decimal(18, 4))                        as price_inr_per_gram,
    cast(round(g.inr_per_gram * 10, 4) as decimal(18, 4))                   as price_inr_per_10g,
    cast(round({{ reprice_per_unit('g.inr_per_gram', 'gm.base_units_per_unit', 'kgm.base_units_per_unit') }}, 4)
        as decimal(18, 4))                                                  as price_inr_per_kg
from graded as g
cross join grams as gm
cross join kilograms as kgm
