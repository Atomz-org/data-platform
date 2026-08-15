with

daily as (

    select * from {{ ref('met_daily_product_sales') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'sale_date') }} as week_start,
        product_id,
        product_name,
        product_type,
        sum(units_sold) as weekly_units,
        sum(order_count) as weekly_orders,
        sum(daily_revenue) as weekly_revenue,
        sum(daily_margin) as weekly_margin,
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
        lag(weekly_revenue) over (
            partition by product_id order by week_start
        ) as prev_week_revenue,
        case
            when lag(weekly_revenue) over (
                partition by product_id order by week_start
            ) > 0
            then (weekly_revenue - lag(weekly_revenue) over (
                partition by product_id order by week_start
            )) * 1.0 / lag(weekly_revenue) over (
                partition by product_id order by week_start
            )
        end as wow_revenue_growth

    from weekly_agg

)

select * from with_growth
