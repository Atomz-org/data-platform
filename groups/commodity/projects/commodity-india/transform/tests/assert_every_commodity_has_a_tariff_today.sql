-- A commodity with no tariff in force silently drops out of the landed-price
-- mart. A new catalog entry must come with a duty row (or an explicit
-- prohibition) in india_import_duties.
select commodity_id
from {{ ref('dim_commodities') }}
where current_tariff_id is null
