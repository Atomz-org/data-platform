-- A market in the group registry whose sister has landed nothing here is a
-- roll-up that silently omits a country. Seed the sister, or remove the row.
select market_code, market_name, project
from {{ ref('dim_markets') }}
where not is_reporting
