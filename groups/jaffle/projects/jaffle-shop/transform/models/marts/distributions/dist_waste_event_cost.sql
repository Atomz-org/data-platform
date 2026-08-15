with

waste as (
    select waste_log_id, cost_of_waste from {{ ref('fct_waste_events') }}
    where cost_of_waste > 0
),

stats as (
    select
        count(*) as total_events,
        round(avg(cost_of_waste), 2) as mean_cost,
        round(percentile_cont(0.50) within group (order by cost_of_waste), 2) as median_cost,
        round(percentile_cont(0.75) within group (order by cost_of_waste), 2) as p75_cost,
        round(percentile_cont(0.90) within group (order by cost_of_waste), 2) as p90_cost,
        round(percentile_cont(0.95) within group (order by cost_of_waste), 2) as p95_cost,
        sum(cost_of_waste) as total_cost_of_waste
    from waste
),

bucketed as (
    select
        case
            when cost_of_waste < 5 then '0-5'
            when cost_of_waste < 15 then '5-15'
            when cost_of_waste < 30 then '15-30'
            when cost_of_waste < 50 then '30-50'
            else '50+'
        end as cost_bucket,
        count(*) as event_count,
        round(sum(cost_of_waste), 2) as bucket_total
    from waste
    group by 1
)

select b.*, s.mean_cost, s.median_cost, s.p90_cost, s.total_events
from bucketed as b cross join stats as s
