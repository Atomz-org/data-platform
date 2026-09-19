-- Each commodity is priced by exactly its declared basis: futures commodities
-- need a live candle, indicative ones a seed level. A delisted Yahoo contract
-- shows up here rather than as a quiet gap on the board.
{{ config(severity='warn') }}
select d.commodity_id, d.price_basis
from {{ ref('dim_commodities') }} as d
left join {{ ref('int_commodity_prices__usd') }} as p
    on p.commodity_id = d.commodity_id
    and p.price_basis = d.price_basis
group by d.commodity_id, d.price_basis
having count(p.price_id) = 0
