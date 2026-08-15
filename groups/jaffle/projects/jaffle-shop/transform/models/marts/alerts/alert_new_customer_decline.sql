with

weekly_new_customers as (
    select
        {{ sf_date_trunc('week', "activity_date") }} as metric_week,
        sum(new_customers) as new_customers,
        avg(sum(new_customers)) over (
            order by {{ sf_date_trunc('week', "activity_date") }}
            rows between 4 preceding and 1 preceding
        ) as new_cust_4w_avg
    from {{ ref('met_daily_customer_metrics') }}
    group by 1
),

alerts as (
    select
        metric_week,
        new_customers,
        new_cust_4w_avg,
        round(new_cust_4w_avg - new_customers * 100.0 / nullif(new_cust_4w_avg, 0), 2) as decline_pct,
        'new_customer_decline' as alert_type,
        'warning' as severity
    from weekly_new_customers
    where new_customers < new_cust_4w_avg * 0.7
      and new_cust_4w_avg > 0
)

select * from alerts
