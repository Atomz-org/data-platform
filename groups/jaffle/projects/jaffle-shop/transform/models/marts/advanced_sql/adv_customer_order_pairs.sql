-- adv_customer_order_pairs.sql
-- Technique: Self-join on consecutive orders using LAG window function
-- Pairs each customer order with their immediately previous order to analyze
-- behavioral changes: time between orders, spending changes, and whether the
-- customer switched stores. This pattern is essential for understanding
-- customer journey progression and retention signals.

with orders as (

    select * from {{ ref('orders') }}

),

order_items as (

    select * from {{ ref('order_items') }}

),

-- Deduplicate products per order (needed for Snowflake which does not support
-- DISTINCT inside array_agg with WITHIN GROUP)
order_products_deduped as (

    select distinct
        order_id,
        product_id
    from order_items

),

-- Get distinct product set per order for mix-change detection
order_product_sets as (

    select
        order_id,
        {% if target.type == 'snowflake' %}
        array_agg(product_id) within group (order by product_id) as product_ids
        {% else %}
        array_agg(product_id order by product_id) as product_ids
        {% endif %}
    from order_products_deduped
    group by 1

),

-- Use LAG to pair each order with the customer's previous order
order_pairs as (

    select
        o.order_id,
        o.customer_id,
        o.location_id,
        o.ordered_at,
        o.order_total,
        o.count_order_items,
        o.customer_order_number,
        ops.product_ids,

        -- Previous order fields via LAG
        lag(o.order_id) over (
            partition by o.customer_id
            order by o.ordered_at, o.order_id
        ) as prev_order_id,

        lag(o.location_id) over (
            partition by o.customer_id
            order by o.ordered_at, o.order_id
        ) as prev_location_id,

        lag(o.ordered_at) over (
            partition by o.customer_id
            order by o.ordered_at, o.order_id
        ) as prev_ordered_at,

        lag(o.order_total) over (
            partition by o.customer_id
            order by o.ordered_at, o.order_id
        ) as prev_order_total,

        lag(o.count_order_items) over (
            partition by o.customer_id
            order by o.ordered_at, o.order_id
        ) as prev_count_order_items

    from orders as o
    left join order_product_sets as ops
        on o.order_id = ops.order_id

),

-- Get previous order's product set for comparison
prev_product_sets as (

    select
        op.*,
        lag_ops.product_ids as prev_product_ids
    from order_pairs as op
    left join order_product_sets as lag_ops
        on op.prev_order_id = lag_ops.order_id

),

-- Calculate derived metrics for each order pair
final as (

    select
        order_id,
        customer_id,
        customer_order_number,
        ordered_at,
        order_total,
        count_order_items,
        location_id,

        prev_order_id,
        prev_ordered_at,
        prev_order_total,
        prev_count_order_items,
        prev_location_id,

        -- Days between consecutive orders
        case
            when prev_ordered_at is not null
            then {{ dbt.datediff('prev_ordered_at', 'ordered_at', 'day') }}
            else null
        end as days_between_orders,

        -- Order total change percentage
        case
            when prev_order_total is not null and prev_order_total > 0
            then round(
                ((order_total - prev_order_total) / prev_order_total * 100), 1
            )
            else null
        end as amount_change_pct,

        -- Did the customer switch stores?
        case
            when prev_location_id is not null
                and location_id != prev_location_id
            then true
            else false
        end as did_store_change,

        -- Did the product mix change?
        case
            when prev_product_ids is not null
                and product_ids is not null
                and product_ids != prev_product_ids
            then true
            when prev_product_ids is null then null
            else false
        end as did_product_mix_change

    from prev_product_sets

    -- Exclude the first order per customer (no previous order to pair with)
    where prev_order_id is not null

)

select * from final
order by customer_id, ordered_at
