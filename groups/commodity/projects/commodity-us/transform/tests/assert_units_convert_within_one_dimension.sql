-- Repricing troy ounces into barrels is arithmetic, not a conversion. Every
-- quote unit must share a dimension with the market unit it is repriced into.
select c.commodity_id, c.quote_unit, mu.market_unit, q.dimension as quote_dimension,
       m.dimension as market_dimension
from {{ ref('commodities') }} as c
inner join {{ ref('market_units') }} as mu on mu.commodity_id = c.commodity_id
left join {{ ref('units_of_measure') }} as q on q.unit_code = c.quote_unit
left join {{ ref('units_of_measure') }} as m on m.unit_code = mu.market_unit
where q.dimension is null
    or m.dimension is null
    or q.dimension <> m.dimension
