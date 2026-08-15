with final as (
    select
        month_start,
        tracked_active_customers,
        new_customers,
        churned_customers,
        round(tracked_active_customers * 100.0 / nullif(total_tracked_customers, 0), 2) as retention_rate_pct,
        lag(tracked_active_customers) over (order by month_start) as prior_month_customers
    from {{ ref('met_monthly_customer_metrics') }}
)
select * from final
