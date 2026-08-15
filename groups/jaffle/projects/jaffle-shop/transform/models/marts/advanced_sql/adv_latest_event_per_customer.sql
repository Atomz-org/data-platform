-- adv_latest_event_per_customer.sql
-- Technique: ROW_NUMBER() window function (cross-database compatible)
-- For each customer, retrieves their last 5 orders with full details.

with customers as (

    select * from {{ ref('stg_customers') }}

),

orders as (

    select * from {{ ref('orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

-- Rank orders per customer by recency
ranked_orders as (

    select
        o.customer_id,
        o.order_id,
        o.ordered_at,
        o.order_total,
        o.count_order_items,
        o.is_food_order,
        o.is_drink_order,
        o.location_id,
        row_number() over (partition by o.customer_id order by o.ordered_at desc) as recency_rank
    from orders as o

),

latest_orders as (

    select
        c.customer_id,
        c.customer_name,
        ro.order_id,
        ro.ordered_at,
        ro.order_total,
        ro.count_order_items,
        ro.is_food_order,
        ro.is_drink_order,
        ro.location_id,
        l.location_name,
        ro.recency_rank
    from customers as c
    inner join ranked_orders as ro
        on c.customer_id = ro.customer_id
    left join locations as l
        on ro.location_id = l.location_id
    where ro.recency_rank <= 5

)

select * from latest_orders
order by customer_id, recency_rank
