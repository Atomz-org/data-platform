with

weekly_revenue as (

    select
        {{ dbt.date_trunc('week', 'revenue_date') }} as week_start,
        sum(total_revenue) as weekly_revenue,
        sum(order_count) as weekly_orders
    from {{ ref('met_daily_revenue_by_store') }}
    group by 1

),

weekly_with_wow as (

    select
        week_start,
        weekly_revenue,
        weekly_orders,
        lag(weekly_revenue) over (order by week_start) as prev_week_revenue,
        lag(weekly_orders) over (order by week_start) as prev_week_orders,
        case
            when lag(weekly_revenue) over (order by week_start) > 0
                then round(cast(
                    (weekly_revenue - lag(weekly_revenue) over (order by week_start)) * 100.0
                    / lag(weekly_revenue) over (order by week_start)
                as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_wow_pct,
        case
            when lag(weekly_orders) over (order by week_start) > 0
                then round(cast(
                    (weekly_orders - lag(weekly_orders) over (order by week_start)) * 100.0
                    / lag(weekly_orders) over (order by week_start)
                as {{ dbt.type_float() }}), 2)
            else null
        end as orders_wow_pct,
        case
            when weekly_orders > 0
                then round(cast(weekly_revenue / weekly_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_order_value
    from weekly_revenue

)

select * from weekly_with_wow
