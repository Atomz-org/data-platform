with

daily_payments as (
    select
        processed_date,
        count(*) as total_payments,
        count(case when payment_status = 'failed' then 1 end) as failed_payments,
        round(count(case when payment_status = 'failed' then 1 end) * 100.0 / nullif(count(*), 0), 2) as failure_rate_pct
    from {{ ref('fct_payment_transactions') }}
    group by 1
),

alerts as (
    select
        processed_date,
        total_payments,
        failed_payments,
        failure_rate_pct,
        'payment_failure_spike' as alert_type,
        case when failure_rate_pct > 10 then 'critical' else 'warning' end as severity
    from daily_payments
    where failure_rate_pct > 5
)

select * from alerts
