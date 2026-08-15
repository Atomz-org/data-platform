with

monthly_churn as (
    select
        month_start,
        tracked_active_customers,
        churned_customers,
        round(churned_customers * 100.0 / nullif(tracked_active_customers, 0), 2) as churn_rate_pct,
        avg(round(churned_customers * 100.0 / nullif(tracked_active_customers, 0), 2)) over (
            order by month_start rows between 3 preceding and 1 preceding
        ) as churn_3m_avg
    from {{ ref('met_monthly_customer_metrics') }}
),

alerts as (
    select
        month_start,
        tracked_active_customers,
        churned_customers,
        churn_rate_pct,
        churn_3m_avg,
        'customer_churn_spike' as alert_type,
        case when churn_rate_pct > churn_3m_avg * 1.5 then 'critical' else 'warning' end as severity
    from monthly_churn
    where churn_rate_pct > churn_3m_avg * 1.3
      and churn_3m_avg > 0
)

select * from alerts
