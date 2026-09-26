{{ config(severity='warn') }}
-- Every commodity in `mcx_products` has at least one futures session. A row
-- here is a job that has never run, or is paused (`src/commodity_india/defs/mcx_jobs.yaml`, or its
-- schedule stopped in Dagster) — warn, because pausing one is allowed.
select distinct p.mcx_commodity
from {{ ref('mcx_products') }} as p
left join {{ ref('int_mcx__futures_sessions') }} as s on s.mcx_commodity = p.mcx_commodity
where s.session_id is null
