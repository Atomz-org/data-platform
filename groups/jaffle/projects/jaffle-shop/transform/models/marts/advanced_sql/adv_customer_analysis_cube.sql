-- adv_customer_analysis_cube.sql
-- Technique: CUBE
-- All possible aggregation combinations of customer_type, location_id, and order_year
-- using CUBE. This produces 2^3 = 8 combinations including grand total, enabling
-- slice-and-dice analysis without multiple queries.

with orders as (

    select * from {{ ref('orders') }}

),

customers as (

    select * from {{ ref('customers') }}

),

order_enriched as (

    select
        o.order_id,
        o.customer_id,
        c.customer_type,
        o.location_id,
        extract(year from o.ordered_at) as order_year,
        o.order_total,
        o.is_food_order,
        o.is_drink_order,
        o.count_order_items
    from orders as o
    inner join customers as c
        on o.customer_id = c.customer_id

),

customer_cube as (

    select
        customer_type,
        location_id,
        order_year,

        count(order_id) as total_orders,
        count(distinct customer_id) as unique_customers,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        sum(count_order_items) as total_items_sold,

        -- Identify which dimensions are aggregated
        grouping(customer_type) as is_type_aggregated,
        grouping(location_id) as is_location_aggregated,
        grouping(order_year) as is_year_aggregated,

        -- Descriptive level name for all 8 combinations
        case
            when grouping(customer_type) = 0 and grouping(location_id) = 0 and grouping(order_year) = 0
                then 'type_location_year'
            when grouping(customer_type) = 0 and grouping(location_id) = 0 and grouping(order_year) = 1
                then 'type_location'
            when grouping(customer_type) = 0 and grouping(location_id) = 1 and grouping(order_year) = 0
                then 'type_year'
            when grouping(customer_type) = 1 and grouping(location_id) = 0 and grouping(order_year) = 0
                then 'location_year'
            when grouping(customer_type) = 0 and grouping(location_id) = 1 and grouping(order_year) = 1
                then 'type_only'
            when grouping(customer_type) = 1 and grouping(location_id) = 0 and grouping(order_year) = 1
                then 'location_only'
            when grouping(customer_type) = 1 and grouping(location_id) = 1 and grouping(order_year) = 0
                then 'year_only'
            else 'grand_total'
        end as cube_level

    from order_enriched

    group by cube (customer_type, location_id, order_year)

)

select * from customer_cube
order by is_type_aggregated, is_location_aggregated, is_year_aggregated, order_year
