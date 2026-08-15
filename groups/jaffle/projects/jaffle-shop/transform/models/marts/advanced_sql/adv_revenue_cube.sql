-- adv_revenue_cube.sql
-- Technique: GROUPING SETS
-- Multi-dimensional revenue analysis across store, product, and month using GROUPING SETS.
-- The grouping() function identifies which aggregation level each row represents.

with

l as (
    select * from {{ ref('stg_locations') }}
),


product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

sales_with_location as (

    select
        ps.sale_date,
        {{ dbt.date_trunc('month', 'ps.sale_date') }} as sale_month,
        ps.product_id,
        ps.product_name,
        l.location_id,
        l.location_name,
        ps.daily_revenue
    from product_sales as ps
    -- Join via orders to get location context
    cross join l
    -- Since fct_product_sales doesn't have location_id directly,
    -- we use int_daily_orders_by_store for the store-level breakdowns
),

-- Use int_daily_orders_by_store for store-level data and stg_order_items for product-level
order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

store_product_month as (

    select
        o.location_id,
        l.location_name,
        oi.product_id,
        p.product_name,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as sale_month,
        sum(p.product_price) as total_revenue,
        count(distinct o.order_id) as order_count
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    inner join products as p on oi.product_id = p.product_id
    inner join l on o.location_id = l.location_id
    group by 1, 2, 3, 4, 5

),

-- GROUPING SETS: produce subtotals at every useful combination
revenue_cube as (

    select
        location_id,
        location_name,
        product_id,
        product_name,
        sale_month,
        sum(total_revenue) as total_revenue,
        sum(order_count) as total_orders,

        -- grouping() returns 0 if column is in the current grouping, 1 if aggregated away
        grouping(location_id) as is_location_aggregated,
        grouping(product_id) as is_product_aggregated,
        grouping(sale_month) as is_month_aggregated,

        -- Human-readable aggregation level
        case
            when grouping(location_id) = 0 and grouping(product_id) = 0 and grouping(sale_month) = 0
                then 'store_product_month'
            when grouping(location_id) = 0 and grouping(product_id) = 1 and grouping(sale_month) = 0
                then 'store_month'
            when grouping(location_id) = 1 and grouping(product_id) = 0 and grouping(sale_month) = 0
                then 'product_month'
            when grouping(location_id) = 0 and grouping(product_id) = 1 and grouping(sale_month) = 1
                then 'store_total'
            when grouping(location_id) = 1 and grouping(product_id) = 0 and grouping(sale_month) = 1
                then 'product_total'
            when grouping(location_id) = 1 and grouping(product_id) = 1 and grouping(sale_month) = 1
                then 'grand_total'
            else 'other'
        end as aggregation_level

    from store_product_month

    group by grouping sets (
        (location_id, location_name, product_id, product_name, sale_month),  -- full detail
        (location_id, location_name, sale_month),                             -- by store + month
        (product_id, product_name, sale_month),                               -- by product + month
        (location_id, location_name),                                         -- by store total
        (product_id, product_name),                                           -- by product total
        ()                                                                     -- grand total
    )

)

select * from revenue_cube
order by is_location_aggregated, is_product_aggregated, is_month_aggregated, sale_month
