with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

weekly_metrics as (

    select
        {{ dbt.date_trunc('week', 'o.ordered_at') }} as week_start,
        o.location_id,
        l.location_name,
        count(o.order_id) as order_count,
        count(distinct o.customer_id) as unique_customers,
        sum(o.order_total) as total_revenue,
        sum(o.subtotal) as total_subtotal,
        sum(o.tax_paid) as total_tax,
        avg(o.order_total) as avg_ticket_size,
        min(o.order_total) as min_order_value,
        max(o.order_total) as max_order_value

    from orders as o

    left join locations as l
        on o.location_id = l.location_id

    group by 1, 2, 3

)

select * from weekly_metrics
