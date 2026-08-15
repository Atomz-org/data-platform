with

monthly_repeat as (
    select
        month_start,
        tracked_active_customers,
        round(tracked_active_customers * 100.0 / nullif(tracked_active_customers, 0), 2) as repeat_rate,
        lag(round(tracked_active_customers * 100.0 / nullif(tracked_active_customers, 0), 2)) over (
            order by month_start
        ) as prior_month_rate
    from {{ ref('met_monthly_customer_metrics') }}
),

alerts as (
    select
        month_start,
        repeat_rate,
        prior_month_rate,
        repeat_rate - prior_month_rate as rate_change_pp,
        'repeat_rate_drop' as alert_type,
        case when repeat_rate - prior_month_rate < -10 then 'critical' else 'warning' end as severity
    from monthly_repeat
    where repeat_rate < prior_month_rate - 5
)

select * from alerts
