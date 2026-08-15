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
        lag(monthly_revenue) over (partition by location_id order by month_start) as prior_month_revenue,
        monthly_orders as current_orders,
        lag(monthly_orders) over (partition by location_id order by month_start) as prior_month_orders,
        monthly_revenue - lag(monthly_revenue) over (partition by location_id order by month_start) as revenue_change,
        round((monthly_revenue - lag(monthly_revenue) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_revenue) over (partition by location_id order by month_start), 0), 2) as revenue_change_pct,
        case
            when monthly_revenue > lag(monthly_revenue) over (partition by location_id order by month_start) * 1.1 then 'strong_growth'
            when monthly_revenue > lag(monthly_revenue) over (partition by location_id order by month_start) then 'growth'
            when monthly_revenue < lag(monthly_revenue) over (partition by location_id order by month_start) * 0.9 then 'significant_decline'
            when monthly_revenue < lag(monthly_revenue) over (partition by location_id order by month_start) then 'decline'
            else 'flat'
        end as performance_band
    from monthly_revenue
)

select * from compared
