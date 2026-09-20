-- An indicative level in a different unit from the catalog would be repriced
-- with the wrong factor in every sister.
select i.commodity_id, i.quote_unit, c.quote_unit as catalog_quote_unit
from {{ ref('indicative_prices') }} as i
inner join {{ ref('commodities') }} as c on c.commodity_id = i.commodity_id
where i.quote_unit <> c.quote_unit
