with

monthly_orders as (
    select
        month_start,
        location_id,
        monthly_orders,
        monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
),

compared as (
    select
        month_start,
        location_id,
        monthly_orders as current_orders,
        lag(monthly_orders) over (partition by location_id order by month_start) as prior_month_orders,
        monthly_orders - lag(monthly_orders) over (partition by location_id order by month_start) as orders_mom_change,
        round((monthly_orders - lag(monthly_orders) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_orders) over (partition by location_id order by month_start), 0), 2) as orders_mom_change_pct
    from monthly_orders
)

select * from compared
