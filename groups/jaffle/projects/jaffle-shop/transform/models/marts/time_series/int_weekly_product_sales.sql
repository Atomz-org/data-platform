with

daily_product as (

    select * from {{ ref('int_daily_orders_by_product') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'order_date') }} as week_start,
        product_id,
        product_name,
        product_type,
        sum(units_sold) as units_sold,
        sum(order_count) as order_count,
        sum(daily_revenue) as weekly_revenue,
        avg(units_sold) as avg_daily_units,
        count(order_date) as active_days_in_week

    from daily_product
    group by 1, 2, 3, 4

)

select * from weekly_agg
