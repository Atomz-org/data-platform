with

deliveries as (
    select shipment_id, actual_transit_days from {{ ref('fct_deliveries') }}
),

stats as (
    select
        round(avg(actual_transit_days), 2) as mean_lead_time,
        round(percentile_cont(0.50) within group (order by actual_transit_days), 2) as median_lead_time,
        round(percentile_cont(0.75) within group (order by actual_transit_days), 2) as p75_lead_time,
        round(percentile_cont(0.90) within group (order by actual_transit_days), 2) as p90_lead_time,
        round(percentile_cont(0.95) within group (order by actual_transit_days), 2) as p95_lead_time
    from deliveries
),

bucketed as (
    select
        case
            when actual_transit_days <= 1 then 'next_day'
            when actual_transit_days <= 3 then '2-3_days'
            when actual_transit_days <= 5 then '4-5_days'
            when actual_transit_days <= 7 then '6-7_days'
            else '7+_days'
        end as lead_time_bucket,
        count(*) as delivery_count
    from deliveries
    group by 1
)

select b.*, s.mean_lead_time, s.median_lead_time, s.p90_lead_time
from bucketed as b cross join stats as s
