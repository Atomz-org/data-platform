with

monthly_revenue as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
),

compared as (
    select
        month_start,
        location_id,
        monthly_revenue as current_revenue,
        lag(monthly_revenue, 12) over (partition by location_id order by month_start) as prior_year_revenue,
        monthly_orders as current_orders,
        lag(monthly_orders, 12) over (partition by location_id order by month_start) as prior_year_orders,
        monthly_revenue - lag(monthly_revenue, 12) over (partition by location_id order by month_start) as revenue_yoy_change,
        round((monthly_revenue - lag(monthly_revenue, 12) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_revenue, 12) over (partition by location_id order by month_start), 0), 2) as revenue_yoy_change_pct
    from monthly_revenue
)

select * from compared
