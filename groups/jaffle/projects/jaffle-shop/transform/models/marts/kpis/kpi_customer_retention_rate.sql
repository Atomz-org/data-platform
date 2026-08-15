with final as (
    select
        month_start,
        tracked_active_customers,
        round(tracked_active_customers * 100.0 / nullif(tracked_active_customers, 0), 2) as retention_rate_pct,
        lag(round(tracked_active_customers * 100.0 / nullif(tracked_active_customers, 0), 2)) over (order by month_start) as prior_month_rate
    from {{ ref('met_monthly_customer_metrics') }}
)
select * from final
