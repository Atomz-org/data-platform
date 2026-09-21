-- A lot in tonnes priced from a per-gram landed price is only meaningful when
-- both units measure mass. Every MCX quote and lot unit must share a dimension
-- with the commodity's Indian market unit.
select l.contract_code, mu.market_unit, l.quote_unit, l.lot_unit
from {{ ref('mcx_contract_lots') }} as l
inner join {{ ref('market_units') }} as mu on mu.commodity_id = l.commodity_id
left join {{ ref('units_of_measure') }} as m on m.unit_code = mu.market_unit
left join {{ ref('units_of_measure') }} as q on q.unit_code = l.quote_unit
left join {{ ref('units_of_measure') }} as t on t.unit_code = l.lot_unit
where m.dimension is null
    or q.dimension is distinct from m.dimension
    or t.dimension is distinct from m.dimension
