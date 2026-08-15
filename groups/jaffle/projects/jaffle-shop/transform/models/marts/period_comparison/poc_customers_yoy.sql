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
        lag(tracked_active_customers, 12) over (order by month_start) as prior_year_customers,
        new_customers as current_new,
        lag(new_customers, 12) over (order by month_start) as prior_year_new,
        round((tracked_active_customers - lag(tracked_active_customers, 12) over (order by month_start)) * 100.0
            / nullif(lag(tracked_active_customers, 12) over (order by month_start), 0), 2) as customer_yoy_change_pct
    from monthly_customers
)

select * from compared
