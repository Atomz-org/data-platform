with

monthly_orders as (
    select
        month_start,
        location_id,
        monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
),

compared as (
    select
        month_start,
        location_id,
        monthly_orders as current_orders,
        lag(monthly_orders, 12) over (partition by location_id order by month_start) as prior_year_orders,
        monthly_orders - lag(monthly_orders, 12) over (partition by location_id order by month_start) as orders_yoy_change,
        round((monthly_orders - lag(monthly_orders, 12) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_orders, 12) over (partition by location_id order by month_start), 0), 2) as orders_yoy_change_pct
    from monthly_orders
)

select * from compared
