with

monthly_customers as (
    select
        month_start,
        tracked_active_customers,
        new_customers
    from {{ ref('met_monthly_customer_metrics') }}
),

compared as (
    select
        month_start,
        tracked_active_customers as current_customers,
        lag(tracked_active_customers) over (order by month_start) as prior_month_customers,
        new_customers as current_new,
        lag(new_customers) over (order by month_start) as prior_month_new,
        tracked_active_customers - lag(tracked_active_customers) over (order by month_start) as customer_mom_change,
        round((tracked_active_customers - lag(tracked_active_customers) over (order by month_start)) * 100.0
            / nullif(lag(tracked_active_customers) over (order by month_start), 0), 2) as customer_mom_change_pct,
        round((new_customers - lag(new_customers) over (order by month_start)) * 100.0
            / nullif(lag(new_customers) over (order by month_start), 0), 2) as new_customer_mom_change_pct
    from monthly_customers
)

select * from compared
