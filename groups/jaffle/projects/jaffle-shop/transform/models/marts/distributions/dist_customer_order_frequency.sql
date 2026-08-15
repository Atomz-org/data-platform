with

customers as (
    select customer_id, total_orders from {{ ref('dim_customer_360') }}
    where total_orders > 0
),

bucketed as (
    select
        case
            when total_orders = 1 then '1_order'
            when total_orders between 2 and 3 then '2-3_orders'
            when total_orders between 4 and 6 then '4-6_orders'
            when total_orders between 7 and 10 then '7-10_orders'
            when total_orders between 11 and 20 then '11-20_orders'
            else '20+_orders'
        end as frequency_bucket,
        count(*) as customer_count,
        round(avg(total_orders), 1) as avg_orders_in_bucket
    from customers
    group by 1
),

stats as (
    select
        round(avg(total_orders), 2) as mean_frequency,
        round(percentile_cont(0.50) within group (order by total_orders), 2) as median_frequency,
        round(percentile_cont(0.90) within group (order by total_orders), 2) as p90_frequency
    from customers
)

select b.*, s.mean_frequency, s.median_frequency, s.p90_frequency
from bucketed as b cross join stats as s
