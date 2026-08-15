with

daily_orders as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'order_date') }} as week_start,
        location_id,
        location_name,
        sum(order_count) as order_count,
        sum(unique_customers) as unique_customer_visits,
        sum(total_revenue) as total_revenue,
        sum(total_subtotal) as total_subtotal,
        avg(avg_order_value) as avg_daily_order_value,
        count(order_date) as active_days_in_week

    from daily_orders
    group by 1, 2, 3

)

select * from weekly_agg
