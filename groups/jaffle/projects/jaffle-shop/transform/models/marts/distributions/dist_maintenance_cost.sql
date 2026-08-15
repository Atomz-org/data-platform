with

maint as (
    select maintenance_log_id, maintenance_cost from {{ ref('fct_maintenance_events') }}
    where maintenance_cost > 0
),

stats as (
    select
        round(avg(maintenance_cost), 2) as mean_cost,
        round(percentile_cont(0.50) within group (order by maintenance_cost), 2) as median_cost,
        round(percentile_cont(0.75) within group (order by maintenance_cost), 2) as p75_cost,
        round(percentile_cont(0.90) within group (order by maintenance_cost), 2) as p90_cost
    from maint
),

bucketed as (
    select
        case
            when maintenance_cost < 50 then 'minor_(<50)'
            when maintenance_cost < 200 then 'moderate_(50-200)'
            when maintenance_cost < 500 then 'significant_(200-500)'
            else 'major_(500+)'
        end as cost_bucket,
        count(*) as event_count,
        round(sum(maintenance_cost), 2) as bucket_total
    from maint
    group by 1
)

select b.*, s.mean_cost, s.median_cost, s.p75_cost
from bucketed as b cross join stats as s
