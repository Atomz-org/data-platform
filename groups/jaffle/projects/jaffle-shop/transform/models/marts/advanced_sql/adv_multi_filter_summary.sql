-- adv_multi_filter_summary.sql
-- Technique: FILTER clause — Complex multi-domain aggregation
-- Combines multiple FILTER conditions across different business domains in a single
-- scan of the orders table. This avoids multiple passes and subqueries.

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
        c.customer_type = 'returning' as is_repeat_buyer,
        c.lifetime_spend,
        {{ day_of_week_number('o.ordered_at') }} as day_of_week,
        extract(hour from o.ordered_at) as order_hour,
        extract(month from o.ordered_at) as order_month
    from orders as o
    inner join customers as c
        on o.customer_id = c.customer_id

),

-- Multi-dimensional summary using FILTER across time, customer, and product domains
multi_filter_summary as (

    select
        location_id,

        -- Time-based filters
        count(case when day_of_week in (0, 6) then 1 end) as weekend_orders,
        count(case when day_of_week between 1 and 5 then 1 end) as weekday_orders,
        sum(case when day_of_week in (0, 6) then order_total end) as weekend_revenue,
        sum(case when day_of_week between 1 and 5 then order_total end) as weekday_revenue,

        -- Seasonal filters (Q1-Q4)
        sum(case when order_month between 1 and 3 then order_total end) as q1_revenue,
        sum(case when order_month between 4 and 6 then order_total end) as q2_revenue,
        sum(case when order_month between 7 and 9 then order_total end) as q3_revenue,
        sum(case when order_month between 10 and 12 then order_total end) as q4_revenue,

        -- Customer value tier filters
        count(distinct case when lifetime_spend > 100 then customer_id end) as high_value_customers,
        count(distinct case when lifetime_spend between 50 and 100 then customer_id end) as mid_value_customers,
        count(distinct case when lifetime_spend < 50 then customer_id end) as low_value_customers,

        -- Cross-domain: high-value repeat customers ordering combos on weekends
        count(case when is_repeat_buyer
              and is_food_order
              and is_drink_order
              and day_of_week in (0, 6) then 1 end) as weekend_combo_repeat_orders,

        -- Revenue from first-time customers who ordered food
        sum(case when customer_order_number = 1 and is_food_order then order_total end) as first_time_food_revenue,

        -- Average basket size for returning drink-only orders
        avg(case when is_drink_order and not is_food_order and customer_order_number > 1 then count_order_items end) as avg_items_repeat_drink_only

    from order_enriched
    group by 1

)

select * from multi_filter_summary
order by location_id
