with

orders as (
    select order_id, order_total from {{ ref('stg_orders') }}
    where order_total > 0
),

stats as (
    select
        count(*) as total_orders,
        round(avg(order_total), 2) as mean_value,
        round(min(order_total), 2) as min_value,
        round(max(order_total), 2) as max_value,
        round(percentile_cont(0.25) within group (order by order_total), 2) as p25,
        round(percentile_cont(0.50) within group (order by order_total), 2) as p50_median,
        round(percentile_cont(0.75) within group (order by order_total), 2) as p75,
        round(percentile_cont(0.90) within group (order by order_total), 2) as p90,
        round(percentile_cont(0.95) within group (order by order_total), 2) as p95,
        round(percentile_cont(0.99) within group (order by order_total), 2) as p99
    from orders
),

bucketed as (
    select
        case
            when order_total < 10 then '0-10'
            when order_total < 20 then '10-20'
            when order_total < 30 then '20-30'
            when order_total < 50 then '30-50'
            when order_total < 75 then '50-75'
            when order_total < 100 then '75-100'
            else '100+'
        end as value_bucket,
        count(*) as order_count,
        round(avg(order_total), 2) as bucket_avg
    from orders
    group by 1
)

select b.*, s.mean_value, s.p50_median, s.p25, s.p75, s.p90, s.p95, s.total_orders
from bucketed as b
cross join stats as s
