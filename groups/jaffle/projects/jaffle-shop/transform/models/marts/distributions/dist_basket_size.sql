with

o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

baskets as (
    select o.order_id, count(oi.order_item_id) as item_count
    from o
    inner join oi on o.order_id = oi.order_id
    group by 1
),

stats as (
    select
        round(avg(item_count), 2) as mean_basket,
        round(percentile_cont(0.50) within group (order by item_count), 2) as median_basket,
        round(percentile_cont(0.75) within group (order by item_count), 2) as p75_basket,
        round(percentile_cont(0.90) within group (order by item_count), 2) as p90_basket,
        max(item_count) as max_basket
    from baskets
),

bucketed as (
    select
        item_count as basket_size,
        count(*) as order_count
    from baskets
    group by 1
)

select b.*, s.mean_basket, s.median_basket, s.p75_basket, s.p90_basket
from bucketed as b cross join stats as s
