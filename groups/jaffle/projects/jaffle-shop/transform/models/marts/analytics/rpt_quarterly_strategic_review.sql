with

monthly_revenue as (

    select
        month_start,
        sum(monthly_revenue) as monthly_revenue,
        sum(monthly_orders) as monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1

),

quarterly as (

    select
        {{ dbt.date_trunc('quarter', 'month_start') }} as quarter_start,
        sum(monthly_revenue) as quarterly_revenue,
        sum(monthly_orders) as quarterly_orders,
        avg(monthly_revenue) as avg_monthly_revenue
    from monthly_revenue
    group by 1

),

with_yoy as (

    select
        quarter_start,
        quarterly_revenue,
        quarterly_orders,
        avg_monthly_revenue,
        lag(quarterly_revenue, 4) over (order by quarter_start) as quarterly_revenue_last_year,
        case
            when lag(quarterly_revenue, 4) over (order by quarter_start) > 0
                then round(cast(
                    (quarterly_revenue - lag(quarterly_revenue, 4) over (order by quarter_start)) * 100.0
                    / lag(quarterly_revenue, 4) over (order by quarter_start)
                as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_yoy_pct,
        lag(quarterly_orders, 4) over (order by quarter_start) as quarterly_orders_last_year,
        case
            when quarterly_orders > 0
                then round(cast(quarterly_revenue / quarterly_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_order_value
    from quarterly

)

select * from with_yoy
