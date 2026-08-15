with

daily_product as (

    select * from {{ ref('int_daily_orders_by_product') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'order_date') }} as month_start,
        product_id,
        product_name,
        product_type,
        sum(units_sold) as units_sold,
        sum(order_count) as order_count,
        sum(daily_revenue) as monthly_revenue,
        avg(units_sold) as avg_daily_units,
        count(order_date) as active_days_in_month

    from daily_product
    group by 1, 2, 3, 4

),

with_growth as (

    select
        *,
        lag(monthly_revenue) over (
            partition by product_id
            order by month_start
        ) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (
                partition by product_id order by month_start
            ) > 0
            then (monthly_revenue - lag(monthly_revenue) over (
                partition by product_id order by month_start
            )) / lag(monthly_revenue) over (
                partition by product_id order by month_start
            )
        end as mom_revenue_growth

    from monthly_agg

)

select * from with_growth
