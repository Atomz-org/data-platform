with

daily_refunds as (
    select
        requested_date,
        count(*) as refund_count,
        sum(refund_amount) as total_amount,
        avg(count(*)) over (order by requested_date rows between 7 preceding and 1 preceding) as avg_7d_refunds
    from {{ ref('fct_refunds') }}
    group by 1
),

alerts as (
    select
        requested_date,
        refund_count,
        total_amount,
        avg_7d_refunds,
        round(refund_count * 100.0 / nullif(avg_7d_refunds, 0), 2) as pct_of_avg,
        'refund_spike' as alert_type,
        'warning' as severity
    from daily_refunds
    where refund_count > avg_7d_refunds * 2
      and avg_7d_refunds > 0
)

select * from alerts
