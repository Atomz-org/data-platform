with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

daily_store_orders as (

    select
        o.ordered_at as order_date,
        o.location_id,
        l.location_name,
        count(o.order_id) as order_count,
        count(distinct o.customer_id) as unique_customers,
        sum(o.order_total) as total_revenue,
        sum(o.subtotal) as total_subtotal,
        avg(o.order_total) as avg_order_value

    from orders as o

    left join locations as l
        on o.location_id = l.location_id

    group by 1, 2, 3

)

select * from daily_store_orders
