with

daily_orders as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'order_date') }} as month_start,
        location_id,
        location_name,
        sum(order_count) as order_count,
        sum(unique_customers) as unique_customer_visits,
        sum(total_revenue) as total_revenue,
        sum(total_subtotal) as total_subtotal,
        avg(avg_order_value) as avg_daily_order_value,
        count(order_date) as active_days_in_month

    from daily_orders
    group by 1, 2, 3

),

with_growth as (

    select
        *,
        lag(total_revenue) over (
            partition by location_id
            order by month_start
        ) as prev_month_revenue,
        lag(total_revenue, 12) over (
            partition by location_id
            order by month_start
        ) as same_month_last_year_revenue,
        case
            when lag(total_revenue) over (
                partition by location_id order by month_start
            ) > 0
            then (total_revenue - lag(total_revenue) over (
                partition by location_id order by month_start
            )) / lag(total_revenue) over (
                partition by location_id order by month_start
            )
        end as mom_revenue_growth,
        case
            when lag(total_revenue, 12) over (
                partition by location_id order by month_start
            ) > 0
            then (total_revenue - lag(total_revenue, 12) over (
                partition by location_id order by month_start
            )) / lag(total_revenue, 12) over (
                partition by location_id order by month_start
            )
        end as yoy_revenue_growth

    from monthly_agg

)

select * from with_growth
