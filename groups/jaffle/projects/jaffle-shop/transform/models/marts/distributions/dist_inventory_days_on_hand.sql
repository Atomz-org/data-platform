with

doh_data as (
    select product_id, location_id, days_on_hand
    from {{ ref('sc_inventory_days_on_hand') }}
),

stats as (
    select
        round(avg(days_on_hand), 2) as mean_doh,
        round(percentile_cont(0.50) within group (order by days_on_hand), 2) as median_doh,
        round(percentile_cont(0.75) within group (order by days_on_hand), 2) as p75_doh,
        round(percentile_cont(0.90) within group (order by days_on_hand), 2) as p90_doh
    from doh_data
),

bucketed as (
    select
        case
            when days_on_hand < 3 then 'critical_(<3d)'
            when days_on_hand < 7 then 'low_(3-7d)'
            when days_on_hand < 14 then 'moderate_(7-14d)'
            when days_on_hand < 30 then 'healthy_(14-30d)'
            else 'excess_(30d+)'
        end as doh_bucket,
        count(*) as item_count
    from doh_data
    group by 1
)

select b.*, s.mean_doh, s.median_doh, s.p75_doh
from bucketed as b cross join stats as s
