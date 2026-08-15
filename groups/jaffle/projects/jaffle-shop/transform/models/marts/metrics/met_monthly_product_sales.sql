with

daily as (

    select * from {{ ref('met_daily_product_sales') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'sale_date') }} as month_start,
        product_id,
        product_name,
        product_type,
        sum(units_sold) as monthly_units,
        sum(order_count) as monthly_orders,
        sum(daily_revenue) as monthly_revenue,
        sum(daily_margin) as monthly_margin,
        case
            when sum(daily_revenue) > 0
            then sum(daily_margin) * 100.0 / sum(daily_revenue)
            else 0
        end as margin_pct

    from daily
    group by 1, 2, 3, 4

),

with_growth as (

    select
        *,
        lag(monthly_revenue) over (
            partition by product_id order by month_start
        ) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (
                partition by product_id order by month_start
            ) > 0
            then (monthly_revenue - lag(monthly_revenue) over (
                partition by product_id order by month_start
            )) * 1.0 / lag(monthly_revenue) over (
                partition by product_id order by month_start
            )
        end as mom_revenue_growth

    from monthly_agg

)

select * from with_growth
