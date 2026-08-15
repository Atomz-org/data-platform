-- adv_conditional_aggregates.sql
-- Technique: FILTER clause (PostgreSQL-specific)
-- The FILTER clause is a cleaner alternative to CASE WHEN inside aggregate functions.
-- It makes conditional aggregation more readable and is a PostgreSQL extension to SQL.

with orders as (

    select * from {{ ref('orders') }}

),

customers as (

    select * from {{ ref('customers') }}

),

order_enriched as (

    select
        o.*,
        c.customer_type,
        c.customer_type = 'returning' as is_repeat_buyer
    from orders as o
    inner join customers as c
        on o.customer_id = c.customer_id

),

-- FILTER clause: each aggregate only considers rows matching the condition
conditional_aggs as (

    select
        location_id,

        -- Total counts
        count(*) as total_orders,
        count(distinct customer_id) as unique_customers,
        sum(order_total) as total_revenue,

        -- Order type breakdown using FILTER
        count(case when is_food_order then 1 end) as food_orders,
        count(case when is_drink_order then 1 end) as drink_orders,
        count(case when is_food_order and is_drink_order then 1 end) as combo_orders,
        count(case when not is_food_order and not is_drink_order then 1 end) as other_orders,

        -- Revenue by customer segment using FILTER
        sum(case when customer_order_number = 1 then order_total end) as first_order_revenue,
        sum(case when customer_order_number > 1 then order_total end) as repeat_order_revenue,

        -- Average order value by segment using FILTER
        avg(case when is_repeat_buyer then order_total end) as repeat_customer_aov,
        avg(case when not is_repeat_buyer then order_total end) as new_customer_aov,

        -- Large order analysis using FILTER
        count(case when order_total > 20 then 1 end) as large_orders,
        avg(case when order_total > 20 then order_total end) as large_order_avg,

        -- Item count analysis using FILTER
        avg(case when is_food_order then count_order_items end) as avg_items_food_orders,
        avg(case when is_drink_order then count_order_items end) as avg_items_drink_orders

    from order_enriched
    group by 1

)

select * from conditional_aggs
order by location_id
