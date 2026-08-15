with final as (
    select
        month_start,
        tracked_active_customers,
        churned_customers,
        round(churned_customers * 100.0 / nullif(tracked_active_customers, 0), 2) as churn_rate_pct,
        lag(round(churned_customers * 100.0 / nullif(tracked_active_customers, 0), 2)) over (order by month_start) as prior_month_churn
    from {{ ref('met_monthly_customer_metrics') }}
)
select * from final
