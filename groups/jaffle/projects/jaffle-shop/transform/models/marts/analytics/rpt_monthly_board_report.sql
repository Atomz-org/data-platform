with

monthly_revenue as (

    select
        month_start,
        sum(monthly_revenue) as total_monthly_revenue,
        sum(monthly_orders) as total_monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1

),

monthly_customers as (

    select
        month_start,
        tracked_active_customers
    from {{ ref('met_monthly_customer_metrics') }}

),

with_growth as (

    select
        mr.month_start,
        mr.total_monthly_revenue,
        mr.total_monthly_orders,
        mc.tracked_active_customers,
        lag(mr.total_monthly_revenue, 12) over (order by mr.month_start) as revenue_last_year,
        case
            when lag(mr.total_monthly_revenue, 12) over (order by mr.month_start) > 0
                then round(cast(
                    (mr.total_monthly_revenue - lag(mr.total_monthly_revenue, 12) over (order by mr.month_start)) * 100.0
                    / lag(mr.total_monthly_revenue, 12) over (order by mr.month_start)
                as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_yoy_growth_pct,
        case
            when mr.total_monthly_orders > 0
                then round(cast(mr.total_monthly_revenue / mr.total_monthly_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_order_value
    from monthly_revenue as mr
    left join monthly_customers as mc
        on mr.month_start = mc.month_start

)

select * from with_growth
