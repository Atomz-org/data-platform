with

monthly_revenue as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
),

trended as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders,
        round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2) as aov,
        avg(round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2)) over (
            partition by location_id order by month_start
            rows between 2 preceding and current row
        ) as aov_3m_ma,
        lag(round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2)) over (
            partition by location_id order by month_start
        ) as prev_month_aov,
        case
            when round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2) > lag(
                round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2)
            ) over (partition by location_id order by month_start) then 'increasing'
            when round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2) < lag(
                round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2)
            ) over (partition by location_id order by month_start) then 'decreasing'
            else 'stable'
        end as trend_direction
    from monthly_revenue
)

select * from trended
